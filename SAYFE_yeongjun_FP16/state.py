from collections import deque
from copy import deepcopy
from dataclasses import replace
import json
import threading
import time

from ground import CalibrationStore
from observations import build_frame_observation
from risk import RiskEngine
from tracking import observed_ids


class RuntimeState:
    def __init__(self, config, recorder):
        self.config = config
        self.recorder = recorder
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.started_ns = time.monotonic_ns()
        self.running = True
        self.inference_alive = False
        self.pipeline_error = None
        self.cameras = {}
        self.results = {}
        self.views = {}
        self.frame_observations = {}
        self.jpegs = {}
        self.recent = deque(maxlen=30)
        self.integration_events = deque(maxlen=100)
        self.integration_sequence = 0
        self.integration_lock = threading.Lock()
        self.rates = {c['id']: deque() for c in config['cameras']}
        self.risk_engine = RiskEngine(self.rates, config['risk']['enter_confirm_frames'], config.get('tracking'),
                                      config['observation']['stale_seconds'],
                                      config['risk'].get('camera_state_hold_seconds', 1.))
        self.calibrations = CalibrationStore(config['cameras'], config.get('homography', {}))
        self.scheduler = None
        self.excavator_ble = None
        self.audio_state = None
        self.reset_pending_episode = None
        self.reset_result_status = None
        self.audio_explosions = deque(maxlen=20)
        self.audio_explosion_ids = set()
        self.audio_events = deque(maxlen=40)
        self.audio_event_ids = set()

    def record_audio_event(self, payload):
        from AudioDetection.vision_bridge import ZONES
        if (not isinstance(payload, dict)
                or set(payload) != {'event_id', 'camera_id', 'zone', 'event', 'label', 'score', 'occurred_at'}
                or not isinstance(payload['event_id'], str) or not payload['event_id']
                or payload['camera_id'] not in ZONES
                or payload['zone'] != ZONES[payload['camera_id']]
                or not isinstance(payload['label'], str)
                or payload['label'] != 'Explosion'
                or payload['event'] != f"{payload['zone']}_EXPLOSION"
                or isinstance(payload['score'], bool) or not isinstance(payload['score'], (int, float))
                or not 0 <= payload['score'] <= 1
                or not isinstance(payload['occurred_at'], str) or not payload['occurred_at']):
            raise ValueError('Invalid zone audio event')
        with self.lock:
            if payload['event_id'] in self.audio_event_ids:
                return False
            if len(self.audio_events) == self.audio_events.maxlen:
                self.audio_event_ids.discard(self.audio_events[0][0]['event_id'])
            self.audio_events.append((dict(payload), time.monotonic_ns()))
            self.audio_event_ids.add(payload['event_id'])
        if payload['label'] == 'Explosion':
            self.record_audio_explosion({key: payload[key] for key in
                ('event_id', 'camera_id', 'label', 'score', 'occurred_at')} | {'event': 'Explosion'})
        return True

    def record_audio_explosion(self, payload):
        if (not isinstance(payload, dict) or set(payload) != {'event_id', 'camera_id', 'label', 'event', 'score', 'occurred_at'}
                or not isinstance(payload['event_id'], str) or not payload['event_id']
                or not isinstance(payload['camera_id'], str) or not payload['camera_id']
                or payload['label'] != 'Explosion'
                or payload['event'] != 'Explosion'
                or isinstance(payload['score'], bool) or not isinstance(payload['score'], (int, float))
                or not 0 <= payload['score'] <= 1
                or not isinstance(payload['occurred_at'], str) or not payload['occurred_at']):
            raise ValueError('Invalid Explosion event')
        with self.lock:
            if payload['event_id'] in self.audio_explosion_ids:
                return False
            if len(self.audio_explosions) == self.audio_explosions.maxlen:
                self.audio_explosion_ids.discard(self.audio_explosions[0][0]['event_id'])
            self.audio_explosions.append((dict(payload), time.monotonic_ns()))
            self.audio_explosion_ids.add(payload['event_id'])
            return True

    def heartbeat_telemetry(self):
        now = time.monotonic_ns()
        with self.lock:
            decision = self.risk_engine.project(self._risk_views(now), now)
            risk = {'state': decision['risk'], 'site_state': decision['site_state'],
                    'hazard_latched': decision['hazard_latched'],
                    'episode_id': decision['episode_id'], 'reasons': decision['reasons'],
                    'event': 'DANGER' if decision['risk'] == 'DANGER' else None}
            explosions = [dict(event) for event, received in self.audio_explosions
                          if 0 <= now - received <= 60_000_000_000]
            audio_events = [dict(event) for event, received in self.audio_events
                            if 0 <= now - received <= 60_000_000_000]
        return {'final_risk': risk, 'audio_explosions': explosions,
                'audio_events': audio_events}

    def event(self, kind, **fields):
        if kind == 'hazard_latched':
            self.reset_result_status = None
        if self.excavator_ble:
            if kind == 'vision_risk_changed' and fields.get('risk') == 'DANGER':
                if self.reset_pending_episode is not None:
                    episode = self.reset_pending_episode
                    self.reset_pending_episode = None
                    self.reset_result_status = 'RESTRICTION_RETAINED'
                    self.event('admin_reset_transmission', episode_id=episode, status='ABORTED', reason='NEW_DANGER')
                    self.event('admin_reset_ack', episode_id=episode, status='UNVERIFIED')
                    self.event('admin_reset_release_result', episode_id=episode,
                               status='RESTRICTION_RETAINED', reason='NEW_DANGER')
                self.excavator_ble.submit('DANGER', fields.get('event_id'))
        entry = self.recorder.event(kind, **fields)
        with self.lock:
            self.recent.append(entry)
        if kind in {'hazard_latched', 'hazard_reset'}:
            evidence = fields.get('trigger_evidence', {})
            intrusion = any(p.get('zone_inside') is True
                            for camera in evidence.values() for p in camera.get('persons', []))
            reason = ('MANUAL_RESET' if kind == 'hazard_reset' else
                      'PERSON_IN_EXCAVATOR_DANGER_BOX' if intrusion else 'FUSED_PERSON_DANGER')
            with self.integration_lock:
                self.integration_sequence += 1
                self.integration_events.append({
                    'schema_version': 1, 'sequence': self.integration_sequence,
                    'run_id': self.recorder.run_id, 'event': kind, 'source': 'vision',
                    'site_state': 'SAFE' if kind == 'hazard_reset' else 'DANGER',
                    'reason': reason, 'episode_id': entry['event_id'], 'event_id': entry['event_id'],
                    'record_id': entry.get('record_id'), 'timestamp': entry.get('time_kst'),
                    'timestamp_ns': entry.get('timestamp_ns'),
                })

    def integration_snapshot(self, after=0, run_id=None):
        with self.integration_lock:
            oldest = self.integration_events[0]['sequence'] if self.integration_events else 1
            reset = run_id not in (None, self.recorder.run_id) or after > self.integration_sequence
            cursor = 0 if reset else after
            return {'schema_version': 1, 'run_id': self.recorder.run_id,
                    'latest_sequence': self.integration_sequence, 'oldest_sequence': oldest,
                    'reset_required': reset, 'gap': cursor < oldest - 1,
                    'events': [dict(event) for event in self.integration_events if event['sequence'] > cursor]}

    def publish(self, camera_id, frame, result):
        with self.changed:
            current = self.results.get(camera_id)
            if current is not None and current['frame_seq'] > result['frame_seq']:
                result['publication_status'] = 'SUPERSEDED'
                return None
            ground = result['ground']
            revision, calibration_id = self.calibrations.identity(camera_id)
            if (ground['calibration']['revision'] != revision or
                    ground['calibration'].get('calibration_id') != calibration_id):
                result['publication_status'] = 'SUPERSEDED'
                return None
            self.risk_engine.tracker.update(ground, result['risk_assessment'])
            self.frame_observations[camera_id] = build_frame_observation(ground, result['risk_assessment'])
            # Record both the current visible number and the stable track key.
            result['ground_details_json'] = json.dumps(ground, ensure_ascii=False, separators=(',', ':'))
            result['risk_details_json'] = json.dumps(result['risk_assessment'], ensure_ascii=False, separators=(',', ':'))
            result['publication_status'] = 'PUBLISHED'
            self.results[camera_id] = result
            self.views[camera_id] = (frame, result)
            ticks = self.rates[camera_id]
            ticks.append(result['result_ns'])
            while ticks and result['result_ns']-ticks[0] > 2_000_000_000:
                ticks.popleft()
            self.changed.notify_all()
            return self.refresh_risk()

    def get_frame_observation(self, camera_id):
        with self.lock:
            frame = self.frame_observations.get(camera_id)
            if frame is None:
                return None
            now = time.monotonic_ns()
            views = self._risk_views(now)
            labels = self._camera_labels(camera_id, now, views)
            return replace(frame, persons=tuple(replace(p, person_id=labels.get(p.track_id or p.person_id))
                                               for p in frame.persons))

    def _camera_labels(self, camera_id, now, views):
        own_view = {camera_id:views.get(camera_id,{})}
        return self.risk_engine.tracker.label_map(
            now, observed_ids(own_view), observed_ids(own_view,True), camera_id=camera_id)

    def _label_result(self, result, labels):
        ground, assessment = result.get('ground'), result.get('risk_assessment')
        if ground is None or assessment is None:
            return False
        before = [p.get('person_id') for p in assessment['persons']]
        self.risk_engine.tracker.apply_labels(ground['persons'], labels)
        self.risk_engine.tracker.apply_labels(assessment['persons'], labels)
        changed = before != [p.get('person_id') for p in assessment['persons']]
        if changed:
            result['ground_details_json'] = json.dumps(ground, ensure_ascii=False, separators=(',', ':'))
            result['risk_details_json'] = json.dumps(assessment, ensure_ascii=False, separators=(',', ':'))
        return changed

    def change_calibration(self, cid, action, revision, points=None):
        with self.changed:
            if cid not in self.cameras or cid not in self.calibrations.specs:
                raise ValueError('Unknown camera')
            if not self.calibrations.enabled:
                raise ValueError('Homography is disabled')
            if self.calibrations.status(cid)['revision'] != revision:
                raise ValueError('Calibration changed; reload status')
            if action == 'save':
                status = self.calibrations.save(cid, points, revision)
            elif action == 'reset':
                status = self.calibrations.reset(cid, revision)
            elif action == 'reload':
                status = self.calibrations.reload(cid)
            else:
                raise ValueError('Unknown calibration action')
            self.frame_observations.pop(cid, None)
            self.risk_engine.tracker.invalidate_camera(cid)
            self.refresh_risk()
            self.event('calibration_changed', camera_id=cid, action=action, revision=status['revision'])
            self.changed.notify_all()
            return status

    def _risk_views(self, now):
        views = {}
        for spec in self.config['cameras']:
            cid = spec['id']
            result = self.results.get(cid)
            health = self.cameras[cid].health(now) if cid in self.cameras else {
                'health': 'WAITING', 'capture_fps': 0., 'error': '캡처 준비 중'}
            age = (now-result['capture_ns'])/1e9 if result else None
            reasons = []
            if not self.running:
                reasons.append('PROCESS_STOPPED')
            if not self.inference_alive or self.pipeline_error:
                reasons.append('INFERENCE_UNAVAILABLE')
            if health['health'] != 'OBSERVING':
                reasons.append('CAMERA_'+health['health'])
            if result is None:
                reasons.append('NO_RESULT')
            elif result.get('error'):
                reasons.append('INFERENCE_FAILED')
            if age is not None and not 0 <= age <= self.config['observation']['stale_seconds']:
                reasons.append('RESULT_STALE')
            ground = (result or {}).get('ground')
            revision, calibration_id = self.calibrations.identity(cid)
            if ground and (ground['calibration']['revision'] != revision or
                           ground['calibration'].get('calibration_id') != calibration_id):
                reasons.append('CALIBRATION_CHANGED')
            assessment = (result or {}).get('risk_assessment')
            if not assessment:
                reasons.append('NO_ASSESSMENT')
            valid = not reasons
            views[cid] = {'state': assessment['state'] if valid else 'UNKNOWN',
                'valid': valid, 'reasons': reasons or assessment['reasons'], 'assessment': assessment,
                'frame_seq': (result or {}).get('frame_seq', -1), 'capture_ns': (result or {}).get('capture_ns'),
                'health': health, 'age': age}
        return views

    def refresh_risk(self):
        started = time.monotonic_ns()
        with self.lock:
            self.risk_engine.tracker.prune(started)
            views = self._risk_views(started)
            for cid, result in self.results.items():
                labels = self._camera_labels(cid, started, views)
                if self._label_result(result, labels) and cid in self.frame_observations:
                    self.frame_observations[cid] = build_frame_observation(result['ground'], result['risk_assessment'])
            decision, events = self.risk_engine.update(views, started)
            ended = time.monotonic_ns()
            self.risk_engine.last_update_ns = ended
            decision.update(decision_ns=ended, site_ms=(ended-started)/1e6)
            for event in events:
                self.event(event['kind'], **{k:v for k,v in event.items() if k != 'kind'})
            return decision

    def scheduling_observations(self, now):
        with self.lock:
            return {cid: {'state': v['state'], 'valid': v['valid']} for cid,v in self._risk_views(now).items()}

    def observation_health(self):
        """Health worker needs no full result copies, JSON or risk evidence."""
        with self.lock:
            return {cid: {'health': v['health']['health'], 'valid': v['valid'], 'error': v['health']['error']}
                    for cid, v in self._risk_views(time.monotonic_ns()).items()}

    def reset_hazard(self, episode_id, operator_confirmed):
        with self.changed:
            self.event('admin_reset_requested', episode_id=episode_id)
            now = time.monotonic_ns()
            views = self._risk_views(now)
            allowed, reason = self.risk_engine.release_check(views, now)
            if operator_confirmed is not True or episode_id != self.risk_engine.episode_id or not allowed:
                reason = 'ADMIN_CONFIRMATION_REQUIRED' if operator_confirmed is not True else (
                    'EPISODE_CHANGED' if episode_id != self.risk_engine.episode_id else reason)
                self.event('admin_reset_validation', episode_id=episode_id, accepted=False, reason=reason)
                raise ValueError('RESET 안전 조건 미충족: ' + reason)
            if self.reset_pending_episode is not None:
                self.event('admin_reset_validation', episode_id=episode_id, accepted=False, reason='RESET_ALREADY_PENDING')
                raise ValueError('RESET 전송 결과를 기다리는 중입니다.')
            self.event('admin_reset_validation', episode_id=episode_id, accepted=True,
                       cameras=list(views))
            ble_connected = bool(self.excavator_ble and self.excavator_ble.snapshot()['connected'])
            if not ble_connected:
                _, events = self.risk_engine.reset(views, now, episode_id, True)
                if self.excavator_ble:
                    self.excavator_ble.clear(episode_id)
                self.event('admin_reset_transmission', episode_id=episode_id, status='SKIPPED',
                           reason='BLE_DISCONNECTED', device_ack='UNVERIFIED', control_applied='UNVERIFIED')
                for event in events:
                    self.event(event['kind'], **{k:v for k,v in event.items() if k != 'kind'})
                self.reset_result_status = 'VISION_RELEASED_NO_BLE'
                self.event('admin_reset_release_result', episode_id=episode_id,
                           status=self.reset_result_status, reason='BLE_DISCONNECTED',
                           device_ack='UNVERIFIED', control_applied='UNVERIFIED')
                self.changed.notify_all()
                return self.snapshot()
            self.reset_pending_episode = episode_id
            self.reset_result_status = 'WRITE_PENDING'
            self.excavator_ble.submit('RESET', episode_id)
            self.event('admin_reset_transmission', episode_id=episode_id, status='QUEUED',
                       device_ack='UNVERIFIED', control_applied='UNVERIFIED')
            self.changed.notify_all()
            return self.snapshot()

    def reset_send_allowed(self, episode_id):
        with self.changed:
            now = time.monotonic_ns()
            allowed, _ = self.risk_engine.release_check(self._risk_views(now), now)
            return (episode_id == self.reset_pending_episode == self.risk_engine.episode_id
                    and allowed and self.excavator_ble.snapshot()['connected'])

    def reset_write_result(self, episode_id, written, reason):
        with self.changed:
            if episode_id != self.reset_pending_episode:
                return
            self.reset_pending_episode = None
            self.event('admin_reset_transmission', episode_id=episode_id,
                       status='WRITE_COMPLETED' if written else 'ABORTED', reason=reason,
                       device_ack='UNVERIFIED', control_applied='UNVERIFIED')
            self.event('admin_reset_ack', episode_id=episode_id, status='UNVERIFIED',
                       reason='FIRMWARE_ACK_PROTOCOL_UNAVAILABLE' if written else 'BLE_RESET_NOT_SENT')
            now = time.monotonic_ns()
            allowed, block = self.risk_engine.release_check(self._risk_views(now), now)
            release_vision = written or reason in ('BLE_DISCONNECTED', 'BLE_WRITE_FAILED')
            if release_vision and allowed and episode_id == self.risk_engine.episode_id:
                _, events = self.risk_engine.reset(self._risk_views(now), now, episode_id, True,
                                                   ble_write_completed=written)
                for event in events:
                    self.event(event['kind'], **{k:v for k,v in event.items() if k != 'kind'})
                self.reset_result_status = ('VISION_RELEASED_CONTROL_UNVERIFIED' if written
                                            else 'VISION_RELEASED_NO_BLE')
            else:
                self.reset_result_status = 'RESTRICTION_RETAINED'
                if self.risk_engine.latched:
                    self.excavator_ble.submit('DANGER', episode_id)
                reason = block if written else reason
            self.event('admin_reset_release_result', episode_id=episode_id,
                       status=self.reset_result_status, reason=reason,
                       device_ack='UNVERIFIED', control_applied='UNVERIFIED')
            self.changed.notify_all()

    def snapshot(self):
        now = time.monotonic_ns()
        with self.lock:
            views = self._risk_views(now)
            rows = []
            for spec in self.config['cameras']:
                cid = spec['id']
                view = views[cid]
                ticks = self.rates[cid]
                span = min(2., max((now-self.started_ns)/1e9, .001))
                rate = sum(0 <= now-t <= 2_000_000_000 for t in ticks)/span
                result = deepcopy(self.results.get(cid))
                if result is not None:
                    self._label_result(result, self._camera_labels(cid, now, views))
                ground = deepcopy((result or {}).get('ground'))
                if ground is not None:
                    ground['observation_valid'] = view['valid']
                rows.append({**spec, **view['health'], 'observation_valid': view['valid'],
                    'risk': view['state'], 'risk_reasons': view['reasons'], 'inference_fps': round(rate,2),
                    'result_age_ms': None if view['age'] is None else round(view['age']*1000,2),
                    'result': result,
                    'calibration': self.calibrations.status(cid), 'ground': ground})
            usable = sum(v['valid'] for v in views.values())
            times = [v['capture_ns'] for v in views.values() if v['valid']]
            ble = self.excavator_ble.snapshot() if self.excavator_ble else None
            audio = self.audio_state
            audio_status = (audio.model_status if audio and audio.running else None)
            return {'project': 'SAYFE', 'version': self.config['project_version'],
                'run_id': self.recorder.run_id, 'mode': self.recorder.mode,
                **self.risk_engine.project(views, now),
                'excavator_ble': ble,
                'admin_reset_status': self.reset_result_status,
                'control_connected': bool(ble and ble['online']),
                'control_status': ble['status'] if ble else 'UNVERIFIED',
                'excavator_box_offset_px': self.config['risk'].get('excavator_box_offset_px', 23.),
                'observation': 'OBSERVING' if usable == len(rows) else 'DEGRADED' if usable else 'UNAVAILABLE',
                'running': self.running, 'inference_alive': self.inference_alive, 'pipeline_error': self.pipeline_error,
                'total_inference_fps': round(sum(r['inference_fps'] for r in rows),2),
                'camera_skew_ms': (max(times)-min(times))/1e6 if len(times)==2 else None,
                'calibration': {cid:self.calibrations.status(cid) for cid in self.rates},
                'scheduler': self.scheduler.snapshot() if self.scheduler else None,
                'external': {'audio': ('연결' if audio_status == 'READY' else
                                       '오류' if audio_status == 'ERROR' else
                                       '준비 중' if audio_status else '미연결'),
                             'esp32': '미연결', 'auracast': '미연결',
                             'control': ('BLE 연결' if ble['connected'] else 'BLE 연결 대기') if ble else '미연결'},
                'recording': self.recorder.health(), 'cameras': rows, 'events': list(self.recent)}
