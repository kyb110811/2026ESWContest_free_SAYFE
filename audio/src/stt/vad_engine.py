from __future__ import annotations

import subprocess
import time
import wave
from collections import deque
from pathlib import Path

import numpy as np
import torch
from silero_vad import load_silero_vad, VADIterator


SAMPLE_RATE = 16000
CHUNK_SAMPLES = 512
THRESHOLD = 0.35
MIN_SPEECH_MS = 600
END_SILENCE_MS = 900
PRE_ROLL_MS = 400

CAPTURE_DEVICE = "plughw:CARD=Device,DEV=0"

OUTPUT_DIR = Path("vad_test")
OUTPUT_DIR.mkdir(exist_ok=True)


def validate_capture_device() -> str:
  ) instead of using a numeric ``hw:N,M`` address.
    """
    result = subprocess.run(
        ["arecord", "-l"],
        capture_output=True,
        text=True,
        check=False,
    )

    cards = result.stdout + result.stderr

    if result.returncode != 0 or "card " not in cards:
        raise RuntimeError(
            "ALSA 입력 장치를 찾을 수 없습니다. "
            f"필요한 관리자 USB 마이크: {CAPTURE_DEVICE}\n"
            f"arecord -l:\n{cards.strip()}"
        )

   
    if not any(
        line.lstrip().startswith("card ")
        and ": Device [" in line
        for line in cards.splitlines()
    ):
        raise RuntimeError(
            "관리자 USB 마이크(CARD=Device)를 찾을 수 없습니다. "
            f"현재 입력 설정: {CAPTURE_DEVICE}\n"
            f"arecord -l:\n{cards.strip()}"
        )

    return CAPTURE_DEVICE


def save_wav(path: Path, frames: list[bytes]) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"".join(frames))


def record_one_utterance() -> Path:
    torch.set_num_threads(1)

    model = load_silero_vad(onnx=False)

    vad = VADIterator(
        model,
        threshold=THRESHOLD,
        sampling_rate=SAMPLE_RATE,
        min_silence_duration_ms=END_SILENCE_MS,
        speech_pad_ms=0,
    )

    chunk_ms = CHUNK_SAMPLES * 1000.0 / SAMPLE_RATE
    pre_roll_chunks = max(1, round(PRE_ROLL_MS / chunk_ms))

    pre_roll = deque(maxlen=pre_roll_chunks)

    recorded_frames = []
    triggered = False
    speech_ms = 0.0

    cmd = [
        "arecord",
        "-D", CAPTURE_DEVICE,
        "-f", "S16_LE",
        "-r", str(SAMPLE_RATE),
        "-c", "1",
        "-t", "raw",
        "-q",
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )

    if process.stdout is None:
        raise RuntimeError("마이크 스트림을 열 수 없습니다.")

    print("========================================")
    print("Silero VAD 마이크 테스트")
    print("한 문장을 말하고 잠시 침묵하세요.")
    print("========================================")

    bytes_per_chunk = CHUNK_SAMPLES * 2

    try:
        while True:
            raw = process.stdout.read(bytes_per_chunk)

            if not raw:
                
                if process.poll() is not None:
                    detail = ""
                    if process.stderr is not None:
                        try:
                            detail = process.stderr.read().decode(
                                "utf-8",
                                errors="replace",
                            ).strip()
                        except Exception:
                            detail = ""

                    raise RuntimeError(
                        f"마이크 입력 프로세스가 종료되었습니다. "
                        f"returncode={process.returncode}\n"
                        f"arecord stderr: {detail}"
                    )

                time.sleep(0.02)
                continue

            if len(raw) != bytes_per_chunk:
                continue

            audio_np = np.frombuffer(
                raw,
                dtype=np.int16,
            ).astype(np.float32) / 32768.0

            audio_tensor = torch.from_numpy(audio_np)

            event = vad(audio_tensor)

            if not triggered:
                pre_roll.append(raw)

            if event and "start" in event and not triggered:
                print("VOICE START")

                triggered = True
                recorded_frames = list(pre_roll)
                recorded_frames.append(raw)
                speech_ms = chunk_ms
                continue

            if triggered:
                recorded_frames.append(raw)
                speech_ms += chunk_ms

                if event and "end" in event:
                    print("VOICE END")

                    if speech_ms < MIN_SPEECH_MS:
                        raise RuntimeError(
                            f"발화가 너무 짧습니다: {speech_ms:.0f} ms"
                        )

                
                    pcm = b"".join(recorded_frames)
                    pcm_np = np.frombuffer(
                        pcm,
                        dtype=np.int16,
                    ).astype(np.float32)

                    rms = float(
                        np.sqrt(
                            np.mean(
                                pcm_np * pcm_np
                            )
                        )
                    )
                    peak = float(
                        np.max(
                            np.abs(pcm_np)
                        )
                    )

                    print(
                        f"Audio level: RMS={rms:.0f}, "
                        f"PEAK={peak:.0f}"
                    )

                   
                    if rms < 250 or peak < 1200:
                        print(
                            "LOW ENERGY INPUT - DROP"
                        )

                        vad.reset_states()
                        triggered = False
                        recorded_frames = []
                        speech_ms = 0.0
                        pre_roll.clear()

                        continue

                    filename = (
                        "utterance_"
                        + time.strftime("%Y%m%d_%H%M%S")
                        + ".wav"
                    )

                    output = OUTPUT_DIR / filename
                    save_wav(output, recorded_frames)

                    print(f"Saved: {output}")
                    print(f"Speech: {speech_ms:.0f} ms")

                    return output

    finally:
        if process.poll() is None:
            process.terminate()

        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    record_one_utterance()
