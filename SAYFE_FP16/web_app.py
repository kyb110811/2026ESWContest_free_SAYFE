import threading
from copy import deepcopy
import time
import secrets
import csv
import io
import math
from pathlib import Path
from urllib.parse import urlsplit

from manual_events import ManualEvents


class FrameEncoder:
    def __init__(self, state, config):
        self.state, self.config = state, config
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, name='jpeg-encoder', daemon=True)
        self.thread.start()

    def _run(self):
        import cv2
        seen = {}
        while not self.stop_event.is_set():
            with self.state.lock:
                views = {cid: (raw, {**result, 'risk_assessment': deepcopy(result.get('risk_assessment', {}))})
                         for cid, (raw, result) in self.state.views.items()}
            for cid, (raw, result) in views.items():
                seq = result['frame_seq']
                labels = tuple((p['observation_id'], p.get('person_id'))
                               for p in result.get('risk_assessment', {}).get('persons', []))
                # Renumbering updates the overlay even without a new capture.
                signature = (seq, labels)
                if seen.get(cid) == signature:
                    continue
                seen[cid] = signature
                try:
                    frame = raw.copy()
                    assessment = result.get('risk_assessment', {})
                    for zone in assessment.get('danger_boxes', []):
                        x1, y1, x2, y2 = [int(round(v)) for v in zone['bbox']]
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
                        cv2.putText(frame, 'EXCAVATOR DANGER AREA', (x1, max(40, y1-5)),
                                    cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 165, 255), 1)
                    persons = {p['observation_id']: p for p in assessment.get('persons', [])}
                    for index, detection in enumerate(result['detections']):
                        if detection['class_name'] not in {'person', 'excavator'}:
                            continue
                        x1, y1, x2, y2 = [int(round(v)) for v in detection['bbox']]
                        person = persons.get(f'{cid}:{seq}:{index}', {})
                        if detection['class_name'] == 'person':
                            color = ((160, 160, 160) if detection.get('risk_ignored') else
                                     {'DANGER': (0, 0, 255), 'SAFE': (0, 220, 0)}.get(person.get('state'), (0, 255, 255)))
                        else:
                            color = (100, 220, 180)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        if detection.get('risk_ignored'):
                            cv2.putText(frame, 'person', (x1, max(45, y1-5)),
                                        cv2.FONT_HERSHEY_SIMPLEX, .5, color, 1)
                            continue
                        person_state = person.get('state') if person.get('state') in {'SAFE','DANGER'} else 'UNKNOWN'
                        name = (f"{person.get('person_id') or 'person'} {person_state}"
                                if detection['class_name'] == 'person' else detection.get('model_class_name', 'excavator'))
                        label = f"{name} {detection['confidence']:.2f}"
                        cv2.putText(frame, label, (x1, max(45, y1-5)), cv2.FONT_HERSHEY_SIMPLEX, .5, color, 1)
                        anchor = person.get('anchor')
                        if anchor:
                            cv2.circle(frame, tuple(int(round(v)) for v in anchor), 4, color, -1)
                    label=assessment.get('state') if assessment.get('state') in {'SAFE','DANGER'} else 'UNKNOWN'
                    cv2.putText(frame, f'{cid} | {label}', (10, 24),
                                cv2.FONT_HERSHEY_SIMPLEX, .6, (70,70,255) if label=='DANGER' else (100,210,255), 2)
                    ok, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.config['jpeg_quality']])
                    if not ok:
                        raise RuntimeError('JPEG 인코딩 실패')
                    with self.state.changed:
                        self.state.jpegs[cid] = (signature, jpg.tobytes())
                        self.state.changed.notify_all()
                except Exception as exc:
                    self.state.event('jpeg_failed', camera_id=cid, error=str(exc))
            self.stop_event.wait(1.0/self.config['stream_fps'])

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)


def make_app(state):
    from flask import Flask, Response, jsonify, request, render_template
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 16384
    frozen = {}
    manual_events = ManualEvents(state.recorder)
    app.extensions['manual_events'] = manual_events

    @app.before_request
    def validate_admin_request():
        protected = request.path.startswith('/api/admin/') or (
            request.path.startswith('/api/calibration/') and request.method == 'POST')
        if not protected:
            return None
        if request.method == 'POST' and not request.is_json:
            return jsonify(error='JSON required'), 415
        origin = request.headers.get('Origin')
        if origin and urlsplit(origin).netloc != request.host:
            return jsonify(error='Cross-origin admin request rejected'), 403

    @app.after_request
    def admin_cache(response):
        if request.path.startswith('/api/admin/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.post('/api/audio/explosion')
    def audio_explosion():
        if request.remote_addr not in ('127.0.0.1', '::1'):
            return jsonify(error='Local audio events only'), 403
        try:
            accepted = state.record_audio_explosion(request.get_json(silent=True))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        return jsonify(accepted=accepted)

    @app.route('/api/admin/events', methods=['GET', 'POST'])
    def test_events():
        if request.method == 'GET':
            return jsonify(manual_events.snapshot())
        try:
            return jsonify(manual_events.send(request.get_json(silent=True)))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

    @app.post('/api/admin/reset')
    def reset_hazard():
        body = request.get_json(silent=True)
        if (not isinstance(body, dict) or set(body) != {'episode_id', 'confirm_all_workers_safe'}
                or not isinstance(body['episode_id'], str) or not body['episode_id']
                or body['confirm_all_workers_safe'] is not True):
            state.event('admin_reset_requested', episode_id=body.get('episode_id') if isinstance(body, dict) else None)
            state.event('admin_reset_validation', accepted=False, reason='INVALID_REQUEST')
            return jsonify(error='현재 위험 이력과 모든 작업자의 이탈 확인이 필요합니다.'), 400
        try:
            return jsonify(state.reset_hazard(body['episode_id'], body['confirm_all_workers_safe']))
        except ValueError as exc:
            return jsonify(error=str(exc)), 409

    @app.get('/api/admin/resources')
    def resources():
        directory = getattr(state.recorder, 'directory', None)
        sample = None
        error = None
        if directory is not None:
            try:
                with (Path(directory) / 'resources.csv').open('rb') as stream:
                    header = stream.readline().decode('utf-8')
                    start = max(stream.tell(), stream.seek(0, 2) - 16384)
                    stream.seek(start)
                    if start > len(header.encode('utf-8')):
                        stream.readline()
                    rows = list(csv.DictReader(io.StringIO(header + stream.read().decode('utf-8'))))
                for row in reversed(rows):
                    if not row.get('timestamp_ns'):
                        continue
                    age_ms = (time.monotonic_ns() - int(row['timestamp_ns'])) / 1e6
                    sample = {'timestamp_ns': row['timestamp_ns'], 'age_ms': age_ms,
                              'stale': age_ms < 0 or age_ms > 5000}
                    for key in ['cpu_system_percent', 'gpu_percent', 'ram_used_bytes', 'ram_total_bytes', 'process_rss_bytes']:
                        value = float(row[key]) if row.get(key) else None
                        sample[key] = value if value is not None and math.isfinite(value) else None
                    break
            except FileNotFoundError:
                pass
            except (OSError, ValueError, UnicodeError, csv.Error) as exc:
                sample = None
                error = str(exc)
        return jsonify(mode=state.recorder.mode, sample=sample, error=error)

    @app.get('/api/calibration')
    def calibration_status():
        return jsonify({cid: state.calibrations.status(cid) for cid in state.calibrations.specs})

    @app.get('/api/calibration/<camera_id>/profiles')
    def calibration_profiles(camera_id):
        try:
            return jsonify(camera_id=camera_id, profiles=state.calibrations.list_profiles(camera_id))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

    @app.get('/api/calibration/<camera_id>/profiles/<profile_id>')
    def calibration_profile(camera_id, profile_id):
        try:
            return jsonify(state.calibrations.load_profile(camera_id, profile_id))
        except FileNotFoundError:
            return jsonify(error='Calibration profile not found'), 404
        except (ValueError, TypeError, KeyError, OSError) as exc:
            return jsonify(error=str(exc)), 400

    @app.get('/api/calibration/frozen/<token>')
    def calibration_image(token):
        with state.lock:
            snap = frozen.get(token)
            if snap is None or time.monotonic() - snap['created'] > 120:
                return jsonify(error='Calibration frame expired'), 410
            return Response(snap['jpeg'], mimetype='image/jpeg', headers={'Cache-Control': 'no-store'})

    @app.post('/api/calibration/<camera_id>/<action>')
    def calibration_action(camera_id, action):
        edits = {'preview', 'save', 'profile-preview', 'profile-save'}
        if camera_id not in state.calibrations.specs or action not in edits | {'freeze', 'reload', 'reset'}:
            return jsonify(error='Unknown camera or action'), 404
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error='JSON object required'), 400
        try:
            with state.lock:
                if not state.calibrations.enabled:
                    raise ValueError('Homography is disabled')
                if action in edits | {'freeze'}:
                    now = time.monotonic_ns()
                    if not state._risk_views(now)[camera_id]['valid']:
                        raise ValueError('A fresh camera observation is required')
                    frame, result = state.views[camera_id]
                    height, width = frame.shape[:2]
                    spec = state.calibrations.specs[camera_id]
                    if (width, height) != (spec['width'], spec['height']):
                        raise ValueError('Camera resolution mismatch')
                if action == 'freeze':
                    import cv2
                    ok, jpeg = cv2.imencode('.jpg', frame)
                    if not ok:
                        raise ValueError('JPEG encoding failed')
                    for token in list(frozen):
                        if time.monotonic() - frozen[token]['created'] > 120:
                            del frozen[token]
                    if len(frozen) >= 8:
                        del frozen[next(iter(frozen))]
                    token = secrets.token_hex(24)
                    frozen[token] = {'created': time.monotonic(), 'camera_id': camera_id,
                        'revision': state.calibrations.status(camera_id)['revision'], 'jpeg': jpeg.tobytes(),
                        'size': (width, height), 'frame_seq': result['frame_seq']}
                    return jsonify(token=token, width=width, height=height, frame_seq=result['frame_seq'],
                                   image_url='/api/calibration/frozen/' + token)
                if action in edits:
                    snap = frozen.get(body.get('token'))
                    if (not snap or time.monotonic() - snap['created'] > 120
                            or snap['camera_id'] != camera_id or snap['size'] != (width, height)):
                        raise ValueError('Freeze a new calibration frame')
                    if snap['revision'] != state.calibrations.status(camera_id)['revision']:
                        raise ValueError('Calibration changed; freeze a new frame')
                    if action in {'profile-preview', 'profile-save'}:
                        profile = body.get('profile')
                        if action == 'profile-preview':
                            return jsonify(state.calibrations.preview_profile(camera_id, profile))
                        status = state.calibrations.save_profile(camera_id, profile, body.get('profile_revision'))
                        del frozen[body['token']]
                        return jsonify(status)
                    points = body.get('points')
                    order = body.get('corner_order', 'ABCD')
                    if order not in {'ABCD', 'DCBA'}:
                        raise ValueError('Unknown corner order')
                    if not isinstance(points, list) or len(points) != 4:
                        raise ValueError('Four corner points are required')
                    points = points[::-1] if order == 'DCBA' else points
                    if action == 'preview':
                        from ground import make_homography, WORLD
                        matrix = make_homography(points, snap['size'])
                        return jsonify(image_points=points, world_xy_m=WORLD.tolist(),
                                       matrix=matrix.tolist(), physical_alignment_verified=False,
                                       transform_valid=True, quality_evaluated=False, quality_approved=False)
                    status = state.change_calibration(camera_id, action, snap['revision'], points)
                    del frozen[body['token']]
                else:
                    revision = body.get('revision')
                    if not isinstance(revision, int) or isinstance(revision, bool):
                        raise ValueError('Calibration revision required')
                    status = state.change_calibration(camera_id, action, revision)
                return jsonify(status)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            return jsonify(error=str(exc)), 400

    @app.get('/')
    def index():
        return render_template('dashboard.html', cameras=state.config['cameras'])

    @app.get('/admin')
    @app.get('/diagnostics')
    def diagnostics():
        return render_template('diagnostics.html', cameras=state.config['cameras'])

    @app.get('/api/status')
    def status():
        return jsonify(state.snapshot())

    @app.get('/api/vision/events')
    def vision_events():
        after = request.args.get('after', '0')
        run_id = request.args.get('run_id')
        if (set(request.args) - {'after', 'run_id'} or len(after) > 20
                or not after.isascii() or not after.isdigit()
                or (run_id is not None and len(run_id) > 128)):
            return jsonify(error='Invalid event cursor'), 400
        response = jsonify(state.integration_snapshot(int(after), run_id))
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/video_feed/<camera_id>')
    def video(camera_id):
        if camera_id not in {c['id'] for c in state.config['cameras']}:
            return '카메라 없음', 404

        def generate():
            last = None
            while state.running:
                with state.changed:
                    state.changed.wait_for(lambda: not state.running or
                        (state.jpegs.get(camera_id) is not None and state.jpegs[camera_id][0] != last), timeout=1)
                    current = state.jpegs.get(camera_id)
                    if not state.running:
                        break
                    if current is None or current[0] == last:
                        continue
                    last, jpg = current
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n'
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame',
                        headers={'Cache-Control': 'no-store'})

    return app
