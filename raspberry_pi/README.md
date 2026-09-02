# Raspberry Pi 제어 모듈

## 역할

Vision 위험 이벤트를 Bluetooth RFCOMM으로 수신하고 newline-delimited JSON을 해석하여 GPIO로 모형 굴착기 또는 안전장치를 제어합니다.

## 입력

- Bluetooth RFCOMM channel 1의 JSON event
- Vision event: `WORKER_NEAR_MOVING_EXCAVATOR`

## 처리 과정

```text
Vision → localhost HTTP Bridge → /dev/rfcomm0
→ Raspberry Pi RFCOMM receiver
→ newline-delimited JSON decode
→ WORKER_NEAR_MOVING_EXCAVATOR
→ WORKER_IN_EQUIPMENT_ZONE mapping
→ GPIO 동작
```

## 출력

- BCM GPIO 2, 3, 4, 14 제어
- 모형 굴착기 또는 안전장치 동작

## 주요 파일

| 파일 | 역할 |
|---|---|
| `excavator_control.py` | GitHub 제출본의 RFCOMM receiver, JSON event mapping, GPIO control 진입점 |
| `requirements.txt` | Raspberry Pi Python dependency |

실제 장비의 실행 파일명은 `ddd.py`이며, GitHub 제출본에서는 역할을 나타내는 `excavator_control.py`라는 이름으로 제공합니다.

## 실행 방법

```bash
cd raspberry_pi
python3 excavator_control.py
```

Bluetooth와 GPIO 권한 및 `RPi.GPIO` 환경이 필요합니다.
