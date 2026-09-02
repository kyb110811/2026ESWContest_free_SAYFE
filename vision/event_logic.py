import time
from dataclasses import dataclass
from typing import Optional

from config import ENTER_CONFIRM_FRAMES, EVENT_NAME, EQUIPMENT_ID


@dataclass
class HazardDecision:
    active: bool
    event: Optional[dict]
    just_triggered: bool
    reset_allowed: bool


class HazardStateMachine:
    """CAS용 latch 상태머신.

    Trigger:
      equipment_state == RUNNING
      AND worker_near_equipment == True
      AND condition이 ENTER_CONFIRM_FRAMES 연속 유지

    Trigger 이후에는 장비가 STOP으로 바뀌어도 active 유지.
    사람이 근접영역에서 완전히 벗어난 뒤 manual reset으로만 해제.
    """

    def __init__(self):
        self.active = False
        self.enter_count = 0
        self.worker_near_equipment = False

    def update(
        self,
        worker_near_equipment: bool,
        equipment_state: str,
        confidence: float = 1.0,
        person_confidence: float = 0.0,
        excavator_confidence: float = 0.0,
        proximity: float | None = None,
    ):
        self.worker_near_equipment = bool(worker_near_equipment)
        trigger_condition = (
            self.worker_near_equipment
            and equipment_state.upper() == "RUNNING"
        )

        just_triggered = False
        event = None

        if not self.active:
            if trigger_condition:
                self.enter_count += 1
                if self.enter_count >= ENTER_CONFIRM_FRAMES:
                    self.active = True
                    self.enter_count = 0
                    just_triggered = True
            else:
                self.enter_count = 0

        if just_triggered:
            event = {
                "source": "VISION",
                "event": EVENT_NAME,
                "equipment": EQUIPMENT_ID,
                "equipment_state": "RUNNING",
                "confidence": round(float(confidence), 3),
                "person_confidence": round(float(person_confidence), 3),
                "excavator_confidence": round(float(excavator_confidence), 3),
                "proximity": None if proximity is None else round(float(proximity), 3),
                "timestamp": int(time.time() * 1000),
            }

        return HazardDecision(
            active=self.active,
            event=event,
            just_triggered=just_triggered,
            reset_allowed=(self.active and not self.worker_near_equipment),
        )

    def reset(self) -> bool:
        """사람이 근접영역 밖에 있을 때만 latch 해제."""
        if not self.active:
            return True

        if self.worker_near_equipment:
            return False

        self.active = False
        self.enter_count = 0
        return True
