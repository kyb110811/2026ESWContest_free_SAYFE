# Vision

최종 결선 Vision 설명은 [메인 README](../README.md)를 기준으로 합니다.

## Overview

Vision Jetson은 작업자와 중장비의 위험상태를 판단하고 Audio 및 장비제어 시스템과 연동합니다.

## Final Vision Pipeline

```text
Dual Camera → Construction-Hazard-Detection 계열 YOLO26m 객체 검출
→ Camera별 위험판정 → Homography 기반 매칭 보조
→ 두 Camera 결과 통합 → 최종 SAFE / DANGER
```

## Dual Camera

서로 다른 시점의 Camera 두 대를 사용해 각 Camera의 위험상태를 판단합니다.

## YOLO26m

최종 적용 모델은 Construction-Hazard-Detection 계열 YOLO26m입니다. 메인 README의 자체 학습 YOLO11n 결과는 **Previous development model** 자료이며 최종 모델 성능을 나타내지 않습니다.

## Risk Decision

각 Camera에서 검출된 작업자와 중장비의 Bounding Box 관계를 바탕으로 SAFE / DANGER를 판단하고, 두 Camera의 결과를 종합합니다.

## Homography

Homography 기반 ground coordinate는 두 Camera 간 동일 작업자 매칭을 보조합니다. 위험 여부를 직접 결정하는 기준은 아닙니다.

## Safety Interlock

최종 DANGER 시 모형 굴착기의 조작을 제한합니다. 위험상황이 해제되어도 안전 인터록은 유지되며, 관리자 확인 후 정상 조작으로 복귀합니다.

## System Integration

Vision DANGER 이벤트는 유선 LAN으로 Audio Jetson에 전달되어 Fast Path 다국어 경고를 시작하고, BLE로 Excavator ESP32-C3에 전달되어 Relay 기반 조작 제한을 시작합니다.
