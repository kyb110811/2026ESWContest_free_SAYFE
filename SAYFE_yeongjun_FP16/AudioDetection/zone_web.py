"""Three-camera, two-zone display backed by the existing audio and vision states."""
from pathlib import Path
import threading
import time

from flask import Flask, Response, jsonify, render_template


ZONES = {'CAM1': 'A', 'CAM2': 'A', 'CAM3': 'B'}


def sound_kind(label):
    if label.casefold() == 'explosion':
        return 'explosion'
    return None


def zone_snapshot(audio_state, camera3=None):
    snapshot = audio_state.snapshot()
    cameras = []
    zones = {name: {'id': name, 'state': 'UNKNOWN', 'sounds': [], 'hazards': [],
                    'microphones': []} for name in ('A', 'B')}
    for camera in snapshot['cameras']:
        row = {'id': camera['id'], 'name': camera['name'], 'zone': ZONES.get(camera['id']),
               'state': camera['state'], 'capture_status': camera['capture_status'],
               'error': camera['error'], 'result_age_seconds': camera['result_age_seconds'],
               'top': camera['result']['top'][:5] if camera['result'] else []}
        cameras.append(row)
        zone = zones.get(row['zone'])
        if zone is None:
            continue
        zone['microphones'].append(row['id'])
        if camera['valid']:
            for item in camera['result']['top'][:3]:
                zone['sounds'].append({'camera_id': row['id'], **item})
            for hazard in camera['result']['hazards']:
                kind = sound_kind(hazard['label'])
                if kind and hazard['active']:
                    zone['hazards'].append({'camera_id': row['id'], 'kind': kind,
                                            'label': hazard['label'], 'score': hazard['score']})
    for zone in zones.values():
        zone_cameras = [row for row in cameras if row['zone'] == zone['id']]
        zone['sounds'].sort(key=lambda row: row['score'], reverse=True)
        zone['state'] = ('DANGER' if zone['hazards'] else 'CLEAR' if zone_cameras and
                         all(row['state'] == 'CLEAR' for row in zone_cameras) else 'UNKNOWN')
    events = []
    for event in reversed(snapshot['events']):
        if event['kind'] not in {'audio_danger_started', 'audio_danger_ended'}:
            continue
        zone = ZONES.get(event.get('camera_id'))
        kind = sound_kind(event.get('label', ''))
        if zone and kind:
            events.append({'time': event['time'], 'event_id': event['event_id'],
                           'zone': zone, 'camera_id': event['camera_id'],
                           'kind': kind, 'label': event['label'], 'score': event.get('score'),
                           'active': event['kind'] == 'audio_danger_started'})
    return {'zones': list(zones.values()), 'cameras': cameras, 'events': events[:30],
            'model_status': snapshot['model_status'],
            'camera3': camera3.status() if camera3 else {'state': 'UNKNOWN', 'error': '영상 입력 없음'}}


class Camera3Video:
    def __init__(self, spec, jpeg_quality=75):
        self.spec = spec
        self.jpeg_quality = jpeg_quality
        self.stop_event = threading.Event()
        self.changed = threading.Condition()
        self.frame = None
        self.sequence = 0
        self.last_frame = None
        self.error = None
        self.source = None
        self.thread = None

    def _source(self):
        if self.spec.get('video_source'):
            return self.spec['video_source']
        match = self.spec.get('video_match', 'FHD60F').casefold()
        paths = sorted(Path('/dev/v4l/by-id').glob('*video-index0'))
        paths += sorted(Path('/dev/v4l/by-path').glob('*video-index0'))
        return next((str(path) for path in paths if match in path.name.casefold()), None)

    def start(self):
        self.thread = threading.Thread(target=self._run, name='zone-cam3-video', daemon=True)
        self.thread.start()

    def _run(self):
        import cv2
        while not self.stop_event.is_set():
            source = self._source()
            if not source:
                self.error = 'CAM3 영상 장치를 찾을 수 없습니다'
                self.stop_event.wait(2)
                continue
            self.source = source
            capture = cv2.VideoCapture(source, cv2.CAP_V4L2)
            try:
                if not capture.isOpened():
                    self.error = f'CAM3 영상 열기 실패: {source}'
                else:
                    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    capture.set(cv2.CAP_PROP_FPS, 15)
                    while not self.stop_event.is_set():
                        ok, frame = capture.read()
                        if not ok:
                            self.error = 'CAM3 영상 입력 중단'
                            break
                        encoded, jpg = cv2.imencode('.jpg', frame,
                                                    [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
                        if encoded:
                            with self.changed:
                                self.frame = jpg.tobytes()
                                self.sequence += 1
                                self.last_frame = time.monotonic()
                                self.error = None
                                self.changed.notify_all()
            finally:
                capture.release()
            self.stop_event.wait(2)

    def status(self):
        age = None if self.last_frame is None else time.monotonic() - self.last_frame
        return {'state': 'LIVE' if age is not None and age < 3 else 'UNKNOWN',
                'error': self.error, 'source': self.source}

    def stop(self):
        self.stop_event.set()
        with self.changed:
            self.changed.notify_all()
        if self.thread:
            self.thread.join(timeout=3)


def make_app(audio_state, vision_state, camera3):
    app = Flask(__name__, template_folder='templates', static_folder='static')

    @app.get('/')
    def index():
        return render_template('zones.html')

    @app.get('/api/status')
    def status():
        response = jsonify(zone_snapshot(audio_state, camera3))
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/video/<camera_id>')
    def video(camera_id):
        if camera_id not in ZONES:
            return '카메라 없음', 404

        def generate():
            last = None
            while audio_state.running:
                if camera_id == 'CAM3':
                    with camera3.changed:
                        camera3.changed.wait_for(lambda: camera3.stop_event.is_set() or
                            camera3.sequence != last, timeout=1)
                        if camera3.stop_event.is_set():
                            break
                        current = camera3.sequence
                        jpg = camera3.frame
                else:
                    with vision_state.changed:
                        vision_state.changed.wait_for(lambda: not vision_state.running or
                            (camera_id in vision_state.jpegs and
                             vision_state.jpegs[camera_id][0] != last), timeout=1)
                        if not vision_state.running:
                            break
                        item = vision_state.jpegs.get(camera_id)
                        current, jpg = item if item else (last, None)
                if jpg is None or current == last:
                    continue
                last = current
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n'

        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame',
                        headers={'Cache-Control': 'no-store'})

    return app
