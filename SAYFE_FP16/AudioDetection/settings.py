import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM_COMMIT = '1aa47e482f7e89904cba2338999345025d8b4e36'


def load_config(path=ROOT/'config.json'):
    config = json.loads(Path(path).read_text())
    config.setdefault('vision_event_enabled', False)
    config.setdefault('vision_event_port', 5010)
    config.setdefault('zone_port', 5012)
    if not isinstance(config['vision_event_enabled'], bool):
        raise ValueError('Invalid vision_event_enabled')
    port = config['vision_event_port']
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError('Invalid vision_event_port')
    if config['model_name'] not in {'frame_mn06', 'frame_mn10'}:
        raise ValueError('model_name must be frame_mn06 or frame_mn10')
    if config['device'] not in {'cpu', 'cuda'}:
        raise ValueError('device must be cpu or cuda')
    if config['sample_rate'] != 16000 or config['window_seconds'] != 10:
        raise ValueError('PretrainedSED expects a 16 kHz, 10-second input')
    for key in ('cpu_threads', 'port', 'zone_port'):
        value = config[key]
        if isinstance(value,bool) or not isinstance(value,int) or value < 1:
            raise ValueError('Invalid '+key)
    if (config['port'] > 65535 or config['zone_port'] > 65535
            or config['zone_port'] in {config['port'], config['vision_event_port']}
            or not isinstance(config['host'],str) or not config['host']):
        raise ValueError('Invalid web address')
    for key in ('hop_seconds','decision_seconds','min_audio_seconds','stale_seconds',
                'release_seconds','cooldown_seconds'):
        value = config[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('Invalid '+key)
    if not config['hop_seconds'] <= config['decision_seconds'] <= 10:
        raise ValueError('hop_seconds <= decision_seconds <= 10 is required')
    if not config['min_audio_seconds'] <= 10 or config['stale_seconds'] <= config['hop_seconds']:
        raise ValueError('Invalid minimum input or stale interval')
    for key in ('danger_threshold','top1_min_score','clear_threshold'):
        value = config[key]
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not 0 < value <= 1:
            raise ValueError('Invalid '+key)
    if config['clear_threshold'] > config['danger_threshold']:
        raise ValueError('clear_threshold must not exceed danger_threshold')
    cameras = config['cameras']
    if not isinstance(cameras,list) or not cameras:
        raise ValueError('At least one microphone device is required')
    for camera in cameras:
        if (not isinstance(camera,dict)
                or not all(isinstance(camera.get(k),str) and camera[k].strip() for k in ('id','name','alsa_device'))
                or not re.fullmatch(r'CAM[1-9][0-9]*',camera['id'])):
            raise ValueError('Invalid microphone configuration')
    if (len({c['id'] for c in cameras})!=len(cameras)
            or len({c['alsa_device'] for c in cameras})!=len(cameras)):
        raise ValueError('Microphone camera IDs and devices must be distinct')
    if 'CAM3' in {c['id'] for c in cameras}:
        cam3 = next(c for c in cameras if c['id'] == 'CAM3')
        for key in ('video_source', 'video_match'):
            if key in cam3 and (not isinstance(cam3[key], str) or not cam3[key].strip()):
                raise ValueError('Invalid CAM3 '+key)
    return config
