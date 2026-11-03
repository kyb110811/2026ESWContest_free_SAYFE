# SAYFE AudioDetection

> **Experimental / Not used in final demonstration:** 이 위험 음향 감지 자료는 별도 실험 기능입니다. 최종 결선 핵심 기능과 모델은 [메인 README](../../README.md)와 [모델 안내](../../models/README.md)를 기준으로 확인하십시오.

세 카메라(CAM1·CAM2·CAM3)의 USB 마이크를 따로 입력받아 공식 [PretrainedSED](https://github.com/fschmid56/PretrainedSED)의
`frame_mn06_strong_1`로 실시간 Sound Event Detection을 수행한다.
원본 코드 revision은 `1aa47e482f7e89904cba2338999345025d8b4e36`으로 고정했다.
모델은 **447개 AudioSet Strong 클래스**를 추론하며, 상시 높게 나오는 `Mechanisms`는 결과에서 제외해 **446개 클래스**를 표시한다. 527개 AudioSet Weak 모델이 아니다.

## 실행

현재 장치에는 코드·가중치·오디오 의존성을 설치하고 CAM1·CAM2 및 새 CAM3 마이크 입력을 확인했다.
프로젝트 루트의 `run.sh`가 Vision과 AudioDetection을 같은 Python 프로세스에서 실행한다.

```bash
cd ~/SAYFE_yeongjun
./run.sh
```

접속: `http://localhost:5011` 또는 `http://<Jetson IP>:5011`.
구역별 3카메라 화면: `http://localhost:5012` 또는 `http://<Jetson IP>:5012`.
CAM1(C922)·CAM2(046d:0825)는 A구역, CAM3(FHD60F)는 B구역이다.
5012 화면은 기존 비전 영상 두 개를 공유하고 CAM3 영상만 별도로 연다. 세 마이크의 최신 상위 소리와
폭발음 감지 위치를 구역별로 표시하며, 위험 소리는 빨간색으로 표시한다. 사이렌 점수는 최신 소리·전체 클래스 목록에서 확인할 수 있다.
감지 구역은 해당 마이크의 설치 구역이며 음원 위치를 삼각측량한 결과가 아니다.
CAM3 영상은 `/dev/v4l/by-id`에서 `FHD60F`와 `video-index0`을 포함하는 장치를 찾는다.
장치 이름이 다르면 `AudioDetection/config.json`의 CAM3에 `video_source` 절대 경로를 넣을 수 있다.
영상 장치가 없거나 연결이 끊겨도 오디오 감지는 계속되고 화면에 영상 오류가 표시된다.
비전 화면은 5010 포트를 사용한다. Explosion 감지 시작 이벤트는 같은 프로세스의 Vision 상태에 직접 전달되어
기존 Vision Heartbeat의 `vision.audio_explosions`에 포함한다. 오디오는 비전 판정·RESET·LATCH를 변경하지 않는다.
Ctrl+C로 두 작업을 함께 종료한다. 마이크 잠금으로 AudioDetection 중복 실행을 막으므로
기존 `AudioDetection/run.sh` 인스턴스가 있다면 먼저 종료해야 한다. Vision만 실행하려면 `./run.sh --no-audio`를 사용한다.
브라우저는 Ctrl+F5로 새로고침한다. 웹은 화면 폭에 맞춰 세 마이크 카드를 배치한다.

새 장치에서 처음 설치하거나 의존성이 없을 때:

```bash
./AudioDetection/setup.sh
./AudioDetection/run.sh --check-model
./AudioDetection/run.sh --list-devices
```

`setup.sh`는 upstream 코드, CPU torchaudio wheel, 학습 가중치를 이 폴더에만 설치한다.
기존 sayfe_vision의 Torch/TorchVision/NumPy를 교체하지 않는다. Torch는 현재 환경의 2.8.0을 사용하고
torchaudio 2.8.0은 `.deps/`에서만 불러온다. 설치에 네트워크가 필요하며 설치 후 추론은 네트워크 다운로드 없이 수행한다.
기본 Python은 `~/venvs/sayfe_vision/bin/python`이며 `SAYFE_VENV`로 바꿀 수 있다.

## 마이크 연결

`config.json`에 현재 확인한 USB 장치의 ALSA 카드 이름을 저장했다. 숫자 카드 인덱스의 재부팅 변동을 피한다.

| 카메라 | 마이크 | ALSA 입력 |
|---|---|---|
| CAM1 | C922 Pro Stream Webcam | `plughw:CARD=Webcam,DEV=0` |
| CAM2 | USB Device 046d:0825 | `plughw:CARD=U0x46d0x825,DEV=0` |
| CAM3 | SunplusIT FHD60F | `plughw:CARD=FHD60F,DEV=0` |

입력은 ALSA `arecord`로 받는다. 16 kHz, mono, signed 16-bit PCM으로 변환한다.
장치를 바꿨다면 `./run.sh --list-devices`로 확인하고 이 폴더의 `config.json`만 수정한다.
마이크별로 캡처 작업자를 두고 추론 작업자 하나가 최신 입력을 모아 처리한다. 밀린 오디오 추론을 계속 쌓지 않는다.
입력 개수는 설정 목록에서 읽으며 워밍업·모델 검사도 같은 개수로 수행한다. 카메라 ID와 장치는 중복될 수 없다.
CAM3가 끊겨도 다른 마이크의 결과를 계속 표시하며, 감지·해제·cooldown은 마이크별로 따로 관리한다.

## 추론과 위험 이벤트

- 모델이 학습한 10초 문맥을 유지한다. 시작 시 실제 입력이 1초 이상 모이면 왼쪽을 0으로 채워 먼저 판정을 시작한다.
- `sigmoid(strong_logits)`의 최근 1초 프레임들에서 클래스별 최대 점수를 계산한다.
  이전 10초 전체의 최고 점수를 현재 위험으로 사용하지 않는다.
- `Mechanisms`를 제외한 446개 점수는 API와 웹의 펼치기/검색 목록에서 확인한다. 여러 클래스의 점수는 합이 100%가 되는 분류가 아니다.
- `Explosion` 판정 점수는 `Explosion`, `Artillery fire`, `Bang`, `Boom`, `Burst, pop`, `Eruption`, `Firecracker`, `Fireworks`, `Fusillade`, `Gunshot, gunfire`, `Sonic boom`의 점수를 합산하고 최대 1.0으로 제한한다. 합산된 값으로 폭발 위험 이벤트를 한 번 생성하며 Vision Heartbeat에도 기존 `Explosion` 이벤트로 전달한다. API의 전체 클래스 점수와 상위 10개 목록은 원본 모델 점수다.
- Siren 및 사이렌 하위 클래스는 계속 추론·표시하지만 위험 소리로 처리하지 않는다.
- 기본 감지 조건은 **위험 클래스 점수 ≥ 0.5**, 또는 **전체 1위가 위험 클래스이고 점수 ≥ 0.2**다.
  다른 소리가 1위여도 합산된 Explosion 점수가 0.5를 넘으면 감지한다.
- 1위라도 매우 낮은 점수는 이벤트로 만들지 않는다. 이 기준은 `danger_threshold`, `top1_min_score`로 조절한다.
- 이미 감지 중인 소리는 점수가 0.25 이상이면 유지한다. 마지막 유지 조건 이후 1.5초 동안 조건이 없으면 해제한다.
- 연속 감지는 매 프레임 새 이벤트를 만들지 않는다. 재감지 알림은 카메라·클래스별 5초 cooldown을 적용한다.
- 마이크/모델 오류나 3초 이상 된 결과는 UNKNOWN으로 표시하고 과거 점수를 숨긴다.
  입력 끊김 후에는 문맥을 초기화하며, 끊기기 전 입력으로 뒤늦게 끝난 추론 결과는 버린다.

`hop_seconds=0.5`는 목표 갱신 간격이다. 추론이 더 오래 걸리면 실제 갱신 속도는 그 처리 시간에 제한된다.
기본값은 CPU 2개 스레드로 비전 GPU와의 경합을 줄인다. 기존 두 채널 실제 입력 검증에서는 배치 추론이 약 0.76~1.0초였다.
3채널 `--check-model` 출력은 `[3,446]`이다. 제외 전 검사용 첫 배치(`[3,447]`)는 약 2.33초였으며 지속 실행 성능 측정값은 아니다.
더 빠른 GPU 처리가 필요하면 `device`를 `cuda`로 변경할 수 있지만 비전 FPS와 함께 측정해야 한다.
폭발 유사 라벨의 합산은 중복되거나 일상적인 큰 소리에도 반응할 수 있으므로, 현장 오탐·미탐은 별도 녹음/재생 검증으로 임계값과 포함 라벨을 조정해야 한다.

## API와 기록

- `GET /api/status`: 모델 정보, 표시 라벨 446개, 마이크별 최신 `scores[446]`, `top[10]`, `hazards`, 입력/결과 나이, 추론 시간, 이벤트.
- `GET /api/status`의 `vision_event_delivery`: Explosion 로컬 전달 건수, 대기 수, 최근 오류.
- `GET /api/events`: 최근 이벤트. `audio_danger_started`, `audio_danger_ended`가 감지 시작/해제다.
- `runs/<run>/events.jsonl`: 이벤트 영구 기록. 카메라·소리·점수·기준·입력 시각·sequence를 포함한다.
- `runs/<run>/predictions.jsonl`: 상위 10개·위험 소리·처리 시간 기록. 전체 클래스는 API로 제공하며 디스크에는 상위 결과를 저장한다.
- `runs/<run>/model.json`: 가중치 hash와 upstream revision. `summary.json`: 종료 시 입력·추론 횟수.

원본 음성은 파일로 저장하지 않는다. 기본 통합 실행에서는 Explosion 시작 이벤트를 Vision 상태에
프로세스 내부 호출로 전달한다. 단독 `AudioDetection/run.sh` 실행 시에는 `vision_event_enabled=true`이면
`127.0.0.1:5010/api/audio/explosion`으로 전달하고 연결 실패를 재시도한다.
  같은 이벤트 ID는 Vision에서 중복 저장하지 않으며 사이렌 이벤트는 외부로 전달하지 않는다.
가중치 SHA-256: `5b8be0664ee194c0413010ae0c6886560f4fd98a9ca1a0c2825e409dfdf33472`.

## 검증

```bash
# 기존 프로젝트 루트에서 실행
~/venvs/sayfe_vision/bin/python -s -B -m unittest discover -s tests -p test_audio_detection.py
# 실제 마이크 + 실제 모델 + 별도 HTTP 검사 서버. 18초 후 자동 종료.
~/venvs/sayfe_vision/bin/python -s -B AudioDetection/verify_live.py
# 기존 오디오 서버가 CAM1/CAM2를 사용 중이면 새 마이크만 별도로 검사
~/venvs/sayfe_vision/bin/python -s -B AudioDetection/verify_live.py --camera CAM3
```

오디오 자동 테스트 16개 통과. 링 버퍼, top1/임계값 감지, 다중 클래스, 세 카메라 독립 이벤트,
히스테리시스/해제/cooldown, stale 처리, 입력 복구 중 이전 결과 제외, 전체 447개 점수/API/JSONL을 검증했다.
추가 테스트는 3개 입력의 워밍업·배치 출력 매핑, CAM3 장애 시 다른 채널 결과 유지, 가변 입력 수와 중복 설정 거부를 검증한다.

새 CAM3 실제 입력 검증에서 유효 HTTP 스냅샷 28개, 447개 클래스 출력, 추론 12회, 입력 오류 없음을 확인했다.
마지막 CAM3 추론 647.5ms, 입력→결과 약 676ms였다. 기존 오디오 서버가 CAM1/CAM2를 점유 중이어서
세 마이크의 동시 실입력은 이번에 재검사하지 않았고, CAM3 개별 실입력과 3채널 모델 출력을 각각 확인했다.
기록: `runs/diagnostics/20261031T172410_live.json`.

기존 2채널 실제 마이크 검증에서는 27개의 유효 HTTP 스냅샷을 확인했고 두 채널 모두 447개 점수를 반환했다.
CAM1 13회/CAM2 12회 추론, 입력 오류 없음. 마지막 배치 755.8ms, 입력→결과 약 775ms였다.
기록: `runs/diagnostics/20261031T164653_live.json`.

이전 검증에서 기존 비전 대시보드 JavaScript 테스트 29개도 통과했다. 당시 전체 Python 테스트는 255개 중 254개 통과했고,
`test_disabled_defaults_and_project_settings_do_not_create_observer_or_socket` 1개는 현재 프로젝트의
`config.json`이 `heartbeat.enabled=true`인 반면 테스트가 false를 기대해서 실패했다.
이번 작업에서는 기존 Heartbeat 설정·송신 로직을 수정하지 않았다.

실제 폭발·사이렌 정답 음원은 재생하지 않았다. 실입력/모델 실행과 이벤트 판단 로직을 각각 검증했으며
위험 소리의 현장 인식 정확도를 측정한 결과는 아니다.
