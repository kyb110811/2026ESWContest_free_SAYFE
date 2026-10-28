# 장치 통합 모듈

## 역할

SAY:FE의 Vision, Audio, Gas Sensor, ESP32-C3, nRF5340 Audio DK 간 이벤트 및 오디오 연결 구조를 설명합니다.

Vision에서 감지한 위험 이벤트를 Audio 모듈로 전달하고, ESP32-C3에서 수집한 가스 센서 데이터를 BLE 통신으로 수신하여 위험 상황 감지 및 다국어 안전 방송에 활용합니다.

## 입력

- `vision/event_sender.py`에서 전송하는 Vision 위험 이벤트
- ESP32-C3 BLE Gas Sensor 측정값
- Audio 모듈에서 수신하는 위험 이벤트

## 처리 과정

```text
Vision / event_sender.py
→ Bluetooth RFCOMM
→ Audio / bluetooth_event_listener.py
→ 위험 이벤트 처리
→ 다국어 안전 방송

ESP32-C3 Gas Sensor
→ BLE
→ Audio / esp32_ble_receiver.py
→ 가스 측정값 수신
→ 위험 상태 판단
```

## 출력

- Vision 위험 감지 이벤트
- ESP32-C3 가스 센서 측정 데이터
- 위험 상황에 따른 Audio 이벤트 처리
- nRF5340 Audio DK를 통한 다국어 Auracast 안전 방송

## 주요 파일

| 파일 | 역할 |
|---|---|
| `../vision/event_sender.py` | Vision 위험 이벤트를 Audio 모듈로 전송 |
| `../audio/src/events/bluetooth_event_listener.py` | Vision → Audio RFCOMM 이벤트 수신 |
| `../audio/src/sensors/esp32_ble_receiver.py` | ESP32-C3 BLE Gas 측정값 수신 |

## 실행 방법

Vision, Audio 및 ESP32-C3의 통신 환경을 설정한 후 각 모듈을 실행합니다.

- Vision 모듈에서 위험 이벤트 생성 및 전송
- Audio 모듈에서 RFCOMM 위험 이벤트 수신
- ESP32-C3 BLE 연결을 통한 가스 센서 측정값 수신
- 위험 이벤트에 따른 다국어 안전 방송 처리
