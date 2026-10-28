# ESP32-C3 Gas Sensor 모듈

## 역할

MQ Gas Sensor의 측정값을 읽고 BLE notification으로 Audio 시스템에 전달합니다. 위험 여부는 ESP32-C3가 아니라 NVIDIA Jetson Orin Nano 8GB의 Audio receiver가 설정 Threshold와 비교하여 판단합니다.

## 입력

- MQ Gas Sensor 측정값

## 처리 과정

```text
MQ Gas Sensor → ESP32-C3 측정 → BLE notification
→ Audio receiver → Threshold 판단 → GAS_DANGER
```

## 출력

- BLE를 통한 MQ 측정값
- Audio Fast Path에서 생성되는 KO/ZH/VI 가스 위험 경고

## 주요 파일

| 파일 | 역할 |
|---|---|
| `sketch_aug18a.ino` | MQ 측정, ESP32-C3 상태 동작, BLE service/characteristic 제공 |

## 실행 방법

Arduino 형식의 source를 ESP32-C3 환경에서 build·flash하고 Audio 실행 시 장치 주소와 Threshold를 환경에 맞게 설정합니다. 정확한 board/library version은 이 저장소에서 특정하지 않습니다.
