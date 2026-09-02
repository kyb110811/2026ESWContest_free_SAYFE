# nRF5340 Audio DK / Auracast 구성

## 1. 역할

SAY:FE의 nRF5340 Audio DK는 Audio Jetson에서 생성된 중국어(ZH)·베트남어(VI) 안전방송 음성을 Auracast로 송출하는 역할을 담당합니다.

Audio Jetson에서 생성된 중국어·베트남어 PCM Audio를 nRF5340 Audio DK의 USB Audio Interface로 전달하고, nRF5340 Audio DK가 이를 Auracast Broadcast로 송출합니다.

실제 시연에서는 Galaxy 스마트폰의 LG ThinQ 앱을 통해 Auracast 방송을 검색·선택하고, LG xboom Rock이 Auracast Receiver로 방송 음성을 수신·재생합니다.

---

## 2. 시스템 흐름

```text
관리자 한국어 음성 / 위험 이벤트
        ↓
NVIDIA Jetson Orin Nano 8GB
        ↓
STT / 건설현장 용어 정규화 / 번역 / TTS
        ↓
중국어(ZH) / 베트남어(VI) Audio
        ↓
auracast_output.py
        ↓
48 kHz Stereo PCM
        ↓
nRF5340 Audio DK
        ↓
Auracast Broadcast
        ↓
Galaxy 스마트폰 / LG ThinQ
방송 검색·선택
        ↓
LG xboom Rock
Auracast 수신·재생
        ↓
외국인 근로자
```

Galaxy 스마트폰은 SAY:FE의 필수 Software Module이나 Audio 출력 장치가 아닙니다.

실제 시연에서 Galaxy 스마트폰은 LG ThinQ 앱을 이용하여 Auracast 방송을 검색·선택하는 제어 단말로 사용하며, 실제 방송 음성의 수신·재생은 LG xboom Rock이 담당합니다.

---

## 3. 입력

nRF5340 Audio DK는 Audio Jetson으로부터 다음 두 종류의 입력을 사용합니다.

### 3.1 Serial Control

- Device: `/dev/ttyACM0`
- Baud Rate: `115200`
- Command Interface: `nac`

`setup_auracast_zh_vi.py`에서 Serial을 통해 nRF5340 Audio DK의 Auracast 방송 설정 명령을 전달합니다.

### 3.2 USB Audio

Audio Jetson에서 생성된 중국어·베트남어 PCM Audio를 nRF5340 Audio DK의 USB Audio Interface로 전달합니다.

- Sample Rate: `48 kHz`
- Format: `S16_LE`
- Channel: Stereo
- Left Channel: Chinese
- Right Channel: Vietnamese

---

## 4. Auracast 방송 설정

SAY:FE에서는 다음 스크립트를 통해 nRF5340 Audio DK의 Auracast 방송 환경을 설정합니다.

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

| 방송 인스턴스 | Broadcast Name | 용도 |
|---|---|---|
| 0 | `CHINESE` | 중국어 안전방송 |
| 1 | `VIETNAMESE` | 베트남어 안전방송 |

---

## 5. Audio Streaming

중국어·베트남어 Audio Streaming은 다음 파일에서 처리합니다.

```text
audio/src/audio/auracast_output.py
```

주요 기능은 다음과 같습니다.

- 중국어(ZH) PCM Queue 관리
- 베트남어(VI) PCM Queue 관리
- Audio Sample Rate 48 kHz 처리
- S16_LE PCM 생성
- 중국어·베트남어 Audio의 Stereo Channel 구성
- Audio가 없는 Channel에 Silence 삽입
- ALSA / `aplay`를 통한 nRF5340 USB Audio 출력
- Fast Path 위험방송 발생 시 일반 Audio Queue보다 우선 출력

실제 PCM 출력은 다음 형태로 수행됩니다.

```bash
aplay -q \
  -D plughw:CARD=Audio,DEV=0 \
  -t raw \
  -f S16_LE \
  -c 2 \
  -r 48000 -
```

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
         ├─ 중국어 / 베트남어 번역
         ├─ TTS
         │
         └─ auracast_output.py
            │
            └─ 48 kHz Stereo PCM
               ↓
            nRF5340 Audio DK
               ↓
            Auracast Broadcast
```

---

## 7. 주요 파일

| 파일 | 역할 |
|---|---|
| [`../audio/scripts/setup_auracast_zh_vi.py`](../audio/scripts/setup_auracast_zh_vi.py) | Serial을 통해 nRF5340 Audio DK의 Auracast 방송 설정 |
| [`../audio/src/audio/auracast_output.py`](../audio/src/audio/auracast_output.py) | 중국어·베트남어 PCM Queue 관리 및 48 kHz Stereo PCM 출력 |
| [`../audio/scripts/ui_gpu_worker.py`](../audio/scripts/ui_gpu_worker.py) | STT·번역·TTS·Fast Path 처리 및 Audio Output 연동 |
| [`../audio/scripts/ui_mic_controller.py`](../audio/scripts/ui_mic_controller.py) | Microphone 입력 및 Audio Worker 실행 관리 |
| [`../audio/run_ui_demo.sh`](../audio/run_ui_demo.sh) | nRF5340 Auracast 설정 후 SAY:FE Audio UI 실행 |

---

## 8. nRF Connect SDK Source

SAY:FE의 Auracast 송출 환경은 Nordic Semiconductor의 nRF Connect SDK 기반 nRF Audio 환경을 사용합니다.

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

### Nordic 제공 Source

다음 Source는 Nordic Semiconductor의 nRF Connect SDK에 포함된 코드입니다.

```text
nrf5340/ncs/v3.4.0/nrf/applications/nrf_audio/
```

```text
nrf5340/ncs/v3.4.0/nrf/samples/bluetooth/nrf_auraconfig/
```

### SAY:FE 팀 작성 Integration Code

Nordic 제공 Source와 별도로, SAY:FE에서는 Audio Jetson과 nRF5340 Audio DK를 연동하기 위한 Host-side Integration Code를 작성하였습니다.

```text
audio/scripts/setup_auracast_zh_vi.py
audio/src/audio/auracast_output.py
audio/scripts/ui_gpu_worker.py
audio/run_ui_demo.sh
```

Nordic에서 제공하는 nRF Audio 기반 환경 위에 SAY:FE에서 작성한 Serial 설정 및 PCM Audio Streaming 기능을 연동하여 중국어·베트남어 Auracast 안전방송 시스템을 구성하였습니다.

---

## 9. Fast Path 연동

SAY:FE에서는 일반 관리자 방송뿐 아니라 위험 이벤트 발생 시 즉시 경고방송을 출력하는 Fast Path를 지원합니다.

Fast Path 발생 시 일반 Audio보다 위험경고 방송을 우선 처리하며, 중국어·베트남어 경고 Audio 역시 동일한 nRF5340 Auracast 출력 경로를 사용합니다.

```text
Vision / Gas 위험 이벤트
        ↓
Fast Path
        ↓
ZH / VI Warning Audio
        ↓
auracast_output.py
        ↓
일반 Audio Queue 선점
        ↓
nRF5340 Audio DK
        ↓
Auracast Broadcast
        ↓
LG xboom Rock
        ↓
외국인 근로자
```

---

## 10. 출력

nRF5340 Auracast 경로를 통해 다음 방송을 제공합니다.

- `CHINESE` 중국어 안전방송
- `VIETNAMESE` 베트남어 안전방송
- 관리자 안전지시 방송
- Vision Fast Path 위험경고 방송
- Gas Fast Path 위험경고 방송

최종 방송은 LG xboom Rock과 같은 Auracast Receiver를 통해 근로자에게 전달됩니다.

---

## 11. 실행 방법

Audio Jetson의 SAY:FE 프로젝트에서 다음과 같이 실행합니다.

```bash
cd ~/construction_safety
./run_ui_demo.sh
```

`run_ui_demo.sh`는 Audio UI 실행 전에 `setup_auracast_zh_vi.py`를 호출하여 nRF5340 Audio DK의 Auracast 방송 환경을 설정합니다.

정상 실행을 위해 다음 조건이 필요합니다.

- nRF5340 Audio DK 연결
- `/dev/ttyACM0` Serial 장치 인식
- nRF5340 USB Audio Device 인식
- Serial / Audio 장치 접근 권한
- SAY:FE Audio 실행 환경 구성

---

## 12. Third-Party Software

This project uses software components provided by Nordic Semiconductor ASA.

The applicable Nordic Semiconductor software components are distributed under the Nordic 5-Clause License.

The original license text is provided in [`THIRD_PARTY_LICENSES.txt`](../THIRD_PARTY_LICENSES.txt).

nRF 관련 Source에 포함된 기존 License, Notice 및 SPDX 정보는 원본 상태를 유지합니다.

Nordic Semiconductor가 제공하는 Source와 SAY:FE 팀이 작성한 Integration Code는 본 문서에서 구분하여 명시하였습니다.
