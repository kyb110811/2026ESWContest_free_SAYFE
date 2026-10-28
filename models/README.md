# Model 구성

## 외부 model

다음 model과 실행 자산은 크기와 배포 조건을 고려하여 저장소에 포함하지 않습니다.

- Whisper model과 whisper.cpp 실행 파일
- NLLB-200 CTranslate2 변환 model
- Piper 중국어·베트남어 voice model 및 실행 파일
- 범용 YOLO pretrained weight

각 장비의 실행 환경에서 별도로 준비해야 하며, 외부 구성요소의 역할은 [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)를 참고하십시오.
