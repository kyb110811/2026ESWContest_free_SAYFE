from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import threading
import time
import uuid

import numpy as np


EXPLOSION_RELATED_LABELS = (
    'Explosion', 'Artillery fire', 'Bang', 'Boom', 'Burst, pop',
    'Eruption', 'Firecracker', 'Fireworks', 'Fusillade',
    'Gunshot, gunfire', 'Sonic boom',
)


def danger_label(label):
    return label.casefold() == 'explosion'


class RollingAudio:
    """A bounded chronological PCM ring. Missing input is never silence-filled."""
    def __init__(self, capacity):
        self.data = np.zeros(capacity,dtype=np.float32)
        self.capacity, self.position, self.count, self.sequence = capacity,0,0,0
        self.generation = 0
        self.end_ns = None
        self.lock = threading.Lock()

    def append(self, samples, end_ns):
        samples = np.asarray(samples,dtype=np.float32).reshape(-1)
        if not len(samples):
            return
        with self.lock:
            samples = samples[-self.capacity:]
            n,first = len(samples),min(len(samples),self.capacity-self.position)
            self.data[self.position:self.position+first] = samples[:first]
            self.data[:n-first] = samples[first:]
            self.position = (self.position+n)%self.capacity
            self.count = min(self.capacity,self.count+n)
            self.sequence += 1
            self.end_ns = end_ns

    def clear(self):
        with self.lock:
            self.position,self.count,self.end_ns = 0,0,None
            self.generation += 1

    def snapshot(self):
        with self.lock:
            output = np.zeros(self.capacity,dtype=np.float32)
            if self.count:
                start = (self.position-self.count)%self.capacity
                first = min(self.count,self.capacity-start)
                output[-self.count:][:first] = self.data[start:start+first]
                output[-self.count:][first:] = self.data[:self.count-first]
            return dict(waveform=output,valid_samples=self.count,sequence=self.sequence,
                        generation=self.generation,end_ns=self.end_ns)


class EventDetector:
    """Independent per-camera/class onset, hysteresis, release and cooldown."""
    def __init__(self, labels, config):
        self.labels,self.config = list(labels),config
        self.indices = [i for i,label in enumerate(labels) if danger_label(label)]
        if 'Explosion' not in self.labels or 'Siren' not in self.labels:
            raise ValueError('Model must include Explosion and Siren')
        self.explosion_index = self.labels.index('Explosion')
        self.explosion_source_indices = [i for i,label in enumerate(self.labels)
                                         if label in EXPLOSION_RELATED_LABELS]
        self.active,self.last_hit,self.last_event = set(),{},{}

    def update(self, scores, now, camera_id):
        scores = np.asarray(scores,dtype=float)
        if scores.shape!=(len(self.labels),) or not np.isfinite(scores).all() or (scores<0).any() or (scores>1).any():
            raise ValueError('Invalid model probabilities')
        effective_scores = scores.copy()
        effective_scores[self.explosion_index] = min(1., float(scores[self.explosion_source_indices].sum()))
        # Rank the combined Explosion against other sounds once, without
        # letting its contributing classes compete with the combined score.
        ranking = effective_scores.copy()
        for i in self.explosion_source_indices:
            if i != self.explosion_index:
                ranking[i] = 0.
        top = int(np.argmax(ranking))
        events = []
        for i in self.indices:
            key = (camera_id,i)
            score = float(effective_scores[i])
            hit = score >= self.config['danger_threshold'] or (i==top and score>=self.config['top1_min_score'])
            if hit or (key in self.active and score>=self.config['clear_threshold']):
                self.last_hit[key] = now
            if hit and key not in self.active:
                self.active.add(key)
                if now-self.last_event.get(key,-math.inf)>=self.config['cooldown_seconds']:
                    events.append(dict(kind='audio_danger_started',camera_id=camera_id,label=self.labels[i],
                                       score=score,top1=i==top,threshold=self.config['danger_threshold'],
                                       trigger='top1' if i==top and score<self.config['danger_threshold'] else 'threshold'))
                    self.last_event[key] = now
            if key in self.active and now-self.last_hit.get(key,now)>=self.config['release_seconds']:
                self.active.remove(key)
                events.append(dict(kind='audio_danger_ended',camera_id=camera_id,label=self.labels[i],score=score))
        hazards = [dict(label=self.labels[i],score=float(effective_scores[i]),active=(camera_id,i) in self.active,
                        top1=i==top) for i in self.indices]
        return hazards,events

    def invalidate(self, camera_id):
        self.active = {key for key in self.active if key[0]!=camera_id}
        self.last_hit = {key:value for key,value in self.last_hit.items() if key[0]!=camera_id}


class Journal:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True,exist_ok=False)
        self.directory = directory
        self.events = (directory/'events.jsonl').open('a',encoding='utf-8')
        self.predictions = (directory/'predictions.jsonl').open('a',encoding='utf-8')
        self.lock = threading.Lock()
        self.error = None

    def write(self, kind, row):
        try:
            with self.lock:
                target = self.events if kind=='event' else self.predictions
                target.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
                target.flush()
        except (OSError,ValueError) as exc:
            self.error = str(exc)

    def close(self):
        with self.lock:
            self.events.close()
            self.predictions.close()


class AudioState:
    def __init__(self, config, journal=None):
        self.config,self.journal = config,journal
        self.lock = threading.RLock()
        self.run_id = uuid.uuid4().hex
        self.running = True
        self.model_status,self.model_error,self.model = 'LOADING',None,{}
        self.labels = []
        self.events = deque(maxlen=100)
        self.explosion_publisher = None
        self.cameras = {c['id']:{**c,'capture_status':'WAITING','error':None,'capture_ns':None,
                               'inference_end_ns':None,'result':None,'capture_samples':0,
                               'inference_count':0,'input_resets':0} for c in config['cameras']}

    def event(self, kind, **fields):
        row = dict(kind=kind,event_id=uuid.uuid4().hex,run_id=self.run_id,
                   time=datetime.now(timezone.utc).isoformat(),**fields)
        with self.lock:
            self.events.append(row)
        if self.journal:
            self.journal.write('event',row)
        if self.explosion_publisher:
            self.explosion_publisher.submit(row)
        return row

    def snapshot(self, now_ns=None):
        now = time.monotonic_ns() if now_ns is None else now_ns
        with self.lock:
            cameras = []
            for row in self.cameras.values():
                current = deepcopy(row)
                result = current['result']
                capture = current['capture_ns']
                age = None if capture is None else (now-capture)/1e9
                decision_age = None if result is None else (now-result['audio_end_ns'])/1e9
                valid = bool(self.running and self.model_status=='READY' and current['capture_status']=='CAPTURING'
                             and age is not None and 0<=age<=self.config['stale_seconds']
                             and decision_age is not None and 0<=decision_age<=self.config['stale_seconds'])
                current.update(valid=valid,input_age_seconds=age,result_age_seconds=decision_age,
                               state='DANGER' if valid and result['danger'] else 'CLEAR' if valid else 'UNKNOWN')
                if not valid:
                    current['result'] = None
                cameras.append(current)
            judged = [row for row in cameras if row['valid']]
            overall = ('DANGER' if any(row['state']=='DANGER' for row in judged)
                       else 'CLEAR' if len(judged)==len(cameras) else 'UNKNOWN')
            return dict(run_id=self.run_id,running=self.running,state=overall,model_status=self.model_status,
                        model_error=self.model_error,model=deepcopy(self.model),labels=list(self.labels),
                        cameras=cameras,events=deepcopy(list(self.events)),
                        vision_event_delivery=(self.explosion_publisher.snapshot()
                                               if self.explosion_publisher else None),
                        recording_error=self.journal.error if self.journal else None,
                        settings={key:self.config[key] for key in ('danger_threshold','top1_min_score',
                                  'clear_threshold','decision_seconds','hop_seconds','window_seconds')})
