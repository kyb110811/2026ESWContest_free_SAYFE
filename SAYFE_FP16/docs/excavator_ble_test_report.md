# 굴착기 BLE 독립 브리지 검증 결과 — 2026-10-31

> **개발 기록 / Previous development note:** 이 문서는 해당 날짜의 별도 개발·검증 기록이며 최종 결선 시스템 명세가 아닙니다. 최종 구조는 [메인 README](../../README.md)를 기준으로 확인하십시오.

## 범위 및 송신 여부

이번 작업은 기존 구조 분석 → 백업 → 독립 모듈 구현 → 기본 DRY-RUN →
Mock 테스트 → 실제 장치 읽기 전용 프로브 순서로 진행했다.
실제 `excavator_danger`/`reset` 제어 명령은 보내지 않았다.
MockESP32에만 `excavator_danger`를 쓰고 `response=True`를 검증했다.
기존 Vision을 종료·재시작하거나 서비스·패키지·venv 설정을 바꾸지 않았다.

환경은 sayfe_ble Python 3.10.12, Bleak 3.0.2다.

## 생성 파일

- `excavator_ble.py`
- `excavator_bridge.py`
- `tests/test_excavator_bridge.py`
- `tests/test_excavator_vision_contract.py`
- `docs/excavator_ble_integration.md`
- 이 보고서

실행 산출물:

- `runs/excavator_bridge/read_only_probe.json`: 실제 프로브 실패 결과
- `runs/excavator_dry_run_check/status.json`: 실제 URL 조회를 시도한 DRY-RUN 결과
- `runs/excavator_integration_validation/test_excavator_bridge.py.txt`
- `runs/excavator_integration_validation/test_excavator_vision_contract.py.txt`
- `runs/excavator_integration_validation/summary.json`: 테스트 종료 코드와 원본 대조
- `.locks/excavator-44b1765fbf62.lock`: 브리지·프로브 중복 실행 잠금 파일

Mock 프로세스 테스트의 상태·SQLite는 임시 디렉터리에서 검증 후 정리했다.
실행을 마친 브리지 프로세스나 상태 서버를 상시 실행 상태로 남기지 않았다.

## 새 테스트

| 테스트 | 실행 수 | 통과 | 건너뜀 | 실패 |
| --- | ---: | ---: | ---: | ---: |
| `test_excavator_bridge.py` (sayfe_ble) | 32 | 31 | 1 | 0 |
| `test_excavator_vision_contract.py` (sayfe_vision) | 1 | 1 | 0 | 0 |
| 합계 | 33 | 32 | 1 | 0 |

검증한 내용:

- MAC 검색, 서비스/특성 확인, 광고된 read/write 속성 확인
- 읽기, notify 수신/구독 실패, 잘못된 UTF-8, 원시 데이터 길이 제한
- `response=True`와 쓰기 직전 속성 재확인
- DRY-RUN에서는 연결 여부와 관계없이 제어 쓰기 0회
- 연결 끊김 감지, 연결 복구, 재접속만으로 재전송하지 않음
- 같은 위험 100회 조회·이벤트/상태 중복·프로세스 재시작에도 시도 1회
- 에피소드·Vision 실행·DRY_RUN/LIVE 분리
- API 이벤트 누락 시 현재 래치 상태로 보완
- 연결 전에 위험이 해제되면 과거 명령을 재생하지 않음
- SAFE/RESET 이벤트가 제한 해제 명령이나 해제 성공 표시로 이어지지 않음
- 쓰기 timeout/실패/프로세스 중단 흔적은 결과 미확인, 자동 재시도 없음
- 기록 DB 장애 시 쓰지 않음
- 잘못된 스키마·실행 ID·이벤트 출처·순서 및 멈춘 Vision에 대해 송신하지 않음
- HTTP 실패 후 이전 pending 캐시로 송신하지 않음
- 이전 에피소드 SENT 이후 새 명령 실패 시 SENT를 새 결과로 유지하지 않음
- 경쟁 직접 연결 설정이 활성화되면 LIVE 시작/시도 차단
- 두 활성화 옵션 없이는 LIVE 불가
- 실제 HTTP 처리기의 읽기 전용 GET, POST 거부, JSON 상태 응답
- Mock HTTP 응답을 사용하는 실제 별도 DRY-RUN 프로세스의 시작·기록·종료
- 변경 전부터 존재한 RuntimeState·Flask 상태/이벤트 API와 연결 호환

실제 TCP 서버·HTTP 왕복을 수행하는 테스트 1개는 샌드박스의 소켓 생성
제한으로 건너뛰었다. 메모리 기반 HTTP 처리기와 Mock 응답 기반 프로세스
테스트는 통과했다. 이를 실제 네트워크 통합 성공으로 해석하지 않는다.

## 기존 회귀 테스트

| 테스트 | 실행 수 | 통과 | 건너뜀 | 실패 |
| --- | ---: | ---: | ---: | ---: |
| `test_admin.py` | 18 | 17 | 1 | 0 |
| `test_risk.py` | 25 | 25 | 0 | 0 |
| `test_pipeline.py` | 8 | 8 | 0 | 0 |
| `test_vision_heartbeat.py` | 26 | 25 | 0 | 1 |

관리자 테스트의 JavaScript 항목 1개는 `SAYFE_NODE` 미지정으로 건너뛰었다.
Heartbeat의 `test_disabled_defaults_and_project_settings_do_not_create_observer_or_socket`
1개는 `config.json`의 기존 `heartbeat.enabled: true`와 테스트가 요구하는
false의 불일치로 실패했다. 작업 전 백업에서도 해당 값이 true였음을 확인했다.
운영 Heartbeat 설정과 기존 테스트는 변경하지 않았다. 전체 기존 테스트 모음의
완전 통과를 주장하지 않는다.

## 실제 DRY-RUN 및 BLE 읽기 전용 결과

다음 명령은 실제 실행했고 정상 종료했다.

```bash
/home/hansungelec/venvs/sayfe_ble/bin/python -s -B excavator_bridge.py --dry-run --no-status-http --duration 3 --runtime-dir runs/excavator_dry_run_check
```

결과는 `mode=DRY_RUN`, `status=DISCONNECTED`, `bridge_state=STOPPED`,
`vision_link=UNAVAILABLE`, 명령 이력 없음이다. 샌드박스가 localhost HTTP
접속을 차단해 `URLError: ... [Errno 1] Operation not permitted`가 기록됐다.
기존 Vision의 실제 가동 여부를 이 오류로 판단할 수 없다.

다음 읽기 전용 프로브도 실제 실행했다.

```bash
/home/hansungelec/venvs/sayfe_ble/bin/python -s -B excavator_bridge.py --read-only-probe --runtime-dir runs/excavator_bridge
```

2026-10-31 18:41:55 KST 결과:

- `probe_result=FAILED`, 종료 코드 1
- `status=DISCONNECTED`, `connection_generation=0`
- `PermissionError: [Errno 1] Operation not permitted`
- `properties=[]`, `last_read=null`, `last_response=null`
- `control_writes_attempted=0`, notify 구독 없음
- `ack_verified=false`, `control_application=UNKNOWN`

장치 연결 전에 BLE/DBus 접근이 차단됐다. 사용자가 이미 성공시킨 연결·
`reset` 읽기를 이번 세션에서 재현하지 못했다. 장치 불량이나 제한 동작 실패가
확인된 것도 아니다. 일반 Jetson 터미널에서 프로브를 다시 실행해야 한다.

## 원본 보존과 병행 변경

작업 전 9개 파일을 `backups/excavator_integration_20261031_183610/`에 복사했고
`sha256.json`에 해시를 남겼다. 이번 작업은 기존 소스 파일을 편집하지 않았다.

최종 해시 대조에서 다음 파일의 **다른 경로에 의한 병행 변경**을 발견했다.

- `main.py`: 직접 연결 BLE 작업자 import/생성/시작/종료 추가
- `state.py`: DANGER 제출, `hazard_reset`에 장치 RESET 제출, 상태 필드 추가
- `ble_excavator.py`: 기존 수동 코드 대신 별도 직접 연결 작업자로 교체
- `config.json`: `excavator_ble.enabled: true`, danger/reset 메시지 설정 추가

이 경로는 관리자 RESET 시 장치 reset, 재연결 시 위험 재전송,
`response=False`를 사용하여 이번 요청의 안전 조건과 충돌한다.
현재 실행 중인 Vision에 이 변경이 실제 로드됐는지는 확인하지 않았다.
작업 중 기존 프로그램을 재시작하거나 장치에 확인 명령을 보내지 않았다.

병행 변경은 덮어쓰지 않았고,
`backups/external_ble_changes_20261031_184629/`에 추가 보존했다.
사용자에게 처리 방향을 문의했으며, 답변 전에는 직접 연결 코드를 정리하지 않는다.
신규 브리지는 경쟁 설정 활성화 시 LIVE 시작과 송신을 거부하도록 했다.

`pipeline.py`, `risk.py`, `web_app.py`, `vision_heartbeat.py`,
`excavator_ble_manual.py`는 최종 대조에서도 작업 전 백업과 SHA-256이 같다.
특히 팀원의 수동 제어 원본은 유지됐다.

전체 시스템을 독립 브리지 정책으로 통일하려면 위 병행 경로의 정리가 남아 있다.
독립 브리지 자체의 DRY-RUN과 Mock 검증은 완료했으며, 실제 제한 명령 시험
직전 단계에서 멈췄다. 현장 시험 조건과 향후 통합 실행 관리자 연결 계약은
`docs/excavator_ble_integration.md`에 정리했다.
