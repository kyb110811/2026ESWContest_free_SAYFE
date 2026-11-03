# 영상 번호와 작업자별 판정 불일치 수정

> **개발 기록 / Previous development note:** 이 문서는 해당 날짜의 별도 개발·검증 기록이며 최종 결선 시스템 명세가 아닙니다. 최종 구조는 [메인 README](../../README.md)를 기준으로 확인하십시오.

수정 범위: SAYFE_yeongjun. 실행 중인 비전·오디오 서버는 재시작하지 않았다.

## 원인

영상과 현재 카메라 관측은 이미 카메라별로 person1부터 압축했다.
그러나 `risk.py`의 결합은 이전 공통 내부 `track_id`로 묶고 표의 번호를 별도로 만들었다.
화면에는 모두 person1이어도 내부 추적이 두 개면 표에 person1/person2 두 행이 생성됐다.

실행 `20261031T172645+0900_db4859dc`에서 실제 확인한 관측:

| 카메라 | 영상 person_id | 내부 track_id | 현재 상태 |
|---|---|---|---|
| CAM1 | person1 | person16 | DANGER |
| CAM2 | person1 | person15 | SAFE |

이 두 관측이 기존에는 UNKNOWN/SAFE와 DANGER/UNKNOWN 두 행으로 나뉘어 SITE DANGER를 만들었다.

## 수정

`risk.py`는 각 카메라의 현재 표시 매핑으로 행의 `person_id`를 정하고 같은 표시 번호의 관측을 결합한다.
영상/FrameObservation/API/작업자 표가 같은 번호를 사용한다.

| 작업자 | CAM1 | CAM2 | 결합 |
|---|---|---|---|
| person1 | DANGER | SAFE | SAFE |

현재 관측이 없는 내부 추적은 재등장 연결용 메모리로만 남기며 표에 추가 행을 만들지 않는다.
현재 관측은 있지만 UNKNOWN/UNKNOWN인 행은 기존처럼 판정 제외이며 화면에서 숨긴다.
추가 번호 표시(`person2 · DANGER`)는 되살리지 않았다.

카메라의 원본 내부 ID는 삭제하지 않는다. API의 `track_ids`와 `observations[camera].track_id`에 남긴다.
결합 행의 `track_id`는 내부 구성 키다. 양쪽 ID가 같으면 기존 ID를 사용하고, 서로 다르면
`fusion:CAM1=person16|CAM2=person15`처럼 두 ID를 기록한다.
위험 확인 횟수와 증거는 이 구성에 연결해 새 person1이 이전 사람의 확인 횟수를 이어받지 않게 한다.
증거의 `fusion_track_id`는 결합 키이며 원본 `track_id`는 카메라 추적 ID다.

카메라별 등장 순서와 남은 사람의 번호를 매기는 방식은 유지한다. 결합은 사용자가 지정한 현재 번호 기준이다.
따라서 양쪽 카메라에서 서로 다른 사람이 각각 person1이 되는 경우에도 같은 행으로 결합된다.
실제 동일인과 일치하려면 양쪽에서 같은 순서·인원으로 관측하는 운영 조건이 필요하다.
이 수정은 외형 기반 동일인 인식 모델을 추가한 작업은 아니다.

## LATCH와 RESET

현재 SITE는 수정된 결합 결과를 따른다. 기존 위험 LATCH는 자동 해제하지 않는다.
SITE SAFE가 확인된 후 관리자 확인 체크와 RESET으로 해제한다.
과거 LATCH를 표에서 행을 합쳤다는 이유만으로 지우지 않는다.

## 검증

- 사진과 같은 내부 ID 분리 재현: 양쪽 영상 person1, CAM1 DANGER/CAM2 SAFE → person1 한 행, 결합 SAFE, 새 LATCH 없음.
- 서로 다른 내부 ID를 가진 동일 표시 번호의 9가지 상태 조합 전체.
- 번호 압축 후 표/원본 관측의 번호와 상태 일치, 미관측 추적의 추가 행 제외.
- 같은 표시 번호를 새 사람에게 재사용할 때 위험 확인 횟수 분리.
- 다른 내부 ID의 DANGER/DANGER 증거 저장, 현재 SAFE에서도 LATCH 유지, 수동 RESET.
- 실제 파이프라인에서 한 카메라 DANGER/다른 카메라 SAFE는 SITE SAFE, 양쪽 DANGER에서 LATCH, 이후 SAFE에서 LATCH 유지.

전체 자동 테스트 261개 중 260개 통과. 남은 1개는 기존 Heartbeat 테스트가 현재
`config.json`의 `heartbeat.enabled=true`를 false로 기대하는 설정 불일치다.
Heartbeat 설정이나 송신 코드는 이번 작업에서 수정하지 않았다.

저장 로그 마지막 5,000개 처리 프레임 재생:

| 지표 | 결과 |
|---|---:|
| 영상 번호와 표·결합 불일치 | 0 |
| 양쪽 영상에 person1만 있던 경우 | 4,856 |
| 그중 서로 다른 내부 ID인 경우 | 4,856 |
| DANGER/SAFE 조합 → 한 행 SAFE | 2,494 |

이 검사는 저장된 관측의 번호·상태 결합 일관성을 확인한 것이며 실제 동일인 정답 정확도나 실시간 성능 측정은 아니다.
보고서: `runs/diagnostics/fusion_labels_20261031.json`.

```bash
python -s -B tools/replay_fusion.py \
  --run runs/20261031T172645+0900_db4859dc \
  --tail-frames 5000 \
  --output runs/diagnostics/fusion_labels_20261031.json
```

적용: 기존 비전 실행 터미널에서 Ctrl+C 후 프로젝트 루트의 `./run.sh`로 재시작하고 브라우저에서 Ctrl+F5.
