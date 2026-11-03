"""Vision TCP heartbeat sender with risk and Explosion telemetry.

The v1 heartbeat envelope and health fields stay compatible with the receiver.
All ages are computed on this device; sent_at is for display only.
"""
from collections import deque
from collections.abc import Mapping
from datetime import datetime
import json
import math
import socket
import threading
import time
import uuid

PROTOCOL_VERSION = 1
MESSAGE_TYPE = 'VISION_HEARTBEAT'
DEFAULTS = dict(enabled=False, target_host='192.168.100.2', target_port=8766,
                interval_sec=1.0, component_timeout_sec=2.5,
                connect_timeout_sec=0.5, node_id='vision-jetson')
MAX_LINE_BYTES = 64 * 1024


def validate_settings(settings):
    if not isinstance(settings, dict) or set(settings) - set(DEFAULTS):
        raise ValueError('Invalid heartbeat settings')
    result = {**DEFAULTS, **settings}
    if not isinstance(result['enabled'], bool):
        raise ValueError('heartbeat.enabled must be boolean')
    port = result['target_port']
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError('Invalid heartbeat target_port')
    for key in ('target_host', 'node_id'):
        if not isinstance(result[key], str) or not result[key].strip():
            raise ValueError('Invalid heartbeat ' + key)
    for key in ('interval_sec', 'component_timeout_sec', 'connect_timeout_sec'):
        value = result[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('Invalid heartbeat ' + key)
    return result


def _number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) and value >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _age(now, stamp):
    return None if stamp is None or stamp > now else (now - stamp) / 1e9


class DualCameraHealthProbe:
    """Read actual capture progress and separately record successful YOLO returns.

    The sender never holds the progress lock during camera sampling or network I/O.
    Camera lock acquisition is bounded so a stuck capture worker cannot hide faults.
    """
    def __init__(self, cameras, component_timeout_sec=2.5, *, mono_ns=time.monotonic_ns):
        self.cameras = dict(cameras)
        if len(self.cameras) != 2:
            raise ValueError('Heartbeat requires two cameras')
        validate_settings({'component_timeout_sec': component_timeout_sec})
        self.component_timeout_sec = component_timeout_sec
        self._mono_ns = mono_ns
        self._started_ns = mono_ns()
        self._lock = threading.Lock()
        self._progress = {cid: dict(last_success_ns=None, success_count=0,
                                   source_frame_seq=None, inference_ms=None,
                                   inference_error=None, ticks=deque()) for cid in cameras}

    def mark_inference_complete(self, camera_id, frame_seq, result):
        # Detector timestamp includes extraction; it is local monotonic_ns, never wall time.
        stamp = int(result['inference_end_ns'])
        duration = _number(result.get('inference_ms'))
        with self._lock:
            row = self._progress[camera_id]
            row.update(last_success_ns=stamp, source_frame_seq=int(frame_seq),
                       success_count=row['success_count'] + 1,
                       inference_ms=duration, inference_error=None)
            row['ticks'].append(stamp)
            while row['ticks'] and stamp - row['ticks'][0] > 2_000_000_000:
                row['ticks'].popleft()

    def mark_inference_fault(self, camera_id, reason):
        with self._lock:
            self._progress[camera_id]['inference_error'] = str(reason)[:512]

    def _capture(self, camera):
        # Read the same fields camera.health() uses, without an unbounded lock wait.
        if not camera.lock.acquire(timeout=0.01):
            return dict(camera_ok=False, camera_age_sec=None, capture_count=None,
                        camera_error='capture state lock unavailable')
        try:
            stamp, count = camera.timestamp_ns, camera.seq
            opened, error = camera.opened, camera.error
            stopped = camera.stop_event.is_set()
            alive = bool(camera.thread and camera.thread.is_alive())
        finally:
            camera.lock.release()
        age = _age(self._mono_ns(), stamp)
        reason = ('capture stopped' if stopped else str(error)[:512] if error else
                  'capture worker unavailable' if not opened or not alive else
                  'no captured frame' if age is None or not count else
                  'capture progress stale' if age > self.component_timeout_sec else None)
        return dict(camera_ok=reason is None, camera_age_sec=age,
                    capture_count=count, camera_error=reason)

    def report(self):
        with self._lock:
            progress = {cid: {**row, 'ticks': tuple(row['ticks'])}
                        for cid, row in self._progress.items()}
        # Timestamp after copying: a completion racing this sample is not a future result.
        now = self._mono_ns()
        cameras = {}
        span = max(0.001, min(2.0, (now - self._started_ns) / 1e9))
        for cid, camera in self.cameras.items():
            try:
                capture = self._capture(camera)
            except Exception as exc:
                capture = dict(camera_ok=False, camera_age_sec=None, capture_count=None,
                               camera_error='capture state unavailable: ' + str(exc)[:512])
            row = progress[cid]
            age = _age(now, row['last_success_ns'])
            error = row['inference_error']
            fresh = age is not None and age <= self.component_timeout_sec
            inference_ok = fresh and error is None
            # No successful result with no input is not evidence of an engine failure.
            reason = ('DETECTOR_ERROR' if error else
                      None if inference_ok else
                      'INPUT_UNAVAILABLE' if not capture['camera_ok'] else
                      'NO_SUCCESSFUL_INFERENCE' if age is None else 'INFERENCE_PROGRESS_STALE')
            detail = error or (reason if reason is not None else None)
            cameras[cid] = {**capture, 'inference_ok': inference_ok,
                'inference_age_sec': age, 'inference_error': detail,
                'inference_reason': reason, 'inference_success_count': row['success_count'],
                'source_frame_seq': row['source_frame_seq'],
                'fps': round(sum(0 <= now - t <= 2_000_000_000 for t in row['ticks']) / span, 2),
                'inference_ms': row['inference_ms']}
        def oldest(field):
            values = [row[field] for row in cameras.values()]
            return None if any(value is None for value in values) else round(max(values), 3)
        def errors(field):
            return '; '.join(f'{cid}: {row[field]}' for cid, row in cameras.items() if row[field]) or None
        newest = max(progress.values(), key=lambda row: row['last_success_ns'] or -1)
        health = dict(camera_ok=all(row['camera_ok'] for row in cameras.values()),
            inference_ok=all(row['inference_ok'] for row in cameras.values()),
            camera_age_sec=oldest('camera_age_sec'), inference_age_sec=oldest('inference_age_sec'),
            camera_error=errors('camera_error'), inference_error=errors('inference_error'),
            frame_seq=sum(row['success_count'] for row in progress.values()),
            fps=round(sum(row['fps'] for row in cameras.values()), 2),
            inference_ms=newest['inference_ms'], component_timeout_sec=self.component_timeout_sec)
        return {'health': health, 'vision': {'cameras': cameras}}

    def snapshot(self):
        return self.report()['health']


class VisionHeartbeatSender:
    """Persistent, no-ACK JSON-lines sender. Only its own worker performs I/O."""
    def __init__(self, probe, *, target_host='192.168.100.2', target_port=8766,
                 interval_sec=1.0, node_id='vision-jetson', telemetry_provider=None,
                 connect_timeout_sec=0.5):
        validate_settings(dict(target_host=target_host, target_port=target_port,
                               interval_sec=interval_sec, node_id=node_id,
                               connect_timeout_sec=connect_timeout_sec))
        self.probe = probe
        self.target_host, self.target_port = target_host, target_port
        self.interval_sec, self.node_id = interval_sec, node_id
        self.telemetry_provider = telemetry_provider
        self.connect_timeout_sec = connect_timeout_sec
        self.boot_id = str(uuid.uuid4())
        self._sequence = 0
        self._stop_event = threading.Event()
        self._thread = None
        self._socket = None
        self._socket_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self.last_error = None
        self.sent_count = 0

    def _payload(self):
        self._sequence += 1
        safe_telemetry = {}
        try:
            if isinstance(self.probe, DualCameraHealthProbe):
                report = self.probe.report()
                health, telemetry = report['health'], report['vision']
            else:
                health, telemetry = self.probe.snapshot(), {}
            safe_telemetry = telemetry
        except Exception as exc:
            health = dict(camera_ok=False, inference_ok=False, camera_error='health probe unavailable',
                          inference_error=str(exc)[:512])
            telemetry = {}
        if self.telemetry_provider is not None:
            try:
                value = self.telemetry_provider()
                if isinstance(value, Mapping):
                    telemetry = {**telemetry, **value}
                json.dumps(telemetry, allow_nan=False)
            except Exception as exc:
                telemetry = {**safe_telemetry,
                             'telemetry_error': str(exc)[:512]}
        return dict(protocol_version=PROTOCOL_VERSION, type=MESSAGE_TYPE, node_id=self.node_id,
                    boot_id=self.boot_id, seq=self._sequence,
                    sent_at=datetime.now().astimezone().isoformat(timespec='milliseconds'),
                    health=health, vision=telemetry, control_command=None)

    def _close_socket(self):
        with self._socket_lock:
            connection, self._socket = self._socket, None
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                connection.close()
            except OSError:
                pass

    def _connection(self):
        with self._socket_lock:
            if self._socket is not None:
                return self._socket
        # Never hold the socket lock during connect: stop() must remain responsive.
        connection = socket.create_connection((self.target_host, self.target_port),
                                              timeout=self.connect_timeout_sec)
        try:
            connection.settimeout(self.connect_timeout_sec)
            with self._socket_lock:
                if self._stop_event.is_set():
                    raise OSError('heartbeat sender stopped')
                self._socket = connection
        except Exception:
            connection.close()
            raise
        return connection

    def send_once(self):
        with self._send_lock:
            data = (json.dumps(self._payload(), ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
            if len(data) - 1 > MAX_LINE_BYTES:
                raise ValueError('heartbeat frame exceeds receiver limit')
            try:
                self._connection().sendall(data)
                self.sent_count += 1
                self.last_error = None
            except OSError:
                self._close_socket()
                raise

    def _run(self):
        deadline = time.monotonic()
        try:
            while not self._stop_event.is_set():
                try:
                    self.send_once()
                except Exception as exc:
                    # Network and telemetry failures must never escape into the vision worker.
                    error = str(exc)[:512]
                    if error != self.last_error:
                        print('[SAYFE VISION HB] send failed: ' + error, flush=True)
                    self.last_error = error
                deadline += self.interval_sec
                now = time.monotonic()
                if deadline <= now:
                    deadline += (math.floor((now - deadline) / self.interval_sec) + 1) * self.interval_sec
                self._stop_event.wait(max(0.0, deadline - now))
        finally:
            self._close_socket()

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name='sayfe-vision-heartbeat-sender', daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._close_socket()
        if self._thread is not None:
            self._thread.join(timeout=2 * self.connect_timeout_sec + 1)
        return not bool(self._thread and self._thread.is_alive())


def make_sender(settings, pipeline):
    """Configure the observer before pipeline.start(); disabled means no observer or socket."""
    settings = validate_settings(settings)
    if not settings['enabled']:
        return None
    probe = DualCameraHealthProbe(pipeline.cameras, settings['component_timeout_sec'])
    sender = VisionHeartbeatSender(probe, **{key: settings[key] for key in
        ('target_host', 'target_port', 'interval_sec', 'node_id', 'connect_timeout_sec')})
    pipeline.health_probe = probe
    return sender
