# 저장소 구성

최종 결선 시스템 설명의 기준은 [메인 README](../README.md)입니다. 아래는 저장소에 실제로 있는 최상위 폴더와 역할입니다.

| 폴더 | 역할 |
|---|---|
| `audio/` | 관리자 한국어 음성의 Safe Path, Vision·Gas 위험 경고 Fast Path, 언어별 방송 |
| `vision/` | Dual Camera·YOLO26m 객체 검출, Camera별 위험판정, Homography 매칭 보조, 최종 SAFE / DANGER |
| `esp32_gas/` | MQ Gas Sensor 측정·위험 판단, Buzzer / Fan / Door 직접 제어, BLE 위험 이벤트 |
| `esp32_excavator/` | BLE 위험 제어 신호 수신, Relay를 통한 모형 굴착기 조작 제한 |
| `integration/` | 장치 간 연동 관련 자료. 포함된 RFCOMM 브리지 코드는 이전 개발 단계 자료 |
| `nrf5340/` | 중국어·베트남어 Auracast 방송 및 Nordic 관련 소스 |
| `models/` | 최종 모델과 이전·실험 모델의 구분 및 외부 모델 안내 |
| `docs/` | 최종 시스템 구조와 문서 안내 |
| `SAYFE_yeongjun_FP16/` | 별도 Vision·AudioDetection 개발 자료와 측정 기록. 최종 시스템 설명은 메인 README 참조 |

최상위 문서로 `README.md`와 `THIRD_PARTY_NOTICES.md`가 있습니다. `raspberry_pi/` 폴더는 현재 저장소에 없습니다. RFCOMM 관련 자료는 최종 결선의 Jetson 간 통신 경로가 아닙니다.
