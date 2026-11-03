# ESP32-C3 Gas Node

최종 결선 Gas Node는 MQ Gas Sensor와 ESP32-C3로 구성됩니다. [메인 README](../README.md)에 따라 ESP32-C3가 가스 위험을 판단하고 현장 장치를 직접 제어합니다.

```text
MQ Gas Sensor → Gas ESP32-C3 → 위험 판단
                           ├─ Buzzer 작동
                           ├─ Fan 작동
                           ├─ Door 제어
                           └─ BLE → Audio Jetson → Fast Path 다국어 경고
```

현장 장치 대응은 Audio Jetson의 음성 처리 결과를 기다리지 않습니다. 위험 판단의 세부 임계값은 이 문서에서 새로 정의하지 않습니다.

`sketch_aug18a.ino`는 이 폴더에 포함된 ESP32-C3 소스입니다. 이전의 “ESP32-C3는 측정값만 보내고 Audio Jetson이 모든 위험을 판단한다”는 설명은 최종 시스템 구성에 해당하지 않습니다.
