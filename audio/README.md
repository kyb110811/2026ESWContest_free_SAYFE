# Audio 모듈

최종 결선 Audio 구조는 [메인 README](../README.md)를 기준으로 합니다. Audio Jetson은 관리자 한국어 음성을 처리하고 Vision·Gas 위험 이벤트의 다국어 경고를 송출합니다.

## Safe Path

```text
관리자 한국어 PTT → Silero VAD → Whisper STT → 현장용어·은어 보정
→ 기준문장 Mapping / NLLB-200 번역 → Safety Guard / Fallback
→ Piper TTS → 언어별 Audio 출력
```

한국어는 Sennheiser BTD700, 중국어·베트남어는 nRF5340 Audio DK의 Auracast 경로를 사용합니다.

## Fast Path

```text
Vision / Gas DANGER 이벤트 → 일반 방송 선점
→ 사전 검수된 한국어·중국어·베트남어 경고 음원 우선 송출
```

Vision Jetson의 위험 이벤트는 **유선 LAN**으로 전달됩니다. Gas ESP32-C3는 자체 위험 판단과 현장 장치 제어 후 BLE로 위험 상태를 전달합니다. Jetson 간 Bluetooth RFCOMM 수신과 Audio Jetson의 센서값 단독 위험 판단은 이전 개발 단계의 설명입니다.

## 실행

메인 README에 기재된 Audio 진입점은 `audio/run_ui_demo.sh`입니다. 장치별 실행 환경과 설정값은 [메인 README의 실행 방법](../README.md#24-실행-방법)을 따릅니다.

관련 코드와 자산은 `scripts/`, `src/`, `assets/fast_path/`에 있습니다.
