from __future__ import annotations

import json
import math
import queue
import subprocess
import threading
import time
import wave
from pathlib import Path
from typing import Callable, Literal

import numpy as np


TARGET_RATE = 48000
NRF_DEVICE = "plughw:CARD=Audio,DEV=0"
PCM_CHUNK_MS = 20
PCM_FRAMES_PER_CHUNK = TARGET_RATE * PCM_CHUNK_MS // 1000
PCM_CHUNK_BYTES = PCM_FRAMES_PER_CHUNK * 2
SILENCE_MONO = b"\x00" * PCM_CHUNK_BYTES
Language = Literal["zh", "vi"]


def _load_mono_16bit(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())

    if width != 2:
        raise RuntimeError(f"16-bit PCM required: {path}")

    audio = np.frombuffer(frames, dtype=np.int16)
    if channels == 2:
        
        audio = audio.reshape(-1, 2).mean(axis=1).astype(np.int16)
    elif channels != 1:
        raise RuntimeError(f"Unsupported channel count: {channels}")
    return audio, rate


def _resample(audio: np.ndarray, src_rate: int) -> np.ndarray:
    if src_rate == TARGET_RATE or len(audio) == 0:
        return audio
    new_length = round(len(audio) * TARGET_RATE / src_rate)
    return np.interp(
        np.linspace(0, len(audio) - 1, new_length),
        np.arange(len(audio)),
        audio.astype(np.float32),
    ).clip(-32768, 32767).astype(np.int16)


def wav_to_pcm_chunks(path: Path) -> list[bytes]:
    
    audio, rate = _load_mono_16bit(path)
    audio = _resample(audio, rate)
    if len(audio) == 0:
        return []
    padding = (-len(audio)) % PCM_FRAMES_PER_CHUNK
    if padding:
        audio = np.pad(audio, (0, padding))
    raw = audio.astype("<i2", copy=False).tobytes()
    return [raw[offset:offset + PCM_CHUNK_BYTES]
            for offset in range(0, len(raw), PCM_CHUNK_BYTES)]


def _piper_sample_rate(config_path: Path) -> int:
   
    with config_path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)
    try:
        return int(config["audio"]["sample_rate"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Piper sample_rate missing in {config_path}") from exc


class _StreamingResampler:
   

    def __init__(self, source_rate: int) -> None:
        if source_rate <= 0:
            raise ValueError("source_rate must be positive")
        self.source_rate = source_rate
        self._step = source_rate / TARGET_RATE
        self._samples = np.empty(0, dtype=np.int16)
        self._start = 0
        self._position = 0.0
        self._received = 0
        self._emitted = 0

    def feed(self, samples: np.ndarray) -> bytes:
        if len(samples) == 0:
            return b""
        self._received += len(samples)
        self._samples = np.concatenate((self._samples, samples.astype(np.int16, copy=False)))
        return self._emit(final=False)

    def finish(self) -> bytes:
        if self._received == 0:
            return b""
        return self._emit(final=True)

    def _emit(self, *, final: bool) -> bytes:
        target_total = round(self._received * TARGET_RATE / self.source_rate)
        if final:
            count = max(0, target_total - self._emitted)
        else:
            last_interpolable = self._start + len(self._samples) - 1
            if self._position > last_interpolable:
                return b""
            count = math.floor(
                (last_interpolable - self._position) / self._step
            ) + 1
        if count <= 0:
            return b""
        positions = self._position + np.arange(count) * self._step
        relative = positions - self._start
        output = np.interp(
            relative,
            np.arange(len(self._samples)),
            self._samples.astype(np.float32),
        ).clip(-32768, 32767).astype("<i2")
        self._position += count * self._step
        self._emitted += count
        retain_from = max(self._start, int(self._position) - 1)
        drop = retain_from - self._start
        if drop:
            self._samples = self._samples[drop:]
            self._start = retain_from
        return output.tobytes()


class AuracastPlaybackQueue:
 
    def __init__(
        self,
        *,
        device: str = NRF_DEVICE,
        max_queue_seconds: float = 30.0,
        sink: Callable[[bytes], None] | None = None,
    ) -> None:
        max_chunks = max(1, round(max_queue_seconds * 1000 / PCM_CHUNK_MS))
       
        self.zh_pcm_queue: queue.Queue[bytes] = queue.Queue(maxsize=max_chunks)
        self.vi_pcm_queue: queue.Queue[bytes] = queue.Queue(maxsize=max_chunks)
        self._device = device
        self._sink = sink
        self._condition = threading.Condition()
        self._stopping = False
        self._stop_event = threading.Event()
        self._process: subprocess.Popen[bytes] | None = None
        self._first_get = {"zh": False, "vi": False}
        self._first_write = {"zh": False, "vi": False}
        self._first_put = {"zh": False, "vi": False}

       
        self._generation = 0

        self._thread = threading.Thread(
            target=self._consume, name="auracast-pcm-playback", daemon=True
        )
        self._thread.start()

    def enqueue_wav(self, language: Language, wav_path: Path) -> int:
      
        chunks = wav_to_pcm_chunks(wav_path)
        pcm_queue = self._queue_for(language)
      
        if pcm_queue.qsize() + len(chunks) > pcm_queue.maxsize:
            raise RuntimeError(f"{language} PCM queue full; utterance not queued")
        for chunk in chunks:
            self._put_chunk(language, chunk, block=False)
        return len(chunks)

    def stream_piper(
        self,
        language: Language,
        text: str,
        *,
        piper: Path,
        model: Path,
        config: Path,
        wav_path: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[float, int]:
       
        source_rate = _piper_sample_rate(config)
        started = time.perf_counter()

        
        generation = self.current_generation()

        self._begin_utterance(language, started)
        process = subprocess.Popen(
            [str(piper), "--model", str(model), "--config", str(config),
             "--output_raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        if process.stdin is None or process.stdout is None:
            process.kill()
            raise RuntimeError(f"{language} Piper pipe unavailable")

        writer: wave.Wave_write | None = None
        if wav_path is not None:
            wav_path.parent.mkdir(parents=True, exist_ok=True)
            writer = wave.open(str(wav_path), "wb")
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(source_rate)

        try:
            process.stdin.write((text + "\n").encode("utf-8"))
            process.stdin.close()
            chunks = self.stream_raw_pcm(
                language,
                process.stdout,
                source_rate,
                writer,
                generation=generation,
            )
            stderr = process.stderr.read().decode("utf-8", errors="replace")
            if process.wait() != 0:
                raise RuntimeError(f"{language} Piper failed: {stderr.strip()}")
            return time.perf_counter() - started, chunks
        finally:
            if writer is not None:
                writer.close()
            if process.poll() is None:
                process.kill()
                process.wait()

    def stream_raw_pcm(
        self,
        language: Language,
        raw_stream: object,
        source_rate: int,
        wav_writer: wave.Wave_write | None = None,
        *,
        generation: int | None = None,
    ) -> int:
       
        resampler = _StreamingResampler(source_rate)
        pending = bytearray()
        trailing = b""
        chunks = 0
        saw_pcm = False
        while True:
            read1 = getattr(raw_stream, "read1", None)
            raw = read1(4096) if read1 is not None else raw_stream.read(4096)
            if not raw:
                break
            if not saw_pcm:
                saw_pcm = True
                self._log_timestamp(language, "FIRST_PCM")
            raw = trailing + raw
            trailing = raw[-1:] if len(raw) % 2 else b""
            raw = raw[:-1] if trailing else raw
            if not raw:
                continue
            if wav_writer is not None:
                wav_writer.writeframesraw(raw)
            pending.extend(resampler.feed(np.frombuffer(raw, dtype="<i2")))
            while len(pending) >= PCM_CHUNK_BYTES:
                chunk = bytes(
                    pending[:PCM_CHUNK_BYTES]
                )
                del pending[:PCM_CHUNK_BYTES]

               
                if (
                    generation is not None
                    and generation != self.current_generation()
                ):
                    continue

                self._put_chunk(
                    language,
                    chunk,
                )
                chunks += 1
        pending.extend(resampler.finish())
        if pending:
            pending.extend(b"\x00" * (-len(pending) % PCM_CHUNK_BYTES))
            for offset in range(
                0,
                len(pending),
                PCM_CHUNK_BYTES,
            ):
                if (
                    generation is not None
                    and generation != self.current_generation()
                ):
                    continue

                self._put_chunk(
                    language,
                    bytes(
                        pending[
                            offset:
                            offset + PCM_CHUNK_BYTES
                        ]
                    ),
                )
                chunks += 1
        return chunks

    def pending_chunks(self) -> dict[str, int]:
        return {"zh": self.zh_pcm_queue.qsize(), "vi": self.vi_pcm_queue.qsize()}

    def current_generation(self) -> int:
        with self._condition:
            return self._generation

    def preempt(self) -> int:
        
        with self._condition:
            self._generation += 1
            generation = self._generation

            cleared = {}

            for language in ("zh", "vi"):
                pcm_queue = self._queue_for(language)
                count = 0

                while True:
                    try:
                        pcm_queue.get_nowait()
                        count += 1
                    except queue.Empty:
                        break

                cleared[language] = count

                self._first_put[language] = False
                self._first_get[language] = False
                self._first_write[language] = False

            self._condition.notify_all()

        print(
            f"[AURACAST PREEMPT] generation={generation} "
            f"cleared_zh={cleared['zh']} "
            f"cleared_vi={cleared['vi']}",
            flush=True,
        )

        return generation

    def stop(self) -> None:
      
        with self._condition:
            self._stopping = True
            self._condition.notify_all()
        self._stop_event.set()
        self._close_process()
        self._thread.join(timeout=2)

    def _queue_for(self, language: Language) -> queue.Queue[bytes]:
        if language == "zh":
            return self.zh_pcm_queue
        if language == "vi":
            return self.vi_pcm_queue
        raise ValueError(f"Unsupported Auracast language: {language}")

    def _put_chunk(self, language: Language, chunk: bytes, *, block: bool = True) -> None:
        pcm_queue = self._queue_for(language)
        if block:
            while not self._stopping:
                try:
                    pcm_queue.put(chunk, timeout=0.1)
                    break
                except queue.Full:
                    continue
            else:
                raise RuntimeError("Auracast playback is stopping")
        else:
            pcm_queue.put_nowait(chunk)
        if not self._first_put[language]:
            self._first_put[language] = True
            self._log_timestamp(language, "QUEUE_FIRST_PUT")
        with self._condition:
            self._condition.notify()

    def _begin_utterance(self, language: Language, started: float) -> None:
       
        with self._condition:
            self._first_put[language] = False
            self._first_get[language] = False
            self._first_write[language] = False
        self._log_timestamp(language, "TTS_START", started)

    @staticmethod
    def _log_timestamp(language: Language, event: str, when: float | None = None) -> None:
        stamp = time.perf_counter() if when is None else when
        print(f"[AURACAST][{language.upper()}] {event}={stamp:.6f}", flush=True)

    def _take_or_silence(self, language: Language) -> bytes:
        pcm_queue = self._queue_for(language)
        try:
            chunk = pcm_queue.get_nowait()
            if not self._first_get[language]:
                self._first_get[language] = True
                self._log_timestamp(language, "QUEUE_FIRST_GET")
            return chunk
        except queue.Empty:
            return SILENCE_MONO

    def _consume(self) -> None:
        while True:
            with self._condition:
                while (not self._stopping and self.zh_pcm_queue.empty()
                       and self.vi_pcm_queue.empty()):
                    self._condition.wait()
                if self._stopping:
                    return

            
            zh = self._take_or_silence("zh")
            vi = self._take_or_silence("vi")
            stereo = np.column_stack((
                np.frombuffer(zh, dtype="<i2"),
                np.frombuffer(vi, dtype="<i2"),
            )).astype("<i2", copy=False).tobytes()
            self._write(stereo, zh != SILENCE_MONO, vi != SILENCE_MONO)
            self._stop_event.wait(PCM_CHUNK_MS / 1000)

    def _write(self, stereo: bytes, has_zh: bool, has_vi: bool) -> None:
        for language, has_pcm in (("zh", has_zh), ("vi", has_vi)):
            if has_pcm and not self._first_write[language]:
                self._first_write[language] = True
                self._log_timestamp(language, "PLAYBACK_FIRST_WRITE")
        if self._sink is not None:
            self._sink(stereo)
            return
        try:
            if self._process is None or self._process.poll() is not None:
                self._process = subprocess.Popen(
                    ["aplay", "-q", "-D", self._device, "-t", "raw",
                     "-f", "S16_LE", "-c", "2", "-r", str(TARGET_RATE), "-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    bufsize=0,
                )
            if self._process.stdin is None:
                raise RuntimeError("aplay stdin unavailable")
            self._process.stdin.write(stereo)
            self._process.stdin.flush()
        except (BrokenPipeError, OSError, RuntimeError) as exc:
            # Playback failure must not kill STT/translation or strand its worker.
            print(f"Auracast playback error: {exc}", flush=True)
            self._close_process()

    def _close_process(self) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            process.terminate()


_shared_playback: AuracastPlaybackQueue | None = None
_shared_lock = threading.Lock()


def get_auracast_playback() -> AuracastPlaybackQueue:
   
    global _shared_playback
    with _shared_lock:
        if _shared_playback is None:
            _shared_playback = AuracastPlaybackQueue()
        return _shared_playback


def stop_auracast_playback() -> None:
    global _shared_playback
    with _shared_lock:
        if _shared_playback is not None:
            _shared_playback.stop()
            _shared_playback = None


def play_zh_vi(zh_wav: Path, vi_wav: Path) -> tuple[Path, Path]:
   
    playback = get_auracast_playback()
    playback.enqueue_wav("zh", zh_wav)
    playback.enqueue_wav("vi", vi_wav)
    return zh_wav, vi_wav
