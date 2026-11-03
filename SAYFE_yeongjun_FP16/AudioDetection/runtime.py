from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
import select
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone

import numpy as np

from .core import EventDetector, RollingAudio
from .settings import ROOT


class Microphone:
    def __init__(self, spec, config, state, stop):
        self.spec,self.config,self.state,self.stop = spec,config,state,stop
        self.buffer = RollingAudio(int(config['sample_rate']*config['window_seconds']))
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run,name='audio-'+self.spec['id'],daemon=True)
        self.thread.start()

    def _capture(self):
        cid,sr = self.spec['id'],self.config['sample_rate']
        command = ['arecord','-q','-D',self.spec['alsa_device'],'-t','raw','-f','S16_LE',
                   '-r',str(sr),'-c','1','--period-size',str(sr//10)]
        errors = deque(maxlen=8)
        process = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
        def drain():
            for line in iter(process.stderr.readline,b''):
                errors.append(line.decode('utf-8',errors='replace').strip()[:500])
        stderr_worker = threading.Thread(target=drain,name='alsa-errors-'+cid,daemon=True)
        stderr_worker.start()
        remainder,last_data = b'',None
        try:
            while not self.stop.is_set():
                now = time.monotonic_ns()
                if last_data is not None and (now-last_data)/1e9>self.config['stale_seconds']:
                    raise RuntimeError('Microphone capture stalled')
                ready,_,_ = select.select([process.stdout],[],[],.25)
                if not ready:
                    if process.poll() is not None:
                        raise RuntimeError('; '.join(errors) or 'arecord stopped')
                    if last_data is None:
                        last_data = now
                    continue
                block = os.read(process.stdout.fileno(),sr//10*2)
                if not block:
                    process.wait(timeout=1)
                    stderr_worker.join(timeout=.2)
                    raise RuntimeError('; '.join(errors) or f'arecord exited ({process.returncode})')
                now = time.monotonic_ns()
                # Do not mix pre-gap and post-gap sound into one context window.
                if last_data is not None and now-last_data>500_000_000:
                    self.buffer.clear()
                    with self.state.lock:
                        self.state.cameras[cid]['input_resets'] += 1
                        self.state.cameras[cid]['result'] = None
                last_data = now
                raw = remainder+block
                size = len(raw)//2*2
                remainder = raw[size:]
                samples = np.frombuffer(raw[:size],dtype='<i2').astype(np.float32)/32768.
                self.buffer.append(samples,now)
                with self.state.lock:
                    row = self.state.cameras[cid]
                    row.update(capture_status='CAPTURING',capture_ns=now,error=None)
                    row['capture_samples'] += len(samples)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            process.stdout.close()
            stderr_worker.join(timeout=1)
            process.stderr.close()

    def _run(self):
        cid = self.spec['id']
        while not self.stop.is_set():
            try:
                self._capture()
            except Exception as exc:
                self.buffer.clear()
                with self.state.lock:
                    self.state.cameras[cid].update(capture_status='ERROR',error=str(exc),result=None)
                self.state.event('audio_capture_error',camera_id=cid,error=str(exc))
                self.stop.wait(2)
        with self.state.lock:
            self.state.cameras[cid]['capture_status'] = 'STOPPED'


class AudioRuntime:
    def __init__(self, config, state, model_factory=None):
        self.config,self.state = config,state
        self.model_factory = model_factory
        self.stop = threading.Event()
        self.microphones = {c['id']:Microphone(c,config,state,self.stop) for c in config['cameras']}
        self.worker = None
        self.locks = ExitStack()

    def start(self):
        folder = ROOT/'.locks'
        folder.mkdir(exist_ok=True)
        try:
            for spec in self.config['cameras']:
                key = hashlib.sha256(spec['alsa_device'].encode()).hexdigest()[:16]
                file = self.locks.enter_context((folder/key).open('a'))
                try:
                    fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise RuntimeError(f"{spec['id']}: another AudioDetection instance owns this microphone") from exc
            for microphone in self.microphones.values():
                microphone.start()
            self.worker = threading.Thread(target=self._infer,name='sed-inference',daemon=True)
            self.worker.start()
        except Exception:
            self.close()
            raise

    def _infer(self):
        try:
            if self.model_factory is None:
                from .backend import PretrainedSED
                factory = PretrainedSED
            else:
                factory = self.model_factory
            model = factory(self.config)
            # Match the configured microphone count, including CAM3.
            samples = int(self.config['sample_rate']*self.config['window_seconds'])
            model.predict(np.zeros((len(self.microphones),samples),dtype=np.float32))
            detector = EventDetector(model.labels,self.config)
            with self.state.lock:
                self.state.labels = list(model.labels)
                self.state.model = model.metadata
                self.state.model_status = 'READY'
            if self.state.journal:
                (self.state.journal.directory/'model.json').write_text(json.dumps(model.metadata,indent=2))
            self.state.event('audio_model_ready',**model.metadata)
        except Exception as exc:
            with self.state.lock:
                self.state.model_status,self.state.model_error = 'ERROR',str(exc)
            self.state.event('audio_model_error',error=str(exc))
            return
        last_sequence,last_inference,last_generation = {},{},{}
        while not self.stop.is_set():
            selected = []
            now = time.monotonic_ns()
            for cid,microphone in self.microphones.items():
                audio = microphone.buffer.snapshot()
                if audio['generation']!=last_generation.get(cid):
                    detector.invalidate(cid)
                    last_generation[cid] = audio['generation']
                with self.state.lock:
                    capturing = self.state.cameras[cid]['capture_status']=='CAPTURING'
                age = math_age(now,audio['end_ns'])
                if not capturing or age is None or age>self.config['stale_seconds']:
                    detector.invalidate(cid)
                    continue
                if (audio['valid_samples'] < self.config['min_audio_seconds']*self.config['sample_rate']
                        or audio['sequence']==last_sequence.get(cid)
                        or (now-last_inference.get(cid,0))/1e9<self.config['hop_seconds']):
                    continue
                selected.append((cid,audio))
            if not selected:
                self.stop.wait(.02)
                continue
            started = time.monotonic_ns()
            try:
                scores = model.predict(np.stack([audio['waveform'] for _,audio in selected]))
                if scores.shape != (len(selected),len(model.labels)):
                    raise ValueError('Invalid SED output shape')
                finished = time.monotonic_ns()
                for (cid,audio),probabilities in zip(selected,scores):
                    # Cadence is measured from inference start. Slow batches
                    # process the newest window immediately instead of adding
                    # another hop delay after finishing.
                    last_sequence[cid],last_inference[cid] = audio['sequence'],started
                    # Never create events from inference that finished too late.
                    if math_age(finished,audio['end_ns'])>self.config['stale_seconds']:
                        detector.invalidate(cid)
                        continue
                    self.publish(model.labels,detector,cid,audio,probabilities,started,finished)
            except Exception as exc:
                for cid,_ in selected:
                    detector.invalidate(cid)
                    last_inference[cid] = time.monotonic_ns()
                    with self.state.lock:
                        self.state.cameras[cid].update(result=None,error='Inference: '+str(exc))
                self.state.event('audio_inference_error',error=str(exc))
                self.stop.wait(.5)

    def publish(self, labels, detector, cid, audio, scores, started, finished):
        order = np.argsort(scores)[::-1]
        valid = audio['waveform'][-min(audio['valid_samples'],self.config['sample_rate']):]
        rms = float(np.sqrt(np.mean(valid.astype(np.float64)**2)))
        result = dict(sequence=audio['sequence'],audio_end_ns=audio['end_ns'],
                      time=datetime.now(timezone.utc).isoformat(),
                      inference_ms=(finished-started)/1e6,input_seconds=audio['valid_samples']/self.config['sample_rate'],
                      audio_to_result_ms=(finished-audio['end_ns'])/1e6,rms_dbfs=20*np.log10(max(rms,1e-9)),
                      top=[dict(label=labels[i],score=float(scores[i])) for i in order[:10]],
                      scores=[float(s) for s in scores])
        with self.state.lock:
            current = self.state.cameras[cid]
            # A capture error may have occurred while this batch was running.
            with self.microphones[cid].buffer.lock:
                generation = self.microphones[cid].buffer.generation
                if current['capture_status']!='CAPTURING' or generation!=audio['generation']:
                    detector.invalidate(cid)
                    return
                # Rejected results must not consume the event cooldown. Commit
                # detector state and camera state together with the generation.
                hazards,events = detector.update(scores,finished/1e9,cid)
                result.update(hazards=hazards,danger=any(h['active'] for h in hazards))
                current.update(result=result,inference_end_ns=finished,error=None)
                current['inference_count'] += 1
        if self.state.journal:
            self.state.journal.write('prediction',dict(camera_id=cid,**{k:v for k,v in result.items() if k!='scores'}))
        for event in events:
            self.state.event(**event,audio_end_ns=audio['end_ns'],sequence=audio['sequence'])

    def close(self):
        self.stop.set()
        for microphone in self.microphones.values():
            if microphone.thread:
                microphone.thread.join(timeout=4)
        if self.worker:
            self.worker.join(timeout=15)
        self.locks.close()
        with self.state.lock:
            self.state.running = False


def math_age(now, stamp):
    return None if stamp is None or stamp>now else (now-stamp)/1e9
