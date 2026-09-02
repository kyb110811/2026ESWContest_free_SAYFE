# 실행 흐름

## 1. Audio

```text
run_ui_demo.sh
├─ scripts/setup_auracast_zh_vi.py
│  └─ serial /dev/ttyACM0 → nRF5340 ZH/VI 방송 설정
└─ src/ui/safety_web.py → Flask UI
   └─ scripts/ui_mic_controller.py
      ├─ src/stt/vad_engine.py → Microphone + Silero VAD
      ├─ src/audio/korean_auracast_output.py → BTD700 한국어 출력
      └─ scripts/ui_gpu_worker.py
         ├─ src/stt/whisper_engine.py → whisper-server
         ├─ src/safety/normalizer.py + construction_rules.py
         ├─ src/translation/verified_site_translations.py
         ├─ src/translation/nllb_engine.py
         ├─ src/translation/safety_guard.py + safety_fallback.py
         ├─ Piper → 중국어·베트남어 TTS
         ├─ src/audio/auracast_output.py → ZH/VI PCM
         ├─ src/events/bluetooth_event_listener.py → Vision Fast Path
         ├─ src/sensors/esp32_ble_receiver.py → GAS_DANGER
         └─ src/safety/fast_path.py → assets/fast_path/{ko,zh,vi}
```

Audio worker는 시작 시 STT/TTS pipeline warm-up을 위해 `audio/data/old_test_audio/stt_test.wav`를 사용합니다.

## 2. Vision

```text
run.sh → best.pt 선택 → web_main.py
├─ detector.py → Ultralytics YOLO
├─ proximity.py → 작업자-굴착기 근접 판단
├─ motion_detector.py → 굴착기 Pixel Motion
├─ event_logic.py → Danger 판단과 latch
└─ event_sender.py
   ├─ Bluetooth RFCOMM → Audio Fast Path
   └─ HTTP POST 127.0.0.1:8765/event
      → integration/pi_rfcomm_bridge_server.py
      → /dev/rfcomm0 → Raspberry Pi
```

## 3. Raspberry Pi

```text
excavator_control.py
├─ Bluetooth RFCOMM channel 1
├─ newline-delimited JSON decoder
├─ WORKER_NEAR_MOVING_EXCAVATOR event mapping
└─ RPi.GPIO → BCM 2, 3, 4, 14
```

## 4. 장비 시작 순서

1. 장비별 Python 환경, 외부 model, Bluetooth pairing, device 권한을 준비합니다.
2. Vision Host에서 Raspberry Pi RFCOMM 연결과 `pi_rfcomm_bridge_server.py`를 시작합니다.
3. Raspberry Pi control을 시작합니다.
4. NVIDIA Jetson Orin Nano 8GB에 nRF5340 Audio DK를 연결하고 Audio를 시작합니다.
5. Vision을 시작합니다.
6. Audio/Vision UI에서 방송과 감지를 시작합니다.
