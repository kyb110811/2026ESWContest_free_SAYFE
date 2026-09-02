# 소프트웨어 구조

## Audio Safe Path와 Fast Path

```mermaid
flowchart LR
    UI[Audio Flask UI] --> MIC[ui_mic_controller.py]
    MIC --> VAD[vad_engine.py]
    MIC --> KO[korean_auracast_output.py<br/>BTD700]
    MIC --> GPU[ui_gpu_worker.py]
    GPU --> STT[whisper_engine.py]
    STT --> NORM[normalizer.py<br/>construction_rules.py]
    NORM --> MAP[verified_site_translations.py]
    MAP --> TRANS[nllb_engine.py]
    TRANS --> GUARD[safety_guard.py<br/>safety_fallback.py]
    GUARD --> TTS[Piper ZH/VI]
    TTS --> AURA[auracast_output.py<br/>nRF5340]

    VE[Vision RFCOMM Event] --> FP[fast_path.py]
    GAS[ESP32 BLE / GAS_DANGER] --> FP
    FP --> WAV[assets/fast_path/ko,zh,vi]
    FP --> KO
    FP --> AURA
```

Safe Path는 관리자 발화를 STT·정규화·번역·TTS로 처리합니다. Fast Path는 Vision/Gas event가 발생하면 Safe Path ZH/VI queue를 선점하고 사전 생성된 KO/ZH/VI WAV를 즉시 전달합니다.

## Vision과 장치 제어

```mermaid
flowchart LR
    VUI[web_main.py] --> DET[detector.py]
    DET --> PROX[proximity.py]
    PROX --> MOTION[motion_detector.py]
    MOTION --> DECIDE[event_logic.py]
    DECIDE --> SEND[event_sender.py]
    SEND -->|Bluetooth RFCOMM| AUDIO[Audio Fast Path]
    SEND -->|POST /event| BRIDGE[pi_rfcomm_bridge_server.py]
    BRIDGE -->|newline JSON /dev/rfcomm0| PI[excavator_control.py]
    PI --> GPIO[BCM GPIO 2, 3, 4, 14]
```

## 외부 실행 구성

whisper-server/Whisper model, NLLB CTranslate2 model, Piper 실행 파일과 voice model은 실행 장비에 별도로 구성합니다. `integration/pi_rfcomm_bridge_server.py`는 Vision sender와 같은 loopback network context에서 실행되어야 하며 Host의 `rfcomm` 명령과 `/dev/rfcomm0` 접근 권한이 필요합니다.
