from __future__ import annotations

import audioop
import queue
import subprocess
import threading
import wave
from pathlib import Path


DEVICE = "plughw:CARD=B700,DEV=0"

TARGET_RATE = 48000
CHANNELS = 2
SAMPLE_WIDTH = 2

CHUNK_MS = 10

FRAMES_PER_CHUNK = (
    TARGET_RATE * CHUNK_MS // 1000
)

CHUNK_BYTES = (
    FRAMES_PER_CHUNK
    * CHANNELS
    * SAMPLE_WIDTH
)

SILENCE = b"\x00" * CHUNK_BYTES


class KoreanAuracastPlayback:
   

    def __init__(
        self,
        device: str = DEVICE,
        max_queue_seconds: float = 30.0,
    ):
        max_chunks = int(
            max_queue_seconds * 1000 / CHUNK_MS
        )

        self._queue: queue.Queue[bytes] = (
            queue.Queue(maxsize=max_chunks)
        )

        self._stopping = threading.Event()

        self._process = subprocess.Popen(
            [
                "aplay",
                "-q",
                "-D",
                device,
                "-t",
                "raw",
                "-f",
                "S16_LE",
                "-r",
                str(TARGET_RATE),
                "-c",
                str(CHANNELS),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        if self._process.stdin is None:
            raise RuntimeError(
                "BTD 700 aplay stdin unavailable"
            )

        self._thread = threading.Thread(
            target=self._consume,
            name="korean-auracast-playback",
            daemon=True,
        )

        self._thread.start()

        print(
            "[KO AURACAST] BTD 700 READY "
            f"device={device}",
            flush=True,
        )

    def enqueue_wav(
        self,
        wav_path: Path,
    ) -> int:

        wav_path = Path(wav_path)

        with wave.open(
            str(wav_path),
            "rb",
        ) as wf:
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()
            raw = wf.readframes(
                wf.getnframes()
            )

      
        if width != SAMPLE_WIDTH:
            raw = audioop.lin2lin(
                raw,
                width,
                SAMPLE_WIDTH,
            )

        if channels == 2:
            raw = audioop.tomono(
                raw,
                SAMPLE_WIDTH,
                0.5,
                0.5,
            )

        elif channels != 1:
            raise RuntimeError(
                "KO WAV는 mono 또는 stereo만 지원: "
                f"{channels} channels"
            )

        if rate != TARGET_RATE:
            raw, _ = audioop.ratecv(
                raw,
                SAMPLE_WIDTH,
                1,
                rate,
                TARGET_RATE,
                None,
            )

        raw = audioop.tostereo(
            raw,
            SAMPLE_WIDTH,
            1.0,
            1.0,
        )

    
        chunks = []

        for offset in range(
            0,
            len(raw),
            CHUNK_BYTES,
        ):
            chunk = raw[
                offset:
                offset + CHUNK_BYTES
            ]

            if len(chunk) < CHUNK_BYTES:
                chunk += (
                    b"\x00"
                    * (CHUNK_BYTES - len(chunk))
                )

            chunks.append(chunk)

        if (
            self._queue.qsize()
            + len(chunks)
            > self._queue.maxsize
        ):
            raise RuntimeError(
                "KO Auracast PCM queue full"
            )

        for chunk in chunks:
            self._queue.put_nowait(chunk)

        print(
            "[KO AURACAST] "
            f"QUEUED {wav_path.name} "
            f"chunks={len(chunks)}",
            flush=True,
        )

        return len(chunks)

    def pending_chunks(self) -> int:
        return self._queue.qsize()

    def stop(self):
        self._stopping.set()

        self._thread.join(
            timeout=2.0,
        )

        try:
            if self._process.stdin:
                self._process.stdin.close()
        except Exception:
            pass

        if self._process.poll() is None:
            self._process.terminate()

            try:
                self._process.wait(
                    timeout=1.0
                )
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()

        print(
            "[KO AURACAST] STOPPED",
            flush=True,
        )

    def _consume(self):
        stdin = self._process.stdin

        if stdin is None:
            return

        while not self._stopping.is_set():

            try:
                chunk = self._queue.get(
                    timeout=CHUNK_MS / 1000.0
                )

            except queue.Empty:
             
                chunk = SILENCE

            try:
                stdin.write(chunk)
                stdin.flush()

            except (
                BrokenPipeError,
                OSError,
            ):
                break


_shared_playback = None
_shared_lock = threading.Lock()


def get_korean_auracast_playback():
    global _shared_playback

    with _shared_lock:
        if _shared_playback is None:
            _shared_playback = (
                KoreanAuracastPlayback()
            )

        return _shared_playback


def stop_korean_auracast_playback():
    global _shared_playback

    with _shared_lock:
        if _shared_playback is not None:
            _shared_playback.stop()
            _shared_playback = None
