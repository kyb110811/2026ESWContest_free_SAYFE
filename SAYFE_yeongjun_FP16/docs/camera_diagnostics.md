# SAYFE STEP 2-A 카메라 입력 진단

> **개발 기록 / Previous development note:** 이 문서는 해당 날짜의 별도 개발·검증 기록이며 최종 결선 시스템 명세가 아닙니다. 최종 구조는 [메인 README](../../README.md)를 기준으로 확인하십시오.

이 도구는 1차 정상 동작 소스를 수정하지 않고 기존 MJPG 입력 조건을 계측합니다.
bbox·3×3·관제 UI·RESET·외부 장치 통신 구현은 포함하지 않습니다.

## 보호 범위

- 기존 camera.py, detector.py, pipeline.py, main.py, metrics.py, state.py, web_app.py 유지.
- config.json, 기존 YOLO 모델, sayfe_vision 및 기존 runs를 변경하지 않음.
- 카메라 위치, 노출, gain, USB 배선, 전력·클록을 변경하지 않음.
- 기존 실행과 동일하게 640×480 MJPG 30FPS를 요청. YUYV 비교는 수행하지 않음.
- 기존 프로세스의 카메라 점유가 확인되면 시작하지 않음. 외부 장치 제어 없음.
- 시험 도구가 생성한 앱·모니터 프로세스만 종료.

1차 소스·환경 백업과 기존 로그 해시 목록은 ../SAYFE_backups에 저장합니다.
백업에는 가상환경이나 대형 모델을 중복 복사하지 않고 참조 파일 해시를 기록합니다.

## 실행

호스트의 GPU·카메라 접근이 가능한 환경에서:

```bash
python -s -B \
  tools/diagnose_camera.py --duration 30 --repeats 3
```

CAM1 단독, CAM2 단독, 두 카메라 캡처 전용, 기존 YOLO·웹 포함 실행을 순서대로
각 30초씩 3회 수행합니다. 부모 제어 프로세스는 영상 디코딩이나 GPU 추론을 수행하지 않습니다.
YOLO·웹 실행은 원본 main/VisionPipeline을 사용하며 해당 프로세스 메모리 안에서만
capture_factory와 기록기를 계측용으로 주입합니다. 운영 파일은 수정하지 않습니다.

웹 포함 조건은 상태 JSON 약 2Hz와 두 MJPEG 스트림의 localhost 지속 구독을 사용합니다.
Windows 브라우저의 실제 렌더링 및 무선 네트워크 부하는 포함하지 않습니다.

## 측정 방식

- open, 각 속성 set 호출의 시작·종료와 소요시간을 이벤트에 기록.
- 각 read의 전체 경과시간과 해당 캡처 스레드의 CPU 사용시간을 기록.
- 원본 LatestFrameCamera의 최신 프레임 유지·해상도 검사·오류 동작을 그대로 사용.
- 기존 RunRecorder의 제한된 큐와 비동기 저장기를 재사용하고 capture.csv를 추가.
- 모든 조건에서 기존 ResourceMonitor의 CPU·GPU·RAM·RSS·tegrastats 원문 저장.
- 처음과 마지막에 USB 트리, V4L2 형식·제어값·전력 모드를 읽어 기록.

read_wall_ms는 장치 대기·디코딩·메모리 복사·스케줄링을 포함합니다.
read_thread_cpu_ms도 순수 JPEG 디코더 시간은 아닙니다.
read_non_cpu_ms는 두 시간의 차이이며 USB 대기시간으로 단정하지 않습니다.

## FPS 정의

전체 구간 캡처 FPS = 유효 캡처 수 / 캡처 시작부터 작업자 종료까지 실제 시간.

첫 프레임 지연 = 첫 유효 read 반환 시각 − 공통 캡처 측정 시작 시각.

활성 구간 캡처 FPS = (유효 캡처 수 − 1) / (마지막 − 첫 유효 read 반환 시각).

추론 FPS = 처리한 고유 검출 결과 수 / 전체 측정 시간.
캡처 전용 조건에서는 추론과 수집→검출을 미측정으로 표시합니다.

기존 timing.csv에는 추론한 프레임만 있습니다. 이전 실행의 활성 FPS 분석은 최종
캡처 계수와 첫 캡처 번호 1이 있을 때만 계산하고, 간격 표본이 불완전함을 표시합니다.
새 capture.csv는 read 실패를 포함해 호출마다 기록하므로 초기 지연과 간격을 직접 확인합니다.

## 결과 저장

runs/step2a_<한국시각>_<고유값>/ 아래:

- suite_metadata.json: 조건·코드 해시·반복 수·웹 부하.
- devices_before.json, devices_after.json: 읽기 전용 장치 정보.
- 조건별 .log: 원시 stdout/stderr. 단독 실행에서만 경고 발생 카메라 귀속 가능.
- results.json: 조건별 진단 결과.
- runs/<run_id>/: 기존 metadata.json, timing.csv, resources.csv, events.jsonl, summary.json.
- 각 run의 capture.csv, camera_diagnostics.json: read 계측과 진단 통계.

capture_errors=0이어도 디코더가 경고와 함께 영상을 반환할 수 있습니다.
동시 실행 콘솔의 경고를 임의로 CAM2에 배정하지 않습니다.
캡처 번호 건너뜀은 최신 프레임 처리에서 생긴 생략이며 USB·드라이버 손실 계수가 아닙니다.

이전 로그를 읽기 전용으로 분석할 때:

```bash
python -s -B \
  tools/analyze_camera_runs.py \
  runs/<기존_run_id>
```

--output은 새 파일 경로만 허용합니다. 기존 원시 실행 기록은 다시 쓰지 않습니다.

## 검증 및 범위 제한

기존 19개와 초기 지연·FPS·읽기 오류·경고 귀속·기록 확장에 대한 9개 시험을 실행합니다.
실기 원인 진단은 승인된 12회 조건 시험으로 제한합니다. 원인이 미확정이면 근거와
한계를 보고하고 STEP 2-B를 지연시키는 추가 실험을 임의로 계속하지 않습니다.

이후 계획인 통합 CCTV UI, 번역·방송 로그, 개발자 Mock 이벤트 시험, 굴착기 RESET,
GUI형 실행 구조는 유지합니다. 실제 장치 통신과 STEP 2-B 구현은 별도 승인 대상입니다.
