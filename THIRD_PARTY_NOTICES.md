# 외부 오픈소스 및 모델

이 문서는 SAY:FE가 사용하는 외부 software/model과 팀 개발 application logic의 경계를 설명합니다. 공식 license 원문을 대체하지 않으며, 정확히 확인되지 않은 version 또는 배포 조건은 확정하여 기재하지 않습니다.

## 구성요소별 역할

### Whisper / whisper.cpp

- 역할: `whisper-server`를 이용한 관리자 한국어 음성 STT
- 구분: 외부 software 및 model
- Upstream: <https://github.com/ggml-org/whisper.cpp>, <https://github.com/openai/whisper>
- License: whisper.cpp는 MIT. 배포 model의 정확한 출처와 조건은 별도 확인 대상
- 저장소 포함 여부: 실행 파일과 model은 포함하지 않음
- 팀 개발 범위: VAD 연결, server lifecycle, 건설현장 prompt, hallucination filtering, safety pipeline integration

### NLLB-200

- 역할: 한국어 안전문장의 중국어·베트남어 번역
- 구분: Meta AI의 외부 model
- Upstream: `facebook/nllb-200-distilled-600M`
- License: upstream model card에 CC-BY-NC-4.0으로 표시됨. 적용 범위는 원문 기준으로 검토 필요
- 저장소 포함 여부: CTranslate2 변환 model은 포함하지 않음
- 팀 개발 범위: 현장용어 preprocessing, Verified Mapping 우선 처리, ZH/VI translation routing, Safety Guard와 Fallback

### CTranslate2

- 역할: NLLB-200 inference 최적화
- 구분: OpenNMT 외부 software
- Upstream: <https://github.com/OpenNMT/CTranslate2>
- License: MIT
- 확인된 Audio 환경 version: 4.4.0
- 팀 개발 범위: model validation, device/compute 설정, translation pipeline integration

### Hugging Face Transformers

- 역할: NLLB tokenizer loading
- 구분: Hugging Face 외부 software
- Upstream: <https://github.com/huggingface/transformers>
- License: Apache-2.0
- 확인된 환경 version: 4.46.3

### Piper

- 역할: 중국어·베트남어 text-to-speech
- 구분: 외부 software 및 voice model
- License: 실제 배포 binary의 fork와 각 ONNX voice model에 따라 달라질 수 있어 일괄 확정하지 않음
- 저장소 포함 여부: binary, shared library, voice model, config는 포함하지 않음
- 팀 개발 범위: ZH/VI 병렬 합성, PCM streaming, WAV 연계, Auracast queue와 Fast Path preemption

### Silero VAD / PyTorch

- 역할: Microphone 입력의 발화 구간 검출
- 구분: 외부 software/model
- Upstream: <https://github.com/snakers4/silero-vad>, <https://github.com/pytorch/pytorch>
- License: Silero VAD는 MIT, PyTorch는 BSD-style license
- 확인된 Audio 환경 version: silero-vad 6.2.1, PyTorch 2.4.1
- 팀 개발 범위: Microphone state machine, threshold/energy handling, STT handoff

### Ultralytics YOLO

- 역할: Vision의 사람·굴착기 object detection framework
- 구분: 외부 software
- Upstream: <https://github.com/ultralytics/ultralytics>
- License: 사용 형태에 따라 AGPL-3.0 또는 Ultralytics Enterprise 조건이 적용될 수 있으므로 실제 적용 조건 확인 필요
- 팀 개발 범위: detector integration, class filtering, proximity logic, Pixel Motion, Danger Event
- 팀 artifact: `vision/best.pt` 정보는 [`models/README.md`](models/README.md)에 별도 기록

### OpenCV / NumPy

- 역할: Vision frame 처리, Pixel Motion 계산, Audio PCM/data 처리
- 구분: 외부 software
- Upstream: <https://opencv.org>, <https://numpy.org>
- License: OpenCV 현재 release는 Apache-2.0, NumPy는 BSD-3-Clause
- 확인된 Audio NumPy version: 1.24.4

### Flask

- 역할: Audio와 Vision web UI
- 구분: Pallets 외부 software
- Upstream: <https://github.com/pallets/flask>
- License: BSD-3-Clause
- 확인된 Audio 환경 version: 3.0.3

### Bleak

- 역할: NVIDIA Jetson Orin Nano 8GB에서 ESP32-C3 BLE Gas Sensor 수신
- 구분: 외부 software
- Upstream: <https://github.com/hbldh/bleak>
- License: MIT
- 확인된 Audio 환경 version: 0.22.3

### pySerial

- 역할: `/dev/ttyACM0`을 통한 nRF5340 Audio DK ZH/VI 방송 설정
- 구분: 외부 software
- Upstream: <https://github.com/pyserial/pyserial>
- License: BSD-3-Clause
- 확인된 Audio 환경 version: 3.5

### Nordic nRF Connect SDK / Zephyr

- 역할: nRF5340 Audio DK의 LE Audio/Auracast platform firmware 기반
- 구분: Nordic Semiconductor 외부 SDK와 Zephyr RTOS
- License: component별 조건이 다르며 Zephyr는 주로 Apache-2.0. 실제 firmware 구성에 포함된 Nordic component notice는 해당 구성 기준으로 확인 필요
- 저장소 포함 여부: Nordic nRF Connect SDK와 Zephyr source 전체는 포함하지 않음
- 팀 개발 범위: `audio/scripts/setup_auracast_zh_vi.py`의 ZH/VI serial 방송 설정과 `auracast_output.py`의 Audio streaming integration
- 별도 팀 수정 Firmware Source: 이 저장소와 읽기 전용 검색 범위에서 식별되지 않음

### RPi.GPIO

- 역할: Raspberry Pi의 모형 굴착기·안전장치 GPIO 제어
- 구분: 외부 Python package
- License/version: 실제 Raspberry Pi 설치 package 기준 확인 필요

## 팀 개발 영역 요약

SAY:FE 팀은 위 외부 기술을 연결하는 application/integration layer를 개발했습니다. 주요 범위는 Audio pipeline orchestration, 건설현장 문장 정규화와 검증 번역, Safety Guard/Fallback, Fast Path, Vision proximity/Pixel Motion/Danger Event, BLE/RFCOMM/HTTP event integration, Raspberry Pi JSON/GPIO control, nRF5340 serial setup과 다국어 Audio routing입니다.
