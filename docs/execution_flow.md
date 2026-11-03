# 최종 결선 실행 흐름

실행 환경과 명령의 기준은 [메인 README의 실행 방법](../README.md#24-실행-방법)입니다.

## Audio

`audio/run_ui_demo.sh`가 Audio UI를 시작합니다. 관리자의 한국어 PTT 입력은 STT → 현장용어 보정 → NLLB 번역 → TTS를 거쳐 언어별 방송으로 전달됩니다. Vision 또는 Gas 위험 이벤트가 들어오면 Fast Path가 일반 방송을 선점하고 사전 검수된 다국어 경고 음원을 송출합니다.

## Vision

메인 README는 Vision 실행 명령으로 `vision/run.sh`를 안내하지만, 이 파일은 현재 체크아웃에 포함되어 있지 않습니다. 최종 시스템 설명상 Vision은 Construction-Hazard-Detection 계열 YOLO26m으로 객체를 검출하고 Camera별 위험을 판단합니다. Homography는 두 Camera 간 동일 작업자 매칭을 보조하며, 두 결과를 통합해 최종 SAFE / DANGER를 결정합니다.

최종 DANGER는 유선 LAN으로 Audio Jetson에, BLE로 Excavator ESP32-C3에 전달합니다. ESP32-C3의 Relay가 모형 굴착기 조작을 제한하며, 위험 해제 후에도 관리자 확인 전까지 안전 인터록을 유지합니다.

## Gas

Gas ESP32-C3가 MQ Gas Sensor를 측정하고 위험을 판단합니다. 위험 시 Buzzer / Fan / Door를 직접 제어하며 BLE로 Audio Jetson에 위험 이벤트를 보냅니다.

이전 Raspberry Pi·RFCOMM·Pixel Motion 실행 안내는 최종 결선 실행 흐름에 해당하지 않습니다.
