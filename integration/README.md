# 장치 통합 모듈

## 역할

SAY:FE의 Vision, Audio, Gas Sensor, Raspberry Pi, nRF5340 Audio DK 사이 event/audio 연결 구조를 설명합니다. 이 폴더의 `pi_rfcomm_bridge_server.py`는 Vision Host의 localhost HTTP 이벤트를 Raspberry Pi용 Bluetooth RFCOMM stream으로 변환합니다.

## 입력

- `vision/event_sender.py`가 보내는 `POST /event` JSON
- endpoint: `127.0.0.1:8765`

## 처리 과정

```text
Vision / event_sender.py
→ HTTP POST 127.0.0.1:8765/event
→ pi_rfcomm_bridge_server.py
→ RFCOMM 연결 확인
→ newline-delimited JSON
→ /dev/rfcomm0
→ Raspberry Pi
```

Bridge는 loopback에만 bind하므로 Vision sender와 동일한 localhost network context에서 실행해야 합니다.

## 출력

- `/dev/rfcomm0`을 통한 Raspberry Pi 위험 이벤트
- Raspberry Pi의 JSON event mapping 및 GPIO control

## 주요 파일

| 파일 | 역할 |
|---|---|
| `pi_rfcomm_bridge_server.py` | localhost HTTP → Bluetooth RFCOMM bridge |
| `../vision/event_sender.py` | Audio RFCOMM과 Pi HTTP bridge로 Vision event 전송 |
| `../audio/src/events/bluetooth_event_listener.py` | Vision → Audio RFCOMM event 수신 |
| `../audio/src/sensors/esp32_ble_receiver.py` | ESP32-C3 BLE Gas 측정값 수신 |
| `../raspberry_pi/excavator_control.py` | Pi RFCOMM JSON 수신 및 GPIO 제어 |

## 실행 방법

Host의 `rfcomm` 명령과 `/dev/rfcomm0` 접근 권한을 준비한 뒤 저장소 root에서 실행합니다.

```bash
python3 integration/pi_rfcomm_bridge_server.py
```
