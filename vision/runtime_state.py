import threading, time

class RuntimeState:
    def __init__(self, equipment_state="STOP"):
        self.lock = threading.Lock()
        self.equipment_state = equipment_state
        self.status = "SAFE"
        self.worker_in_zone = False
        self.fps = 0.0
        self.inference_ms = 0.0
        self.frame_ms = 0.0
        self.last_event = None
        self.last_event_time = None
        self.jpeg_frame = None
        self.person_enabled = True
        self.excavator_enabled = True
        self.camera_ok = False
        self.reset_allowed = False
        self.person_detected = False
        self.excavator_detected = False
        self.person_confidence = 0.0
        self.excavator_confidence = 0.0
        self.proximity = None

        self.motion_score = 0.0
        self.motion_pixel_ratio = 0.0
        self.motion_center_shift = 0.0
        self.motion_source = "VISION_PIXEL"

        self.audio_bt_status = "READY"
        self.control_bt_status = "READY"
        self.audio_bt_error = None
        self.control_bt_error = None
        self.audio_send_ms = None
        self.control_send_ms = None
        self.bt_total_ms = None
        self.event_logs = []

    def add_log(self, msg, level="INFO"):
        with self.lock:
            self.event_logs.append({
                "time": time.strftime("%H:%M:%S"),
                "level": level,
                "message": str(msg),
            })
            self.event_logs = self.event_logs[-12:]

    def snapshot(self):
        with self.lock:
            return {
                "equipment_state": self.equipment_state,
                "status": self.status,
                "worker_near_excavator": self.worker_in_zone,
                "fps": round(self.fps, 2),
                "inference_ms": round(self.inference_ms, 2),
                "frame_ms": round(self.frame_ms, 2),
                "last_event": self.last_event,
                "last_event_time": self.last_event_time,
                "person_enabled": self.person_enabled,
                "excavator_enabled": self.excavator_enabled,
                "camera_ok": self.camera_ok,
                "reset_allowed": self.reset_allowed,
                "person_detected": self.person_detected,
                "excavator_detected": self.excavator_detected,
                "person_confidence": round(self.person_confidence, 3),
                "excavator_confidence": round(self.excavator_confidence, 3),
                "proximity": None if self.proximity is None else round(self.proximity, 3),

                "motion_score": round(self.motion_score, 4),
                "motion_pixel_ratio": round(self.motion_pixel_ratio, 4),
                "motion_center_shift": round(self.motion_center_shift, 4),
                "motion_source": self.motion_source,

                "audio_bt_status": self.audio_bt_status,
                "control_bt_status": self.control_bt_status,
                "audio_bt_error": self.audio_bt_error,
                "control_bt_error": self.control_bt_error,
                "audio_send_ms": self.audio_send_ms,
                "control_send_ms": self.control_send_ms,
                "bt_total_ms": self.bt_total_ms,
                "event_logs": list(self.event_logs),
            }
