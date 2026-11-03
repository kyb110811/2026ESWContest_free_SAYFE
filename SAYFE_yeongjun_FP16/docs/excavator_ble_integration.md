# Vision Jetson ↔ 굴착기 ESP32-C3 통합

기본값은 DRY-RUN이다. 별도 활성화 없이는 BLE 제어 명령을 쓰지 않는다.
`excavator_danger`만 구현했으며 `reset` 전송 경로는 없다.
실제 제한 적용·ACK·해제는 모두 미검증 상태로 유지한다.

**현재 작업 트리의 병행 변경 주의:** 최종 대조에서 다른 경로가 `main.py`,
`state.py`, `ble_excavator.py`, `config.json`을 변경한 사실을 확인했다.
그 경로는 BLE `enabled: true`, 관리자 RESET → 장치 `reset`, 재접속 시 위험
재전송, `response=False`를 사용한다. 아래 독립 브리지와 정책이 다르다.
이번 작업에서는 이 파일들을 수정하거나 원상 복구하지 않았다. 해당 변경은
`backups/external_ble_changes_20261031_184629/`에도 별도로 보존했다.
새 브리지는 이 직접 연결 설정이 활성화되어 있으면 LIVE 시작·송신을 거부한다.
현재 Vision을 종료·재시작하지 않았으며, 전체 시스템에 이 문서의 안전 정책을
적용하려면 직접 연결 경로와의 충돌부터 해소해야 한다.

## 기존 구조 분석

| 파일/구성 | 현재 역할 | 이번 연결 방식 |
| --- | --- | --- |
| `main.py` | Vision 전용 venv 검사, 카메라 잠금, 모델 워밍업, 파이프라인·웹·Heartbeat 시작/정리 | 변경 없음. 브리지는 별도 Python 프로세스 |
| `pipeline.py` | 단일 모델 추론 작업자, 카메라별 처리 작업자, 관측 상태 작업자. `state.publish()`와 `refresh_risk()` 호출 | BLE/HTTP 작업을 추가하지 않음 |
| `risk.py` | 굴착기 박스 확장, 사람 박스 교차 판정, 사람별 CAM1·CAM2 융합 및 위험 래치 | 변경 없음. 현재 `site_state`와 래치 이력 `risk`를 구분 |
| `state.py` | RuntimeState 잠금, 관측·위험 상태, 기록, 통합 이벤트 링 | 기존 `hazard_latched`, `hazard_reset` 활용 |
| `web_app.py` | UI, 상태 조회, 이벤트 조회, 관리자 RESET | 기존 GET 두 개만 사용. POST 호출 없음 |
| `vision_heartbeat.py` | 별도 수신기 통신 및 관측 상태 보고 | 변경 없음. BLE 명령과 분리 |
| `manual_events.py` / `/api/admin/events` | 관리자 수동 Mock 이벤트 | 자동 제어 입력으로 사용하지 않음 |

표의 '변경 없음'은 이번 작업에서 해당 파일을 편집하지 않았다는 뜻이다.
직접 연결 병행 변경 전의 구조를 기준으로 분석했다.

현재 융합에서는 같은 사람에 대해 SAFE 관측이 DANGER보다 우선하고,
UNKNOWN 관측은 다른 카메라의 판단에 위임한다. 두 관측이 UNKNOWN이면
안전으로 간주하지 않는다. DANGER가 확인되면 `hazard_latched`가 발생한다.
그 뒤 영역이 SAFE로 바뀌어도 위험 이력은 유지되며, 관리자 RESET은 현재
에피소드·작업자 이탈 확인·현재 관측 조건을 요구한다. 이 정책은 그대로다.

`GET /api/vision/events?after=N&run_id=...`는 다음을 제공한다.

- `schema_version: 1`, `run_id`, `latest_sequence`, `oldest_sequence`
- `reset_required`, `gap`, 최대 100개 `events`
- 각 이벤트의 `sequence`, `source: vision`, `event`, `episode_id`, `event_id`
- `hazard_reset`도 같은 위험 `episode_id`를 사용한다.

`GET /api/status`의 `run_id`, `running`, `hazard_latched`, `episode_id`, `risk`로
현재 위험 이력을 확인한다. 두 응답의 실행 ID가 다르거나 스키마가 잘못되면
명령을 보내지 않고 다음 조회에서 다시 확인한다. API 이벤트 조회 자체는
위험 판정이나 RESET을 실행하지 않는다.

## 기존 수동 BLE 코드 분석 및 보존

`excavator_ble_manual.py`는 원본 그대로 유지했다. `ble_excavator.py`도 이번 작업에서
수정하지 않았지만, 위에 설명한 병행 변경이 발견되어 작업 전 원본을 백업에 보존했다.
수동 프로그램은 다음 특성이 있어 자동 브리지에서 import/실행하지 않는다.

- 장치명을 기준으로 검색해 MAC·서비스를 검증하지 않는다.
- `input()`이 asyncio 루프를 막아 연결 해제 처리 등과 충돌할 수 있다.
- 재검색·재접속·중복 방지·지속 기록·상태 API가 없다.
- `response=False`로 쓰지만, 확인된 속성은 `read, write, notify`다.
- 쓰기 완료 출력만으로 장치 제한 적용 여부를 알 수 없다.
- 메뉴에 `reset`이 있어 자동 실행 경로로 재사용하기에 적합하지 않다.

작업 전 다음 디렉터리에 핵심 기존 파일 9개와 SHA-256 목록을 복사했다.

`backups/excavator_integration_20261031_183610/`

## 생성 파일과 동작

- `excavator_ble.py`: MAC 검색, 이름·서비스·특성 확인, 연결, 읽기,
  notify 수신, 연결 해제 콜백, 주기적 재접속, 제한 명령 쓰기.
- `excavator_bridge.py`: 기존 Vision API 소비, 중복 방지 SQLite 기록,
  독립 상태 HTTP 서버, 상태 JSON, 명시적 실행 모드.
- `tests/test_excavator_bridge.py`: Mock ESP32/HTTP 응답/프로세스 테스트.
- `tests/test_excavator_vision_contract.py`: 실제 RuntimeState·Flask API와의
  호환성 테스트. Vision venv 사용, 카메라·추론·BLE는 실행하지 않는다.

브리지 내부에는 asyncio BLE 작업자와 Vision 조회 작업자가 있고, HTTP
요청은 최대 1개 스레드의 별도 작업자에서 실행한다. 상태 HTTP 서버도 별도
스레드다. Vision 프로세스의 모델·CUDA·카메라·UI 작업자를 공유하지 않는다.
기본 조회 간격은 1초이고 HTTP 요청별 timeout은 2초다. BLE 검색·연결·GATT
작업은 기본 8초 제한, 재접속 간격은 3초다. 제어 지연의 실시간 상한을
보장하는 구조는 아니며, 실제 현장 지연은 별도로 측정해야 한다.

브리지는 현재 래치가 유지되는 에피소드만 처리한다. 이벤트가 조회되면
`hazard_latched`를 식별하고, 시작·누락·재동기화 때는 현재 상태로 보완한다.
이미 관리자 RESET으로 종료된 과거 위험은 재생하지 않는다. 연결이 안 된
동안 현재 위험은 pending으로 표시하며, 연결 후 새로운 상태 조회에서도
그 위험이 유지되는 경우에만 전송한다. 오래된 캐시로 전송하지 않는다.

## 중복 방지와 실패 처리

SQLite 기본 경로는 `runs/excavator_bridge/commands.sqlite3`다.
키는 `(장치 MAC, DRY_RUN/LIVE, Vision run_id, episode_id)`다.
전송 시도 전에 `ATTEMPTING`을 FULL 동기화 모드로 commit한다.

| 기록 결과 | 의미 | 자동 재전송 |
| --- | --- | --- |
| `DRY_RUN` | 모의 명령 기록. BLE 제어 쓰기 없음 | 없음 |
| `ATTEMPTING` | 시도 예약. 프로세스가 중단됐다면 실제 결과 불명 | 없음 |
| `SENT` | `write_gatt_char(..., response=True)` 호출 완료 | 없음 |
| `UNKNOWN` | timeout, 취소, 예외로 전달 결과 불명 | 없음 |

전달 보장보다 중복 시도 방지를 택했다. 시도 기록 직후 송신 전에 죽으면
명령이 전달되지 않았을 수 있고, timeout이어도 장치가 이미 수신했을 수 있다.
이 경우 운영자가 실제 제한 상태와 기록을 확인해야 한다. 재연결이나 브리지
재시작으로 같은 명령을 다시 보내지 않는다. 자동 재가동/해제를 승인하지 않는다.
이 제한은 펌웨어가 `command_id` 기반 중복 제거·ACK를 지원한 뒤 개선할 수 있다.

DRY_RUN 기록은 LIVE 기록과 분리한다. DRY-RUN에서 LIVE로 명시적 전환하면
현재 래치가 즉시 전송 대상이 될 수 있다. 런타임 디렉터리와 DB를 보존해야
재시작 후에도 중복 방지가 유지된다. DB 삭제·교체·다른 runtime-dir 사용 시
이 보장은 이어지지 않는다. 같은 장치 브리지/프로브의 동시 실행은 프로젝트의
`.locks/excavator-44b1765fbf62.lock`으로 차단한다. 원본 수동 프로그램은 이 잠금을
알지 못하므로 동시 실행하지 않는다. 다른 체크아웃에서도 병행 실행하지 않는다.

## 상태와 응답의 의미

독립 조회 주소는 기본 `http://127.0.0.1:5011`이다.

- `GET /api/excavator/status`: 전체 상태와 최근 명령 100개
- `GET /api/excavator/history`: 최근 명령 100개
- 같은 전체 상태를 `runs/excavator_bridge/status.json`에 원자적 교체로 기록
- 전체 명령 이력은 SQLite에 보존. HTTP 이력만 100개로 제한
- 명령 실행·RESET용 HTTP 엔드포인트는 없음

| 필드 | UI 표시 기준 |
| --- | --- |
| `status` | `DISCONNECTED` / `CONNECTED` / `SENT`. SENT는 해당 연결에서 GATT 쓰기 완료만 의미 |
| `connection_state` | 현재 BLE 연결 여부. 끊기면 즉시 DISCONNECTED, 재연결하면 CONNECTED |
| `mode` | DRY_RUN / LIVE. DRY_RUN 기록을 실제 송신으로 표시하지 말 것 |
| `last_response` | 가장 최근 읽기 또는 notify의 UTF-8/hex, 수신 시각, 원본 길이 |
| `last_read`, `last_notification` | 읽기와 notify를 각각 보존 |
| `notify` | 광고 미지원 / 미구독 / 구독 실패 / `SUBSCRIBED_UNVERIFIED` |
| `last_command`, `command_history` | 에피소드·실행·모드·명령·시도 결과·오류·시간 |
| `control_application` | 항상 `UNKNOWN`. 제한 동작 피드백 미검증 |
| `ack_verified` | 항상 false. 임의의 `reset` 또는 `ACK` 문자열도 확인 응답으로 승격하지 않음 |
| `restriction_release_verified` | 항상 false. Vision RESET으로 바뀌지 않음 |
| `automatic_restart_authorized` | 항상 false |
| `vision_link`, `vision_error` | Vision API 도달 상태와 오류. 장치 안전 판정과 분리 |
| `vision`, `vision_age_seconds` | 마지막 Vision 판정과 조회 후 경과 시간 |
| `bridge_state`, `updated_at` | 브리지 실행 여부와 전체 상태 갱신 시각 |

Audio Jetson UI는 `bridge_state != RUNNING`, 조회 실패, 5초 이상 갱신 중단이면
연결 상태를 UNKNOWN/UNAVAILABLE로 표시해야 한다. 마지막 JSON의 CONNECTED나
Vision의 SAFE를 굴착기의 안전·해제 완료로 표시하지 않는다. 이력의 SENT도
실제 제한 적용 완료를 뜻하지 않는다. 종료 후 남은 status.json은 STOPPED이며,
강제 종료 시에는 갱신 시각으로 오래된 상태를 감지해야 한다.

광고된 `write` 속성에 맞게 `response=True`를 사용하고, 쓰기 직전에 실제 특성의
속성을 재확인한다. 이는 GATT 응답을 요청하는 것이며 모터·릴레이 적용 ACK가
아니다. notify를 지원하면 브리지의 BLE 관측/실제 연결 모드에서 구독하지만,
수신 데이터는 검증되지 않은 원시 응답으로만 보관한다. 구독 자체는 CCCD
디스크립터 쓰기를 포함하므로 엄격한 읽기 전용 프로브에서는 구독하지 않는다.
참고: [Bleak 3.0.2 공식 클라이언트 API](https://bleak.readthedocs.io/en/latest/api/client.html).

## 실행 명령

작업 디렉터리는 `/home/hansungelec/SAYFE_yeongjun`이다. 기존 Vision은 그대로 둔다.
아래 기본 실행은 기존 Vision의 5010 포트에 조회만 하며 BLE를 사용하지 않는다.

```bash
/home/hansungelec/venvs/sayfe_ble/bin/python -s -B excavator_bridge.py --dry-run
```

60초 후 자동 종료하는 DRY-RUN:

```bash
/home/hansungelec/venvs/sayfe_ble/bin/python -s -B excavator_bridge.py --dry-run --duration 60
```

상태 서버 바인딩 없이 파일만 내보내는 DRY-RUN:

```bash
/home/hansungelec/venvs/sayfe_ble/bin/python -s -B excavator_bridge.py --dry-run --no-status-http --duration 10
```

엄격한 실제 장치 연결·읽기 점검(브리지와 동시에 실행하지 않음):

```bash
/home/hansungelec/venvs/sayfe_ble/bin/python -s -B excavator_bridge.py --read-only-probe
```

이 모드는 검색·연결·서비스/속성 확인·읽기 후 연결을 닫는다. 보고서는
`runs/excavator_bridge/read_only_probe.json`에 저장하며 제어/notify 쓰기 경로를
호출하지 않는다. `--dry-run --observe-ble`는 읽기·notify 구독·재접속을 포함한
관측 모드이고, 제어 명령은 여전히 쓰지 않는다.

단위 테스트와 기존 API 호환성 테스트:

```bash
/home/hansungelec/venvs/sayfe_ble/bin/python -s -B -m unittest discover -s tests -p 'test_excavator_bridge.py' -v
/home/hansungelec/venvs/sayfe_vision/bin/python -s -B -m unittest discover -s tests -p 'test_excavator_vision_contract.py' -v
```

## 이번 검증 결과와 실제 제어 시험 전 확인

2026-10-31 확인한 BLE venv는 Python 3.10.12 / Bleak 3.0.2다.
새 Mock 테스트, 실제 Flask API 계약 테스트 및 기존 회귀 결과는
`docs/excavator_ble_test_report.md`를 참조한다.

이번 실행 환경에서는 로컬 TCP 소켓과 BLE/DBus 접근이
`PermissionError: [Errno 1] Operation not permitted`로 차단됐다.
실제 장치 프로브는 DISCONNECTED/FAILED이며 읽기 값은 없다. 사용자가 이전에
확인한 `reset` 읽기 성공은 이번 재검증 결과나 ACK로 사용하지 않았다.
제어 명령은 전송하지 않았다. 실제 장치 시험은 이 단계에서 중단했다.

실제 제한 시험 전에 다음을 확인한다.

1. Jetson 일반 터미널에서 읽기 전용 프로브를 실행해 MAC·서비스·특성·
   `read/write/notify` 속성·읽기 데이터를 다시 확인한다. 기존 수동 BLE 앱의
   장치 점유 여부를 확인한다. 실패했을 때 어댑터나 Vision을 자동 재시작하지 않는다.
2. 펌웨어에서 `excavator_danger` 바이트 처리와 `write` 응답 방식을 확인한다.
   `reset` 읽기나 명령 echo는 ACK로 사용하지 않는다.
3. 시험 구역·전원·비상 정지·운전자 통제 조건을 준비하고, 모터/릴레이 제한
   적용 및 제한 유지 여부를 직접 측정할 수 있도록 한다.
4. DRY-RUN에서 실제 Vision 이벤트/상태, 현재 에피소드, SQLite 중복 방지를
   확인한다. 기존 위험이 래치된 상태라면 LIVE 활성화 즉시 전송될 수 있다.
5. 실제 송신을 명시적으로 활성화한 뒤 제한 시험을 수행한다. 브리지 CLI는
   `--enable-control`과 `--confirm-command excavator_danger`를 함께 요구한다.
   이 옵션은 이번 작업에서 실행하지 않았다.
6. SENT 이후 실제 제한 동작을 확인한다. ACK를 추가하려면 펌웨어가
   장치/부팅/명령 ID·적용 결과·물리 피드백을 구분해 응답하도록 합의해야 한다.
   지금은 검증 결과를 자동으로 APPLIED로 바꾸는 경로가 없다.
7. SAFE·관리자 RESET·BLE 단절·재연결·전원 복구 뒤에 제한이 임의로 해제되거나
   모터가 자동 재가동하지 않는지 별도 확인한다. ESP32 부팅/통신 장애 시
   릴레이 기본 동작은 펌웨어·회로에서 보장해야 하며 Python만으로 보장할 수 없다.
8. 결과 불명인 동일 에피소드 재시험은 현장 상태를 확인해 별도로 결정한다.
   재송신을 유도하려고 기록 DB를 지우거나 Vision RESET을 자동 실행하지 않는다.

## 추후 두 Jetson·ESP32 두 대 통합 실행 관리자

통합 관리자는 다음 구성의 실행·종료·상태 집계를 맡으면 된다. 이번에 서비스를
등록하거나 자동 시작 설정을 변경하지 않았다.

| 구성 | 프로세스/조회 계약 | 장애 시 처리 |
| --- | --- | --- |
| Vision Jetson | 기존 sayfe_vision Python `main.py`, 5010 상태/이벤트 | 기존 카메라 잠금·Heartbeat 유지 |
| 굴착기 브리지 | sayfe_ble Python `excavator_bridge.py`, 5011 조회 또는 상태 파일 | 독립 감시. 동일 DB로 통신 작업자 복구 가능, 동일 명령 자동 재시도 없음 |
| Audio Jetson | 기존 Audio 서비스와 집계 백엔드 | Vision·BLE 상태를 별도 표시, 오래된 응답은 미확인 |
| 두 번째 ESP32 | 해당 장치 전용 어댑터/작업자 필요 | 주소·UUID·명령·ACK 정책 확인 후 추가 |

관리자는 장치별 worker, 주소, 상태 경로, 포트를 따로 두고 프로세스 argv를
명시적으로 구성한다. 두 번째 ESP32의 프로토콜은 제공되지 않았으므로 굴착기
명령이나 MAC을 복제하지 않는다. 기본 관리 설정에도 DRY-RUN을 유지하고,
LIVE 전환은 현장 시험 조건에 맞게 명시적으로 설정한다.

Audio Jetson에서 직접 조회하려면 브리지의 `--status-host <Vision-Jetson-IP>`를
명시하고 집계 백엔드가 읽게 하거나, localhost 조회를 프록시/터널로 전달한다.
UI는 같은 출처의 집계 API를 사용하면 별도 CORS 설정 없이 연결할 수 있다.
상태 API에는 명령 실행 기능이 없다.

종료 시 관리자는 브리지에 SIGTERM을 보내고 종료를 기다린다. 브리지는 상태를
STOPPED로 기록하고 BLE를 닫는다. 어떤 종료·재시작 순서에서도 `reset`을
송신하지 않는다. 전원 복구 후 장치 재가동 승인은 현장 확인과 향후 검증된
장치 피드백을 기반으로 별도로 설계해야 한다.
