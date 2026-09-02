# Vision Safety Node - Jetson / Dynamic proximity / Bluetooth

EQUIPMENT_ID = "EXCAVATOR_01"

# 음성 Jetson과 합의할 최종 이벤트 이름
EVENT_NAME = "WORKER_NEAR_MOVING_EXCAVATOR"

# 굴착기 bbox를 기준으로 자동 생성되는 근접 안전영역.
# 값 0.35 = 굴착기 bbox 폭의 35%만큼 상하좌우 확장.
# 목업/카메라 배치에 따라 0.25~0.50 범위에서 조정 권장.
PROXIMITY_MARGIN_RATIO = 0.35

# 연속 N 프레임 동안 RUNNING + 근접이 유지되어야 이벤트 확정
ENTER_CONFIRM_FRAMES = 2

# 이벤트는 자동 해제하지 않고 latch.
# 사람이 근접영역을 벗어난 뒤 Manual Reset 해야 다시 RUNNING 가능하도록
# 제어 파트에서 같은 정책을 적용하는 것을 권장.
DEFAULT_EQUIPMENT_STATE = "STOP"  # RUNNING / STOP

LOG_PATH = "vision_events.csv"


# v.6 - visual excavator motion detection
# Fixed-camera mock-up defaults. Tune these if needed.
MOTION_START_THRESHOLD = 0.055
MOTION_STOP_THRESHOLD = 0.022
MOTION_PIXEL_THRESHOLD = 18
MOTION_START_FRAMES = 1
MOTION_STOP_FRAMES = 8
