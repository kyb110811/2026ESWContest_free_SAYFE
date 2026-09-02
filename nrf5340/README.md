# nRF5340 Audio DK / Auracast 구성

## 역할

nRF5340 Audio DK는 Audio 시스템이 생성한 중국어·베트남어 Audio를 Auracast로 방송하는 경로입니다. 실제 시연에서는 LG xboom Rock이 Auracast Receiver로 방송 음성을 재생합니다.

## 입력

- NVIDIA Jetson Orin Nano 8GB에서 전달되는 ZH/VI Audio stream
- `/dev/ttyACM0`, 115200 baud serial의 `nac` 설정 명령

## 처리 과정

```text
Audio Jetson
├─ setup_auracast_zh_vi.py → serial nac commands
│  ├─ BIG 0 / CHINESE
│  └─ BIG 1 / VIETNAMESE
└─ auracast_output.py → ZH/VI stereo PCM
   → nRF5340 Audio DK → Auracast Broadcast
   → Galaxy 스마트폰의 LG ThinQ 앱에서 방송 검색·선택
   → LG xboom Rock에서 Auracast 수신·재생
   → 외국인 근로자
```

실제 시연에서는 Galaxy 스마트폰의 LG ThinQ 앱으로 Auracast 방송을 검색·선택했습니다. Galaxy는 Repository의 필수 software module이나 Audio 출력 장치가 아니며, 실제 방송 수신·재생은 LG xboom Rock이 담당합니다.

## 출력

- `CHINESE` 방송 프로그램
- `VIETNAMESE` 방송 프로그램
- LG xboom Rock 등 Auracast Receiver가 수신하는 중국어·베트남어 방송

## 주요 파일

| 파일 | 역할 |
|---|---|
| `../audio/scripts/setup_auracast_zh_vi.py` | `nac stop/clear`, preset, BIS, program info, broadcast name을 설정하고 방송 시작 |
| `../audio/src/audio/auracast_output.py` | Piper/Fast Path ZH·VI Audio를 독립 queue로 관리하고 nRF5340용 PCM stream 생성 |
| `../audio/run_ui_demo.sh` | nRF5340 설정 script 실행 후 Audio UI 시작 |

## Firmware Source 범위

이 제출본에는 별도의 팀 수정 nRF5340 Firmware Source가 식별되어 있지 않습니다. Nordic nRF Connect SDK와 Zephyr 전체는 외부 SDK이므로 저장소에 포함하지 않았으며, 팀 작성 범위로 확인되는 것은 위 serial setup script와 Audio streaming integration입니다.

## 실행 방법

`audio/run_ui_demo.sh`가 Audio UI 시작 전에 `setup_auracast_zh_vi.py`를 호출합니다. nRF5340 Audio DK가 `/dev/ttyACM0`으로 연결되어 있고 serial/Audio 장치 접근 권한이 있어야 합니다.
