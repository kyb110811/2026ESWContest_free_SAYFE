# 하드웨어 구성

[메인 README](../README.md)의 최종 결선 구성을 요약합니다.

| 장치 | 역할 | 주요 연결 |
|---|---|---|
| Audio Jetson Orin Nano | 관리자 음성 처리, 다국어 방송, Vision·Gas Fast Path | Vision Jetson과 유선 LAN, Gas ESP32-C3와 BLE |
| Vision Jetson Orin Nano | Dual Camera 영상의 객체 검출과 최종 SAFE / DANGER 판단 | Audio Jetson과 유선 LAN, Excavator ESP32-C3와 BLE |
| Camera × 2 | 서로 다른 시점의 영상 입력 | Vision Jetson |
| Gas ESP32-C3 + MQ Gas Sensor | 가스 위험 판단과 Buzzer / Fan / Door 직접 제어 | Audio Jetson에 BLE 위험 이벤트 |
| Excavator ESP32-C3 + Relay | DANGER 시 모형 굴착기 조작 제한 | Vision Jetson의 BLE 제어 신호 |
| Microphone | 관리자 한국어 음성 입력 | Audio Jetson |
| Sennheiser BTD700 | 한국어 Audio 출력 | Audio Jetson |
| nRF5340 Audio DK | 중국어·베트남어 Auracast 방송 | Audio Jetson의 PCM 입력 |
| Auracast Receiver | 중국어·베트남어 방송 수신 | Auracast |

위험 해제 후 굴착기 조작 제한은 관리자 확인을 거쳐 해제합니다. Raspberry Pi GPIO와 Jetson 간 RFCOMM은 이전 개발 단계의 구조입니다.
