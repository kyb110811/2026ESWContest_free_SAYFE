# Model 구성

## 역할

SAYFE가 사용하는 model 가운데 GitHub 제출본에 포함한 Vision model과, 실행 장비에서 별도로 준비해야 하는 외부 model의 범위를 설명합니다.

## Vision model

| 항목 | 내용 |
|---|---|
| 파일 | `vision/best.pt` |
| 역할 | 사람과 굴착기 object detection |
| framework | Ultralytics YOLO / PyTorch |
| 크기 | 5,452,570 bytes (약 5.20 MiB) |
| SHA-256 | `e56c12f5319ec222124cb99072a681820e759e5e2632db41a8d36c2ed3dcd2b4` |
| runtime | `vision/run.sh`가 `vision/`의 `.engine` 또는 `.pt`를 선택하며 현재 제출본에서는 `best.pt` 사용 |

정확도, dataset 구성, 학습 수량 등 저장소에서 확인되지 않는 성능·학습 정보는 기재하지 않습니다.

## 외부 model

다음 model과 실행 자산은 크기와 배포 조건을 고려하여 저장소에 포함하지 않습니다.

- Whisper model과 whisper.cpp 실행 파일
- NLLB-200 CTranslate2 변환 model
- Piper 중국어·베트남어 voice model 및 실행 파일
- 범용 YOLO pretrained weight

각 장비의 실행 환경에서 별도로 준비해야 하며, 외부 구성요소의 역할은 [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)를 참고하십시오.
