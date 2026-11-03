import argparse
from datetime import datetime
import json
import signal
import subprocess
import threading
import time
import uuid

import numpy as np

from .core import AudioState, Journal
from .runtime import AudioRuntime
from .settings import ROOT, load_config
from .vision_bridge import ExplosionPublisher


def main():
    parser = argparse.ArgumentParser(description='Multi-microphone PretrainedSED live monitor')
    parser.add_argument('--config',default=ROOT/'config.json')
    parser.add_argument('--list-devices',action='store_true')
    parser.add_argument('--check-model',action='store_true')
    parser.add_argument('--duration',type=float,help='Stop after this many seconds (including model startup)')
    parser.add_argument('--no-web',action='store_true')
    args = parser.parse_args()
    if args.list_devices:
        return subprocess.run(['arecord','-l'],check=False).returncode
    config = load_config(args.config)
    if args.check_model:
        from .backend import PretrainedSED
        model = PretrainedSED(config)
        started = time.perf_counter()
        samples = int(config['sample_rate']*config['window_seconds'])
        scores = model.predict(np.zeros((len(config['cameras']),samples),dtype=np.float32))
        print(json.dumps(dict(**model.metadata,output_shape=list(scores.shape),
                              finite=bool(np.isfinite(scores).all()),
                              batch_ms=(time.perf_counter()-started)*1000),indent=2))
        return 0
    if args.duration is not None and (not np.isfinite(args.duration) or args.duration<=0):
        parser.error('--duration must be positive')
    journal = Journal(ROOT/'runs'/(datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8]))
    (journal.directory/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2))
    state = AudioState(config,journal)
    explosion_publisher = ExplosionPublisher(config['vision_event_port']) if config['vision_event_enabled'] else None
    state.explosion_publisher = explosion_publisher
    runtime = AudioRuntime(config,state)
    server = server_thread = None
    stop = threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):
        signal.signal(sig,lambda *_:stop.set())
    status = 0
    try:
        if explosion_publisher:
            explosion_publisher.start()
        if not args.no_web:
            from werkzeug.serving import make_server
            from .web import make_app
            server = make_server(config['host'],config['port'],make_app(state),threaded=True)
            server.daemon_threads = True
            server_thread = threading.Thread(target=server.serve_forever,daemon=True)
            server_thread.start()
            print(f"[AUDIO] http://localhost:{config['port']} / {journal.directory}",flush=True)
        runtime.start()
        started = time.monotonic()
        while not stop.wait(.25):
            with state.lock:
                if state.model_status=='ERROR':
                    raise RuntimeError(state.model_error)
            if args.duration and time.monotonic()-started>=args.duration:
                break
    except Exception as exc:
        print('[AUDIO] ERROR:',str(exc),flush=True)
        status = 1
    finally:
        runtime.close()
        if explosion_publisher:
            explosion_publisher.close()
        if server:
            server.shutdown()
            server.server_close()
        if server_thread:
            server_thread.join(timeout=3)
        final = state.snapshot()
        # Preserve final capture/inference counters without storing PCM.
        (journal.directory/'summary.json').write_text(json.dumps(final,ensure_ascii=False,indent=2))
        print(json.dumps(dict(run=str(journal.directory),model=state.model_status,
                              cameras=[{k:c[k] for k in ('id','capture_samples','inference_count','error')}
                                       for c in final['cameras']],events=len(final['events'])),ensure_ascii=False),flush=True)
        journal.close()
    return status


if __name__=='__main__':
    raise SystemExit(main())
