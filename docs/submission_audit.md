# 제출본 문서 안내

최종 결선 시스템 설명의 기준은 [메인 README](../README.md)입니다. 이 문서는 저장소에서 확인되는 자료의 위치를 간단히 안내합니다.

| 영역 | 저장소 위치 | 최종 결선에서 설명하는 역할 |
|---|---|---|
| Audio | `audio/` | Safe Path 번역 방송, 위험 이벤트 우선 Fast Path |
| Vision | `vision/README.md` | Dual Camera·YOLO26m 기반 최종 SAFE / DANGER 설명 |
| Gas | `esp32_gas/` | 가스 위험 판단, Buzzer / Fan / Door, BLE 알림 |
| 굴착기 제어 | `esp32_excavator/` | BLE·Relay 기반 조작 제한과 안전 인터록 |
| Auracast | `nrf5340/` | 중국어·베트남어 방송 |
| 이전 개발 자료 | `integration/`, `SAYFE_yeongjun_FP16/` | 최종 구성과 구분해 읽을 자료 |

이전 제출 상태의 파일 개수·해시·테스트 결과는 현재 최종 시스템의 검증 결과로 제시하지 않습니다. 메인 README가 언급하는 `vision/run.sh`, `vision/best.pt`, `vision/training_results/`, `THIRD_PARTY_LICENSES.txt`는 현재 체크아웃에 포함되어 있지 않습니다. 실행 환경과 외부 모델은 메인 README 및 [모델 안내](../models/README.md)를 따릅니다.
