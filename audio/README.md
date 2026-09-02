# Audio 모듈

## 역할

NVIDIA Jetson Orin Nano 8GB에서 관리자 한국어 음성을 처리하고 한국어·중국어·베트남어 안전방송을 생성·routing합니다. Vision과 Gas 위험 이벤트가 들어오면 Safe Path를 선점하고 Fast Path 긴급 경고를 우선 방송합니다.

## 입력

- Microphone의 관리자 한국어 음성
- Vision이 Bluetooth RFCOMM으로 전송한 `WORKER_NEAR_MOVING_EXCAVATOR`
- ESP32-C3가 BLE로 전송한 MQ Gas Sensor 측정값
- Audio Flask UI의 방송 제어 요청

## 처리 과정

### Safe Path

```text
Microphone → Silero VAD → Whisper STT
→ Construction Normalizer / 은어 교정
→ Verified Translation Mapping 또는 NLLB-200 / CTranslate2
→ Safety Guard / Fallback
→ Piper TTS
→ BTD700 또는 nRF5340 Audio DK
```

### Fast Path

```text
Vision/Gas Event → fast_path.py → Safe Path Audio 선점
→ assets/fast_path/{ko,zh,vi}의 사전 생성 WAV
→ KO/ZH/VI 긴급 경고 방송
```

Vision 이벤트는 `WORKER_IN_EQUIPMENT_ZONE` 경고로 연결되고, BLE 측정값이 설정 Threshold를 초과하면 `GAS_DANGER`가 발생합니다.

## 출력

- 한국어 Audio → Sennheiser BTD700
- 중국어·베트남어 PCM → nRF5340 Audio DK → Auracast Broadcast
- 실제 시연 → Galaxy 스마트폰의 LG ThinQ 앱에서 방송 검색·선택 → LG xboom Rock에서 Auracast 수신·재생

## 주요 파일

| 파일 | 역할 |
|---|---|
| `run_ui_demo.sh` | nRF5340 설정과 Audio Flask UI를 시작하는 진입점 |
| `src/ui/safety_web.py` | Audio web UI 및 전체 실행 제어 |
| `scripts/ui_mic_controller.py` | Microphone/VAD, 한국어 출력, GPU worker orchestration |
| `scripts/ui_gpu_worker.py` | STT, 번역, TTS, Vision/Gas Fast Path 통합 |
| `src/stt/vad_engine.py` | Silero VAD 기반 발화 구간 검출 |
| `src/stt/whisper_engine.py` | whisper.cpp server를 이용한 한국어 STT |
| `src/safety/normalizer.py` | 건설현장 용어·은어 정규화 |
| `src/translation/verified_site_translations.py` | 현장 검증 번역 우선 Mapping |
| `src/translation/nllb_engine.py` | NLLB-200/CTranslate2 번역 orchestration |
| `src/translation/safety_guard.py` | 번역 안전성 검사 |
| `src/translation/safety_fallback.py` | 검사 실패 시 안전문장 fallback |
| `src/safety/fast_path.py` | Vision/Gas 긴급 이벤트의 KO/ZH/VI 경고 실행 |
| `src/audio/auracast_output.py` | ZH/VI PCM queue, streaming, Fast Path preemption |
| `scripts/setup_auracast_zh_vi.py` | serial 명령으로 nRF5340 ZH/VI 방송 프로그램 설정 |

## 실행 방법

외부 Whisper/NLLB/Piper model과 실행 파일, Python 환경, ALSA/Bluetooth/serial 권한을 장비에 준비한 뒤 실행합니다.

```bash
cd audio
SAYFE_GAS_ENABLED=1 \
SAYFE_GAS_MAC=<GAS_SENSOR_BT_MAC> \
SAYFE_GAS_THRESHOLD=1000 \
./run_ui_demo.sh
```

`run_ui_demo.sh`는 활성 환경의 `python3` 또는 `PYTHON`으로 지정한 interpreter를 사용합니다.
