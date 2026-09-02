# Vision 모듈

## 역할

Camera 영상에서 사람과 굴착기를 탐지하고, 작업자-굴착기 근접 상태와 굴착기의 Pixel Motion을 함께 판단하여 위험 이벤트를 생성합니다.

## 입력

- Camera frame
- `vision/best.pt` YOLO model
- 감지 confidence, 근접영역, motion 관련 설정값

## 처리 과정

```text
Camera
→ YOLO 사람·굴착기 탐지
→ 작업자-굴착기 근접 판단
→ 굴착기 Pixel Motion 판단
→ Danger 판단 및 latch
→ WORKER_NEAR_MOVING_EXCAVATOR
```

## 출력

- Bluetooth RFCOMM → Audio의 `WORKER_IN_EQUIPMENT_ZONE` Fast Path 경고
- localhost HTTP `POST /event` → `pi_rfcomm_bridge_server.py` → Raspberry Pi GPIO 제어
- Flask UI의 실시간 영상 및 상태
- runtime event log

## 주요 파일

| 파일 | 역할 |
|---|---|
| `run.sh` | model을 선택하고 `web_main.py`를 시작하는 진입점 |
| `web_main.py` | Camera, detector, 판단 logic, UI, event sender 통합 |
| `detector.py` | Ultralytics YOLO 기반 사람·굴착기 탐지 |
| `proximity.py` | 작업자와 굴착기의 근접영역 판단 |
| `motion_detector.py` | 굴착기 영역의 Pixel Motion 판단 |
| `event_logic.py` | 위험 조건과 event latch 처리 |
| `event_sender.py` | Audio RFCOMM 및 Raspberry Pi bridge로 이벤트 전송 |
| `config.py` | Vision threshold와 event name 설정 |
| `runtime_state.py` | runtime 상태 관리 |
| `models.py` | detection data model 정의 |
| `logger.py` | runtime event 기록 |

## 실행 방법

GPU, Camera, Python package, Bluetooth, localhost bridge를 준비한 뒤 실행합니다.

```bash
cd vision
bash run.sh
```

`run.sh`는 제출본의 `best.pt`를 선택하고 Camera 0, 640×480 설정으로 `web_main.py`를 실행합니다.
