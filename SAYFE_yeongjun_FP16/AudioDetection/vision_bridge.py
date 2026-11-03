"""Forward audio onsets to the local Vision heartbeat process."""
import json
from queue import Empty, Full, Queue
import threading
from urllib.request import Request, urlopen

ZONES = {'CAM1': 'A', 'CAM2': 'A', 'CAM3': 'B'}


def audio_event_payload(event):
    if event.get('kind') != 'audio_danger_started':
        return None
    zone = ZONES.get(event.get('camera_id'))
    label = event.get('label', '')
    if not zone or label != 'Explosion':
        return None
    return {'event_id': event['event_id'], 'camera_id': event['camera_id'],
            'zone': zone, 'event': f'{zone}_EXPLOSION', 'label': label,
            'score': event['score'], 'occurred_at': event['time']}


def explosion_payload(event):
    if event.get('kind') != 'audio_danger_started' or event.get('label') != 'Explosion':
        return None
    payload = {key: event[key] for key in ('event_id', 'camera_id', 'label', 'score')}
    payload['event'] = 'Explosion'
    payload['occurred_at'] = event['time']
    return payload


class InProcessAudioEventPublisher:
    """Deliver zone audio onsets to Vision state when both run in main.py."""
    def __init__(self, receiver):
        self.receiver = receiver
        self.sent_count = 0
        self.last_error = None

    def submit(self, event):
        payload = audio_event_payload(event)
        if payload is None:
            return
        try:
            self.receiver(payload)
            self.sent_count += 1
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)[:512]

    def snapshot(self):
        return {'sent_count': self.sent_count, 'pending': 0, 'last_error': self.last_error}


InProcessExplosionPublisher = InProcessAudioEventPublisher


class ExplosionPublisher:
    def __init__(self, port=5010, timeout=0.5):
        self.url = f'http://127.0.0.1:{port}/api/audio/explosion'
        self.timeout = timeout
        self.queue = Queue(maxsize=64)
        self.stop_event = threading.Event()
        self.thread = None
        self.last_error = None
        self.sent_count = 0

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name='audio-explosion-publisher', daemon=True)
        self.thread.start()

    def submit(self, event):
        payload = explosion_payload(event)
        if payload is None:
            return
        try:
            self.queue.put_nowait(payload)
        except Full:
            self.last_error = 'Explosion forwarding queue full'

    def snapshot(self):
        return {'sent_count': self.sent_count, 'pending': self.queue.qsize(),
                'last_error': self.last_error}

    def _run(self):
        while not self.stop_event.is_set():
            try:
                payload = self.queue.get(timeout=0.2)
            except Empty:
                continue
            data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8')
            request = Request(self.url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
            while not self.stop_event.is_set():
                try:
                    with urlopen(request, timeout=self.timeout) as response:
                        if response.status != 200:
                            raise OSError(f'Vision event endpoint returned {response.status}')
                    self.sent_count += 1
                    self.last_error = None
                    break
                except Exception as exc:
                    self.last_error = str(exc)[:512]
                    self.stop_event.wait(1)
            self.queue.task_done()

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=self.timeout + 1.5)
