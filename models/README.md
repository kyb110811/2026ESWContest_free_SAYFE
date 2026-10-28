# Model 구성

## 외부 model

다음 model과 실행 자산은 크기와 배포 조건을 고려하여 저장소에 포함하지 않습니다.

- Whisper model과 whisper.cpp 실행 파일
- NLLB-200 CTranslate2 변환 model
- Piper 중국어·베트남어 voice model 및 실행 파일
- YOLO26m 건설현장 객체 검출 모델
  출처: Hugging Face yihong1120/Construction-Hazard-Detection
  용도: 작업자·중장비·안전장비 객체 검출
  최적화: Jetson Orin Nano에서 TensorRT FP16 엔진으로 변환하여 사용
  배포: 원본 가중치 및 변환된 엔진 파일은 저장소에 포함하지 않음
- EfficientAT dymn10_as (MobileNet 기반 음향 이벤트 분류 model) pretrained weight 및 추가 학습 checkpoint
출처: GitHub fschmid56/EfficientAT
용도: 건설현장 내 폭발음(Explosion) 및 사이렌(Siren) 등 위험 음향 실시간 감지
학습: 사전 학습된 백본과 Siren 분류 가중치는 고정하고, Explosion 클래스만 추가 학습
최적화: Jetson Orin Nano에서 1~1.5초 오디오 입력 기반 실시간 음향 분류
배포: 원본 pretrained weight 및 추가 학습 checkpoint는 저장소에 포함하지 않음

각 장비의 실행 환경에서 별도로 준비해야 하며, 외부 구성요소의 역할은 [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)를 참고하십시오.



