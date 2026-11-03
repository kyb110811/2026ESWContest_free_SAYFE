# 관리자 RESET 안전 복구 기록 (2026-10-31)

> **개발 기록 / Previous development note:** 이 문서는 해당 날짜의 별도 개발·검증 기록이며 최종 결선 시스템 명세가 아닙니다. 최종 구조는 [메인 README](../../README.md)를 기준으로 확인하십시오.

## 버전 확인

실행 기록 `runs/20261031T194129+0900_36621557/metadata.json`의 네 파일 SHA-256은 수정 전 파일과 모두 같았다.
`main.py` `6dbdca9d`, `state.py` `9b6a93c3`, `risk.py` `578fde66`, `ble_excavator.py` `98134a60`.
현재 접근 가능한 프로세스 목록에는 Vision Python 프로세스가 없어, 이 기록이 실제 실행 중인 프로세스의 로드 코드인지 확인할 수 없었다.
기록의 `run_status=running`은 프로세스 생존 증거가 아니다. 프로세스는 종료하거나 재시작하지 않았다.

## 적용 전 상태

원본은 `backups/admin_reset_safe_20261031_1951/`에 보관했다.
관리자 RESET은 현재 episode, CAM1·CAM2 최신 유효 관측과 YOLO 정상 상태,
두 카메라의 위험영역 관측, 모든 검출 인원 이탈 및 연속 3초 안전,
관리자 토큰, BLE Heartbeat ONLINE을 요구한다.
요청 후에도 BLE 쓰기 직전과 직후에 안전을 재검사한다.
새 DANGER, Heartbeat 상실, BLE 쓰기 실패는 RESET을 중단하고 DANGER를 다시 주장한다.
BLE 재연결만으로 RESET을 재전송하지 않는다.

`admin_reset_requested`, `admin_reset_validation`, `admin_reset_transmission`,
`admin_reset_ack`, `admin_reset_release_result`가 단계별 결과를 기록한다.
GATT 쓰기 완료는 ESP32 명령 ACK나 실제 제한 해제 증거가 아니다.
펌웨어 ACK와 실제 제한 해제 상태 피드백이 없어 전체 해제 성공은 확인할 수 없다.

## 실제 장치에 적용할 때

1. 현재 실행 인스턴스와 독립 브리지의 실행 상태 및 코드 버전을 운영 환경에서 확인한다.
2. 독립 브리지 LIVE 제어를 비활성화하고 공통 장치 잠금 파일이 단일 제어자를 보장하는지 확인한다.
3. 승인된 정비 시간에 새 코드를 적용한다. 실행 중인 프로세스에 파일 변경이 자동 반영된다고 가정하지 않는다.
4. 별도 승인 후 실제 ESP32에서 GATT write-with-response, ACK 프로토콜, 제한 해제 상태 피드백,
   위험 재진입 및 Heartbeat 중단 시 동작을 순서대로 검증한다.

이 작업에서는 실제 API 호출, ESP32 제어 명령 전송, 장치 시험을 하지 않았다.
