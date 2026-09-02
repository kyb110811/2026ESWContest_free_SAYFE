# 저장소 구성

이 저장소는 SAYFE의 팀 application/integration source와 실행에 필요한 소규모 asset을 장치·기능별로 구분합니다.

```text
2026ESWContest_free_SAYFE/
├── README.md                 프로젝트 소개와 전체 시스템 구조
├── THIRD_PARTY_NOTICES.md   외부 software/model 역할과 license 정보
├── audio/                    Safe Path, Fast Path, 다국어 Audio routing
├── vision/                   YOLO, proximity, Pixel Motion, Danger Event
├── esp32_gas/                MQ Gas Sensor 측정 및 BLE 송신
├── raspberry_pi/             RFCOMM JSON event와 GPIO control
├── integration/              Vision Host HTTP/RFCOMM Bridge
├── nrf5340/                  nRF5340 Audio DK/Auracast 구성 설명
├── models/                   Vision model 정보와 외부 model 정책
└── docs/                     시스템 기술 문서
```

## 폴더별 역할

| 폴더 | 역할 | 진입점 또는 핵심 파일 |
|---|---|---|
| `audio/` | 관리자 음성 VAD/STT, 정규화, 번역, TTS, Vision/Gas Fast Path, KO/ZH/VI routing | `run_ui_demo.sh`, `src/ui/safety_web.py` |
| `vision/` | 사람·굴착기 탐지, 근접 판단, Pixel Motion, 위험 이벤트 생성·전송 | `run.sh`, `web_main.py` |
| `esp32_gas/` | MQ 측정값 BLE 송신 | `sketch_aug18a.ino` |
| `raspberry_pi/` | RFCOMM JSON event 수신과 GPIO 제어 | `excavator_control.py` |
| `integration/` | Vision localhost HTTP event를 Pi RFCOMM으로 전달 | `pi_rfcomm_bridge_server.py` |
| `nrf5340/` | nRF5340/Auracast 경계와 팀 serial setup 범위 설명 | `README.md` |
| `models/` | 포함된 Vision model과 외부 model 구분 | `README.md` |
| `docs/` | 시스템, software, hardware, 실행 흐름 문서 | `*.md` |

## 저장소에 포함하지 않는 항목

- Python virtual environment와 package cache
- Whisper/NLLB/Piper 외부 model과 실행 파일
- Nordic nRF Connect SDK 및 Zephyr SDK 전체
- runtime log/output, 녹음, cache, `__pycache__`, `*.pyc`
- backup archive, 발표자료, 보고서 PDF, 시연영상 원본

시스템 구조는 외부 PNG 없이 GitHub에서 직접 렌더링되는 Mermaid diagram으로 제공합니다.
