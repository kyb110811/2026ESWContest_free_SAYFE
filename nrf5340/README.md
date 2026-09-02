# nRF5340 Audio DK / Auracast 구성

## 1. 역할

SAYFE는 건설현장 안전정보를 **한국어(KOREAN), 중국어(CHINESE), 베트남어(VIETNAMESE)** 3개 언어로 전달합니다.

각 언어의 Audio 출력 경로는 다음과 같이 구성됩니다.

- **KOREAN** → Audio Jetson → BTD700 → 한국어 방송
- **CHINESE** → Audio Jetson → nRF5340 Audio DK → Auracast Broadcast
- **VIETNAMESE** → Audio Jetson → nRF5340 Audio DK → Auracast Broadcast

즉, **nRF5340 Audio DK는 SAYFE의 3개 언어 중 CHINESE와 VIETNAMESE 방송의 Auracast 송출을 담당합니다.**

Audio Jetson에서 생성된 중국어·베트남어 PCM Audio를 nRF5340 Audio DK의 USB Audio Interface로 전달하고, nRF5340 Audio DK는 이를 Auracast Broadcast로 송출합니다.

실제 시연에서는 Galaxy 스마트폰의 LG ThinQ 앱을 통해 Auracast 방송을 검색·선택하고, **LG XBOOM Rock**이 Auracast Receiver로 중국어·베트남어 안전방송을 수신·재생합니다.

---

## 2. 전체 Audio 출력 구조

```text
                  관리자 한국어 음성 / 위험 이벤트
                              ↓
                   NVIDIA Jetson Orin Nano 8GB
                              ↓
              STT / 용어 정규화 / 번역 / TTS
                              ↓
         ┌────────────────────┼────────────────────┐
         │                    │                    │
      KOREAN               CHINESE             VIETNAMESE
         │                    │                    │
         ↓                    └─────────┬──────────┘
      BTD700                            ↓
         │                     auracast_output.py
         ↓                              ↓
   한국어 안전방송               48 kHz Stereo PCM
                                        ↓
                               nRF5340 Audio DK
                                        ↓
                               Auracast Broadcast
                                        ↓
                         Galaxy 스마트폰 / LG ThinQ
                              방송 검색·선택
                                        ↓
                                LG XBOOM Rock
                              Auracast 수신·재생
                                        ↓
                                  외국인 근로자
```

한국어(KOREAN)는 nRF5340 Auracast 경로를 사용하지 않고 **BTD700을 통해 별도로 출력**합니다.

nRF5340 Audio DK는 **CHINESE / VIETNAMESE 전용 Auracast 송출 경로**를 담당합니다.

Galaxy 스마트폰은 SAYFE의 필수 Software Module이나 Audio 출력 장치가 아닙니다.

실제 시연에서는 Galaxy 스마트폰의 LG ThinQ 앱을 이용하여 Auracast 방송을 검색·선택하는 제어 단말로 사용하며, 실제 방송 음성의 수신·재생은 **LG XBOOM Rock**이 담당합니다.

---

## 3. nRF5340 Audio DK 입력

nRF5340 Audio DK는 Audio Jetson으로부터 크게 두 종류의 입력을 전달받습니다.

### 3.1 Serial Control

Auracast 방송 설정을 위한 Serial Command를 전달합니다.

- Device: `/dev/ttyACM0`
- Baud Rate: `115200`
- Command Interface: `nac`

다음 파일에서 Serial을 통해 nRF5340 Audio DK의 Auracast 방송 환경을 설정합니다.

```text
audio/scripts/setup_auracast_zh_vi.py
```

### 3.2 USB Audio

Audio Jetson에서 생성된 CHINESE / VIETNAMESE PCM Audio를 nRF5340 Audio DK의 USB Audio Interface로 전달합니다.

Audio Format은 다음과 같습니다.

- Sample Rate: `48 kHz`
- Format: `S16_LE`
- Channel: Stereo
- Left Channel: CHINESE
- Right Channel: VIETNAMESE

---

## 4. Auracast 방송 설정

SAYFE에서는 다음 스크립트를 통해 nRF5340 Audio DK의 Auracast 방송 환경을 설정합니다.

```text
audio/scripts/setup_auracast_zh_vi.py
```

주요 설정 명령은 다음과 같습니다.

```text
nac stop
nac clear
nac preset 48_4_2 0
nac preset 48_4_2 1
nac num_bises 1 0 0
nac num_bises 1 1 0
nac program_info "Construction Safety Chinese" 0 0
nac program_info "Construction Safety Vietnamese" 1 0
nac broadcast_name "CHINESE              " 0
nac broadcast_name "VIETNAMESE           " 1
nac start
```

두 개의 방송 인스턴스를 구성하여 중국어와 베트남어 안전방송을 송출합니다.

| 방송 인스턴스 | Broadcast Name | 언어 | 역할 |
|---|---|---|---|
| 0 | `CHINESE` | 중국어 | 중국어 안전방송 |
| 1 | `VIETNAMESE` | 베트남어 | 베트남어 안전방송 |

한국어 방송은 해당 nRF5340 방송 인스턴스를 사용하지 않고 BTD700 출력 경로를 사용합니다.

---

## 5. Audio Streaming

CHINESE / VIETNAMESE Audio Streaming은 다음 파일에서 처리합니다.

```text
audio/src/audio/auracast_output.py
```

주요 기능은 다음과 같습니다.

- CHINESE PCM Queue 관리
- VIETNAMESE PCM Queue 관리
- Audio Sample Rate 48 kHz 처리
- S16_LE PCM 생성
- CHINESE / VIETNAMESE Stereo Channel 구성
- Audio가 없는 Channel에 Silence 삽입
- ALSA / `aplay`를 통한 nRF5340 USB Audio 출력
- Fast Path 위험방송 발생 시 일반 Audio Queue보다 우선 출력

실제 PCM 출력은 다음과 같은 형태로 수행됩니다.

```bash
aplay -q \
  -D plughw:CARD=Audio,DEV=0 \
  -t raw \
  -f S16_LE \
  -c 2 \
  -r 48000 -
```

Audio Jetson에서 생성된 Stereo PCM을 nRF5340 Audio DK의 USB Audio Interface로 전달한 뒤, nRF5340 Audio DK가 이를 Auracast로 송출합니다.

---

## 6. SAY:FE Audio 실행 흐름

```text
audio/run_ui_demo.sh
│
├─ setup_auracast_zh_vi.py
│  └─ nRF5340 Serial nac 설정
│
└─ safety_web.py
   │
   └─ ui_mic_controller.py
      │
      └─ ui_gpu_worker.py
         │
         ├─ STT
         ├─ 건설현장 용어 정규화
         ├─ CHINESE / VIETNAMESE 번역
         ├─ TTS
         │
         ├─ KOREAN
         │   └─ BTD700
         │       └─ 한국어 안전방송
         │
         └─ CHINESE / VIETNAMESE
             └─ auracast_output.py
                 └─ 48 kHz Stereo PCM
                     ↓
                 nRF5340 Audio DK
                     ↓
                 Auracast Broadcast
```

SAYFE Audio 시스템에서는 하나의 Audio 처리 시스템에서 3개 언어의 출력 경로를 관리하지만, 실제 출력 장치는 언어에 따라 구분됩니다.

| 언어 | 출력 경로 |
|---|---|
| `KOREAN` | Audio Jetson → BTD700 |
| `CHINESE` | Audio Jetson → nRF5340 Audio DK → Auracast |
| `VIETNAMESE` | Audio Jetson → nRF5340 Audio DK → Auracast |

---

## 7. 주요 파일

| 파일 | 역할 |
|---|---|
| [`../audio/scripts/setup_auracast_zh_vi.py`](../audio/scripts/setup_auracast_zh_vi.py) | Serial을 통해 nRF5340 Audio DK의 Auracast 방송 환경 설정 |
| [`../audio/src/audio/auracast_output.py`](../audio/src/audio/auracast_output.py) | CHINESE / VIETNAMESE PCM Queue 관리 및 48 kHz Stereo PCM 출력 |
| [`../audio/scripts/ui_gpu_worker.py`](../audio/scripts/ui_gpu_worker.py) | STT·번역·TTS·Fast Path 처리 및 Audio Output 연동 |
| [`../audio/scripts/ui_mic_controller.py`](../audio/scripts/ui_mic_controller.py) | Microphone 입력 및 Audio Worker 실행 관리 |
| [`../audio/run_ui_demo.sh`](../audio/run_ui_demo.sh) | nRF5340 Auracast 설정 후 SAY:FE Audio UI 실행 |

---

## 8. nRF Connect SDK Source

SAYFE의 Auracast 송출 환경은 Nordic Semiconductor의 **nRF Connect SDK 기반 nRF Audio 환경**을 사용합니다.

경진대회 제출 및 구현 환경 확인을 위해 본 Repository에는 사용한 nRF 관련 Source를 다음 경로에 포함합니다.

```text
nrf5340/
└── ncs/
    └── v3.4.0/
        └── nrf/
            ├── applications/
            │   └── nrf_audio/
            │
            └── samples/
                └── bluetooth/
                    └── nrf_auraconfig/
```

### Nordic Semiconductor 제공 Source

다음 Source는 Nordic Semiconductor의 nRF Connect SDK에 포함된 코드입니다.

```text
nrf5340/ncs/v3.4.0/nrf/applications/nrf_audio/
```

```text
nrf5340/ncs/v3.4.0/nrf/samples/bluetooth/nrf_auraconfig/
```

### SAY:FE 팀 작성 Integration Code

Nordic Semiconductor 제공 Source와 별도로, SAY:FE에서는 **Audio Jetson과 nRF5340 Audio DK를 연동하기 위한 Host-side Integration Code**를 작성하였습니다.

```text
audio/scripts/setup_auracast_zh_vi.py
audio/src/audio/auracast_output.py
audio/scripts/ui_gpu_worker.py
audio/run_ui_demo.sh
```

SAY:FE에서는 Nordic에서 제공하는 nRF Audio 기반 환경 위에 다음 기능을 연동하였습니다.

- CHINESE / VIETNAMESE 방송 설정
- Serial `nac` Command 제어
- CHINESE / VIETNAMESE 독립 PCM Queue 관리
- 48 kHz Stereo PCM 생성
- USB Audio Interface를 통한 nRF5340 Audio 전달
- Auracast Broadcast 연동
- Fast Path 위험경고 우선 출력

즉, **Nordic에서 제공하는 nRF Audio 환경과 SAYFE 팀이 직접 작성한 Host-side Audio Integration Code를 결합하여 CHINESE / VIETNAMESE Auracast 안전방송 시스템을 구성하였습니다.**

---

## 9. Fast Path 연동

SAYFE에서는 일반 관리자 방송뿐 아니라 위험 이벤트 발생 시 즉시 경고방송을 출력하는 **Fast Path**를 지원합니다.

주요 위험 이벤트는 Vision 및 Gas 시스템에서 발생합니다.

```text
Vision / Gas 위험 이벤트
        ↓
Audio Jetson Fast Path
        ↓
3개 언어 위험경고 Audio
        ↓
        ├─ KOREAN
        │    ↓
        │  BTD700
        │    ↓
        │  한국어 위험경고
        │
        └─ CHINESE / VIETNAMESE
             ↓
        auracast_output.py
             ↓
      일반 Audio Queue 선점
             ↓
       nRF5340 Audio DK
             ↓
       Auracast Broadcast
             ↓
        LG XBOOM Rock
             ↓
        외국인 근로자
```

Fast Path가 발생하면 일반 관리자 방송보다 위험경고 방송을 우선 처리합니다.

CHINESE / VIETNAMESE 위험경고 Audio 역시 일반 방송과 동일한 nRF5340 Auracast 출력 경로를 사용합니다.

---

## 10. 출력

SAY:FE Audio 시스템은 다음 3개 언어의 안전방송을 제공합니다.

| Broadcast Name | 언어 | 주요 출력 경로 |
|---|---|---|
| `KOREAN` | 한국어 | BTD700 |
| `CHINESE` | 중국어 | nRF5340 Audio DK → Auracast |
| `VIETNAMESE` | 베트남어 | nRF5340 Audio DK → Auracast |

nRF5340 Audio DK가 담당하는 출력은 다음과 같습니다.

- `CHINESE` 중국어 관리자 안전지시 방송
- `VIETNAMESE` 베트남어 관리자 안전지시 방송
- `CHINESE` Vision Fast Path 위험경고
- `VIETNAMESE` Vision Fast Path 위험경고
- `CHINESE` Gas Fast Path 위험경고
- `VIETNAMESE` Gas Fast Path 위험경고

최종 CHINESE / VIETNAMESE 방송은 LG XBOOM Rock과 같은 Auracast Receiver를 통해 근로자에게 전달됩니다.

---

## 11. 실행 방법

Audio Jetson의 SAYFE 프로젝트에서 다음과 같이 실행합니다.

```bash
cd ~/construction_safety
./run_ui_demo.sh
```

Gas Sensor 연동까지 포함한 실제 통합 실행 환경에서는 다음과 같이 실행할 수 있습니다.

```bash
cd ~/construction_safety

SAYFE_GAS_ENABLED=1 \
SAYFE_GAS_MAC=80:F1:B2:64:32:02 \
SAYFE_GAS_THRESHOLD=1000 \
./run_ui_demo.sh
```

`run_ui_demo.sh`는 Audio UI 실행 전에 `setup_auracast_zh_vi.py`를 호출하여 nRF5340 Audio DK의 Auracast 방송 환경을 설정합니다.

정상 실행을 위해 다음 조건이 필요합니다.

- NVIDIA Jetson Orin Nano 8GB
- nRF5340 Audio DK 연결
- `/dev/ttyACM0` Serial 장치 인식
- nRF5340 USB Audio Device 인식
- Serial / Audio 장치 접근 권한
- SAYFE Audio 실행 환경 구성

---

## 12. Third-Party Software

This project uses software components provided by Nordic Semiconductor ASA.

The applicable Nordic Semiconductor software components are distributed under the Nordic 5-Clause License.

The original license text is provided in [`THIRD_PARTY_LICENSES.txt`](../THIRD_PARTY_LICENSES.txt).

nRF 관련 Source에 포함된 기존 License, Notice 및 SPDX 정보는 원본 상태를 유지합니다.

Nordic Semiconductor가 제공하는 Source와 SAYFE 팀이 작성한 Integration Code는 본 문서에서 구분하여 명시하였습니다.
