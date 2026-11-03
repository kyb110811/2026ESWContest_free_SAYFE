# 시스템 연동

최종 결선의 장치 간 경로는 [메인 README](../README.md)를 기준으로 합니다.

| 이벤트 | 전달 경로 | 대응 |
|---|---|---|
| Vision DANGER | Vision Jetson → 유선 LAN → Audio Jetson | Fast Path 다국어 경고 |
| Vision DANGER | Vision Jetson → BLE → Excavator ESP32-C3 | Relay로 모형 굴착기 조작 제한 |
| Gas DANGER | Gas ESP32-C3 → BLE → Audio Jetson | Fast Path 다국어 경고 |

Gas ESP32-C3는 위험 판단과 Buzzer / Fan / Door 제어를 직접 수행합니다. Vision 위험이 해제되어도 굴착기 안전 인터록은 관리자 확인 후 해제합니다.

이 폴더의 `pi_rfcomm_bridge_server.py`는 초기 개발 단계의 Jetson–Raspberry Pi RFCOMM 브리지 자료입니다. 최종 결선의 Jetson 간 위험 이벤트 경로로 사용하지 않습니다.
