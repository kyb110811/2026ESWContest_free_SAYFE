# Model 구성

최종 결선 시스템의 모델 역할은 [메인 README](../README.md)를 기준으로 합니다. 외부 모델의 배포 조건과 고지는 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)를 참고하십시오.

## 최종 결선에서 사용하는 모델

| 영역 | 모델 | 역할 |
|---|---|---|
| STT | Whisper / whisper.cpp | 관리자 한국어 음성 인식 |
| 번역 | NLLB-200 / CTranslate2 | 중국어·베트남어 번역 |
| TTS | Piper | 중국어·베트남어 음성 생성 |
| VAD | Silero VAD | 관리자 발화 구간 검출 |
| Vision | Construction-Hazard-Detection 계열 YOLO26m | Dual Camera의 작업자·중장비 객체 검출 |

Vision은 YOLO26m 검출 결과를 바탕으로 Camera별 Bounding Box 위험판정을 수행합니다. Homography 기반 지면 좌표는 두 Camera 간 동일 작업자 매칭을 보조하며, 두 결과를 종합해 최종 SAFE / DANGER를 결정합니다.

## Previous / Experimental

- 메인 README의 초기 자체 학습 `person` / `excavator` 2-class YOLO11n 결과는 이전 개발 자료입니다. 최종 Vision 모델의 성능 자료가 아닙니다. 메인 README가 링크한 `vision/best.pt`와 `vision/training_results/`는 현재 체크아웃에 포함되어 있지 않습니다.
- `SAYFE_yeongjun_FP16/AudioDetection/`의 위험 음향 분류는 별도 실험·개발 자료입니다. 메인 README의 최종 결선 핵심 기능에 포함되지 않습니다.
- 이전 문서에 기재된 EfficientAT `dymn10_as` 위험 음향 분류 모델 역시 **Experimental / Not used in final demonstration**으로 구분합니다.

외부 Whisper, NLLB, Piper, 최종 YOLO26m 모델 자산은 장비 환경에서 별도로 준비합니다. 초기 모델과 실험 자료를 최종 적용 모델로 해석하지 마십시오.
