"""Short, bounded live microphone + real model + HTTP API verification."""
from datetime import datetime
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera',action='append',help='Only test this camera; repeat to select several')
    args=parser.parse_args()
    folder=ROOT/'runs'/'diagnostics'
    folder.mkdir(parents=True,exist_ok=True)
    stem=datetime.now().strftime('%Y%m%dT%H%M%S')
    config=json.loads((ROOT/'config.json').read_text())
    if args.camera:
        known={c['id'] for c in config['cameras']}
        if set(args.camera)-known:
            parser.error('Unknown camera: '+', '.join(sorted(set(args.camera)-known)))
        config['cameras']=[c for c in config['cameras'] if c['id'] in args.camera]
    expected_ids = {c['id'] for c in config['cameras']}
    config.update(host='127.0.0.1',port=5012)
    path=folder/(stem+'_config.json')
    path.write_text(json.dumps(config,ensure_ascii=False,indent=2))
    log=(folder/(stem+'_live.log')).open('w')
    process=subprocess.Popen([sys.executable,'-s','-B','-m','AudioDetection.app','--config',str(path),
                              '--duration','18'],cwd=ROOT.parent,stdout=log,stderr=subprocess.STDOUT)
    snapshots=[]
    deadline=time.monotonic()+35
    try:
        while process.poll() is None and time.monotonic()<deadline:
            try:
                with urlopen('http://127.0.0.1:5012/api/status',timeout=1) as response:
                    snapshot=json.load(response)
                if snapshot['model_status']=='READY' and all(c['valid'] for c in snapshot['cameras']):
                    assert {c['id'] for c in snapshot['cameras']}==expected_ids
                    assert len(snapshot['labels'])==446
                    assert 'Mechanisms' not in snapshot['labels']
                    assert all(len(c['result']['scores'])==len(snapshot['labels']) for c in snapshot['cameras'])
                    snapshots.append(snapshot)
            except (OSError,ValueError):
                pass
            time.sleep(.4)
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        log.close()
    if process.returncode or not snapshots:
        raise RuntimeError('Live verification failed; see '+str(folder/(stem+'_live.log')))
    snapshot=snapshots[-1]
    report=dict(valid_http_snapshots=len(snapshots),microphone_count=len(expected_ids),class_count=len(snapshot['labels']),
                model=snapshot['model'],cameras=[dict(id=c['id'],capture_samples=c['capture_samples'],
                inference_count=c['inference_count'],batch_ms=c['result']['inference_ms'],
                audio_to_result_ms=c['result']['audio_to_result_ms'],rms_dbfs=c['result']['rms_dbfs'],
                top3=c['result']['top'][:3],error=c['error']) for c in snapshot['cameras']],
                limits='Live input and all-class output verified; no labelled explosion/siren sound was played.')
    target=folder/(stem+'_live.json')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(dict(report=str(target),**report),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
