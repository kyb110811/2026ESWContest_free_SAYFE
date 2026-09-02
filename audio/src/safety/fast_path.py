from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from src.audio.auracast_output import get_auracast_playback


ROOT: Final = Path(
    os.getenv(
        "SAYFE_PROJECT_ROOT",
        str(Path(__file__).resolve().parents[2]),
    )
).resolve()
FAST_PATH_DIR: Final = ROOT / "assets" / "fast_path"

FAST_PATH_WAV_FILES: Final = {
    "WORKER_IN_EQUIPMENT_ZONE": {
        "ko": "worker_equipment_warning.wav",
        "zh": "worker_equipment_warning.wav",
        "vi": "worker_equipment_warning.wav",
    },
    "GAS_DANGER": {
        "ko": "gas_ko_warning.wav",
        "zh": "gas_zh_warning.wav",
        "vi": "gas_vi_warning.wav",
    },
}

SUPPORTED_EVENTS: Final = frozenset(FAST_PATH_WAV_FILES)


def request_korean_fast_path(wav_path: Path) -> bool:
    """Send a KO WAV request to the mic-controller-owned BTD 700 queue."""
    raw_fd = os.environ.get("SAYFE_KO_FAST_PATH_FD")
    if raw_fd is None:
        print(
            "[KO FAST PATH IPC] unavailable; KO channel is not owned "
            "by this process",
            flush=True,
        )
        return False

    try:
        fd = int(raw_fd)
        os.write(fd, (str(wav_path) + "\n").encode("utf-8"))
    except (ValueError, OSError) as error:
        print(
            "[KO FAST PATH IPC] request failed:",
            error,
            flush=True,
        )
        return False

    return True


def get_fast_path_wav_map(
    event: str,
) -> dict[str, Path]:
    """Return the pre-generated KO / ZH / VI WAV paths for an event."""

    event = event.strip().upper()

    if event not in SUPPORTED_EVENTS:
        raise ValueError(
            f"Unsupported Fast Path event: {event}"
        )

    wav_paths = {
        language: FAST_PATH_DIR / language / filename
        for language, filename in FAST_PATH_WAV_FILES[event].items()
    }

    for language, wav_path in wav_paths.items():
        if not wav_path.exists():
            raise FileNotFoundError(
                f"{language.upper()} Fast Path WAV missing: {wav_path}"
            )

    return wav_paths


def get_fast_path_wavs(
    event: str,
) -> tuple[Path, Path]:
    """
    Return pre-generated ZH / VI Fast Path WAV files
    for one structured safety event.
    """

    wav_paths = get_fast_path_wav_map(event)
    return wav_paths["zh"], wav_paths["vi"]


def trigger_fast_path(
    event: str,
) -> dict[str, object]:
    """
    Bypass STT / NLLB / realtime Piper.

    Pre-generated ZH / VI safety audio is queued immediately into the
    existing independent Auracast PCM queues.  The KO WAV path is sent by
    IPC to ui_mic_controller, which exclusively owns the BTD 700 stream.
    """

    event = event.strip().upper()

    wav_paths = get_fast_path_wav_map(event)
    ko_wav = wav_paths["ko"]
    zh_wav = wav_paths["zh"]
    vi_wav = wav_paths["vi"]

    playback = get_auracast_playback()

    # Fast Path는 현재 재생 중이거나 대기 중인
    # 일반 Safe Path 음성을 즉시 선점한다.
    generation = playback.preempt()

    zh_chunks = playback.enqueue_wav(
        "zh",
        zh_wav,
    )

    vi_chunks = playback.enqueue_wav(
        "vi",
        vi_wav,
    )

    ko_requested = request_korean_fast_path(ko_wav)

    result = {
        "event": event,
        "generation": generation,
        "ko_wav": str(ko_wav),
        "zh_wav": str(zh_wav),
        "vi_wav": str(vi_wav),
        "ko_requested": ko_requested,
        "zh_chunks": zh_chunks,
        "vi_chunks": vi_chunks,
        "pending": playback.pending_chunks(),
    }

    print("=" * 60)
    print("FAST PATH TRIGGERED")
    print("=" * 60)
    print("EVENT :", event)
    print("KO    :", ko_wav)
    print("ZH    :", zh_wav)
    print("VI    :", vi_wav)
    print("KO IPC:", "requested" if ko_requested else "unavailable")
    print("ZH PCM:", zh_chunks, "chunks")
    print("VI PCM:", vi_chunks, "chunks")
    print("QUEUE :", result["pending"])
    print("=" * 60)

    return result
