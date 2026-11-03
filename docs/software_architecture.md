# 소프트웨어 구조

최종 결선의 처리 경로는 [메인 README](../README.md)를 기준으로 합니다.

## Audio

```text
Safe Path: 관리자 한국어 PTT → STT → 현장용어 보정 → NLLB 번역 → TTS → 언어별 방송
Fast Path: Vision / Gas DANGER → 일반 방송 선점 → 사전 검수된 다국어 경고 음원
```

한국어는 BTD700, 중국어·베트남어는 nRF5340 Audio DK의 Auracast 경로로 출력합니다.

## Vision과 장비 제어

```text
Dual Camera → Construction-Hazard-Detection 계열 YOLO26m 객체 검출
→ Camera별 Bounding Box 기반 위험판정
→ Homography 기반 지면 좌표·동일 작업자 매칭 보조
→ 두 Camera 결과 통합 → 최종 SAFE / DANGER
```

최종 DANGER는 유선 LAN으로 Audio Jetson에 전달되고, BLE로 Excavator ESP32-C3에 전달됩니다. 장비 조작 제한은 안전 인터록과 관리자 확인 후 해제 절차를 따릅니다.

## Gas

Gas ESP32-C3가 MQ Gas Sensor 값을 바탕으로 위험을 판단하고 Buzzer / Fan / Door를 직접 제어합니다. 위험 이벤트는 BLE로 Audio Jetson에 전달되어 Fast Path 방송을 시작합니다.
