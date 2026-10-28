# Model 구성

## 외부 Model

다음 Model과 실행 자산은 파일 크기 및 배포 조건을 고려하여 저장소에 포함하지 않습니다.

### 1. Whisper 음성 인식 Model

- **출처:** [GitHub - openai/whisper](https://github.com/openai/whisper)
- **실행 도구:** [GitHub - ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp)
- **용도:** 건설현장 내 한국어 음성 방송을 텍스트로 변환(STT)
- **최적화:** whisper.cpp 기반 음성 인식으로 로컬 환경에서 실행
- **배포:** Whisper Pretrained Weight 및 whisper.cpp 실행 파일은 저장소에 포함하지 않음

### 2. NLLB-200 다국어 번역 Model

- **출처:** [Hugging Face - facebook/nllb-200-distilled-600M](https://huggingface.co/facebook/nllb-200-distilled-600M)
- **실행 도구:** [GitHub - OpenNMT/CTranslate2](https://github.com/OpenNMT/CTranslate2)
- **용도:** 한국어 안전 방송을 중국어·베트남어로 자동 번역
- **최적화:** CTranslate2 형식으로 변환하여 다국어 번역 추론 실행
- **배포:** 원본 Pretrained Weight 및 CTranslate2 변환 모델 파일은 저장소에 포함하지 않음

### 3. Piper 다국어 음성 합성 Model

- **출처:** [GitHub - rhasspy/piper](https://github.com/rhasspy/piper)
- **Voice Model:** [Piper Voices](https://huggingface.co/rhasspy/piper-voices)
- **용도:** 번역된 중국어·베트남어 안전 방송 문장을 음성으로 변환(TTS)
- **최적화:** ONNX 기반 로컬 음성 합성으로 외부 클라우드 의존 없이 실행
- **배포:** 중국어·베트남어 Voice Model 및 Piper 실행 파일은 저장소에 포함하지 않음

### 4. YOLO26m 건설현장 객체 검출 Model

- **출처:** [Hugging Face - yihong1120/Construction-Hazard-Detection](https://huggingface.co/yihong1120/Construction-Hazard-Detection)
- **용도:** 작업자·중장비·안전장비 객체 검출
- **최적화:** Jetson Orin Nano에서 TensorRT FP16 엔진으로 변환하여 사용
- **배포:** 원본 가중치 및 변환된 엔진 파일은 저장소에 포함하지 않음

### 5. EfficientAT dymn10_as 위험 음향 분류 Model

- **출처:** [GitHub - fschmid56/EfficientAT](https://github.com/fschmid56/EfficientAT)
- **모델:** EfficientAT `dymn10_as` (Dynamic MobileNet 기반 음향 이벤트 분류 모델)
- **용도:** 건설현장 내 폭발음(Explosion) 및 사이렌(Siren) 등 위험 음향 실시간 감지
- **학습:** 사전 학습된 백본과 Siren 분류 가중치는 고정하고, Explosion 클래스만 추가 학습
- **최적화:** Jetson Orin Nano에서 1~1.5초 오디오 입력 기반 실시간 음향 분류
- **배포:** 원본 Pretrained Weight 및 추가 학습 Checkpoint는 저장소에 포함하지 않음

---

각 Model과 실행 자산은 장비별 실행 환경에서 별도로 준비해야 합니다.

외부 구성요소의 역할 및 관련 사항은 [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)를 참고하십시오.
