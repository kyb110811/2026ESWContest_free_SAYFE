# 제출본 구성 확인

이 문서는 GitHub 제출본의 구성과 재현 범위를 요약합니다. 장비별 경로와 Bluetooth MAC address는 환경별 설정값으로 안내합니다.

## 포함된 실행 영역

| 영역 | 진입점 | 제출본 구성 |
|---|---|---|
| Audio | `audio/run_ui_demo.sh` | UI, VAD/STT integration, 정규화, 번역, TTS, Fast Path, KO/ZH/VI asset |
| Vision | `vision/run.sh` | Vision v.6 source와 `best.pt` |
| Raspberry Pi | `raspberry_pi/excavator_control.py` | RFCOMM JSON event handling과 GPIO control |
| ESP32-C3 | `esp32_gas/sketch_aug18a.ino` | MQ 측정과 BLE 송신 source |
| Integration | `integration/pi_rfcomm_bridge_server.py` | localhost HTTP → RFCOMM bridge |
| nRF5340 | `audio/scripts/setup_auracast_zh_vi.py` | ZH/VI Auracast serial setup |

## 확인된 제출 상태

- Python source 34개가 syntax 검사를 통과했습니다.
- 모든 shell script가 `bash -n` 검사를 통과했습니다.
- Fast Path에서 사용하는 KO/ZH/VI WAV 6개가 포함되어 있습니다.
- `vision/best.pt`: 5,452,570 bytes, SHA-256 `e56c12f5319ec222124cb99072a681820e759e5e2632db41a8d36c2ed3dcd2b4`
- `pi_rfcomm_bridge_server.py`의 `POST /event` → newline-delimited JSON → `/dev/rfcomm0` 흐름이 Vision sender와 Raspberry Pi decoder 구조에 대응합니다.
- backup/archive/cache와 100 MiB 초과 파일은 포함하지 않습니다.

## 환경별 설정 항목

- Audio, Raspberry Pi, ESP32-C3의 Bluetooth address와 RFCOMM channel
- Whisper server/model, NLLB CTranslate2 model, Piper binary/voice 위치
- `/dev/ttyACM0`, `/dev/rfcomm0`, ALSA device와 접근 권한
- Gas Threshold와 BLE device 설정
- Camera와 Microphone device

## 외부 자산 범위

virtual environment, 외부 model, Piper binary/voice, Nordic/Zephyr SDK, runtime output, cache, archive, 문서 PDF와 영상 원본은 GitHub 제출본에 포함하지 않습니다. 외부 구성요소는 [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)에 구분하여 기록합니다.

## 문서화하지 않은 미확정 정보

저장소에서 근거를 확인할 수 없는 성능 수치, Vision model의 정확한 dataset/성능, Camera·Microphone 세부 모델, 실제 시연 Galaxy의 정확한 모델, 별도 nRF5340 Firmware 수정 여부는 확정 정보로 기재하지 않습니다.
