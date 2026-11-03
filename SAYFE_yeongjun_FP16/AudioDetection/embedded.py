"""AudioDetection lifecycle inside the Vision Python process."""
from datetime import datetime
import json
import threading
import uuid

from .core import AudioState, Journal
from .runtime import AudioRuntime
from .settings import ROOT
from .vision_bridge import InProcessAudioEventPublisher


class EmbeddedAudio:
    def __init__(self, config, vision_state, web_enabled=True):
        self.config = config
        self.vision_state = vision_state
        self.web_enabled = web_enabled
        self.journal = None
        self.state = None
        self.runtime = None
        self.server = None
        self.server_thread = None
        self.zone_server = None
        self.zone_server_thread = None
        self.camera3 = None

    def start(self):
        name = datetime.now().strftime('%Y%m%dT%H%M%S') + '_' + uuid.uuid4().hex[:8]
        self.journal = Journal(ROOT / 'runs' / name)
        try:
            (self.journal.directory / 'config.json').write_text(
                json.dumps(self.config, ensure_ascii=False, indent=2))
            self.state = AudioState(self.config, self.journal)
            self.state.explosion_publisher = InProcessAudioEventPublisher(
                self.vision_state.record_audio_event)
            self.runtime = AudioRuntime(self.config, self.state)
            if self.web_enabled:
                from werkzeug.serving import make_server
                from .web import make_app
                from .zone_web import Camera3Video, make_app as make_zone_app
                self.server = make_server(self.config['host'], self.config['port'],
                                          make_app(self.state), threaded=True)
                self.server.daemon_threads = True
                camera3_spec = next((c for c in self.config['cameras'] if c['id'] == 'CAM3'), None)
                if camera3_spec:
                    self.camera3 = Camera3Video(camera3_spec)
                    self.zone_server = make_server(self.config['host'], self.config['zone_port'],
                        make_zone_app(self.state, self.vision_state, self.camera3), threaded=True)
                    self.zone_server.daemon_threads = True
                self.server_thread = threading.Thread(target=self.server.serve_forever,
                                                      name='audio-web-server', daemon=True)
                self.server_thread.start()
                if self.zone_server:
                    self.zone_server_thread = threading.Thread(target=self.zone_server.serve_forever,
                        name='zone-web-server', daemon=True)
                    self.zone_server_thread.start()
                    self.camera3.start()
            self.runtime.start()
            page = f"{self.config['port']} 화면" if self.web_enabled else '웹 비활성'
            print(f"[AUDIO] 동일 프로세스 실행 / {page} / {self.journal.directory}", flush=True)
            if self.zone_server:
                print(f"[AUDIO] A/B 구역 화면 http://<Jetson-IP>:{self.config['zone_port']}", flush=True)
        except Exception:
            self.stop()
            raise

    def stop(self):
        if self.camera3:
            self.camera3.stop()
            self.camera3 = None
        if self.zone_server:
            self.zone_server.shutdown()
            self.zone_server.server_close()
            self.zone_server = None
        if self.zone_server_thread:
            self.zone_server_thread.join(timeout=3)
            self.zone_server_thread = None
        if self.runtime:
            self.runtime.close()
            self.runtime = None
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.server_thread:
            self.server_thread.join(timeout=3)
            self.server_thread = None
        if self.journal:
            if self.state:
                (self.journal.directory / 'summary.json').write_text(
                    json.dumps(self.state.snapshot(), ensure_ascii=False, indent=2))
            self.journal.close()
            self.journal = None
