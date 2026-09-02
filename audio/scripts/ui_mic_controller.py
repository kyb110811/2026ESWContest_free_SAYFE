from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

PROJECT = Path(
    os.getenv(
        "SAYFE_PROJECT_ROOT",
        str(Path(__file__).resolve().parents[1]),
    )
).resolve()
VENV_PYTHON = Path(sys.executable)

KO_DIR = (
    PROJECT
    / "output"
    / "realtime_safe_path"
    / "ko_input"
)

KO_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

sys.path.insert(
    0,
    str(PROJECT),
)

from src.stt.vad_engine import (
    record_one_utterance,
)

from src.audio.korean_auracast_output import (
    get_korean_auracast_playback,
    stop_korean_auracast_playback,
)


def main():
    env = os.environ.copy()

    # UI에서 선택한 방송 언어
    selected_languages = {
        lang.strip()
        for lang in env.get(
            "SAYFE_LANGUAGES",
            "ko,zh,vi",
        ).split(",")
        if lang.strip()
    }

    print(
        "[SAY:FE] Selected languages:",
        sorted(selected_languages),
    )

  
    ko_playback = None

    if "ko" in selected_languages:
        ko_playback = get_korean_auracast_playback()
        print("[SAY:FE] KO channel enabled")
    else:
        print("[SAY:FE] KO channel disabled")

   
    env["TOKENIZERS_PARALLELISM"] = "false"

    env.setdefault(
        "CONSTRUCTION_SAFETY_TRANSLATION_DEVICE",
        "cuda",
    )

    env[
        "PYTHONPATH"
    ] = str(PROJECT)

 
    ko_fast_path_read_fd = None
    ko_fast_path_write_fd = None
    pass_fds = ()

    if ko_playback is not None:
        (
            ko_fast_path_read_fd,
            ko_fast_path_write_fd,
        ) = os.pipe()
        env["SAYFE_KO_FAST_PATH_FD"] = str(
            ko_fast_path_write_fd
        )
        pass_fds = (ko_fast_path_write_fd,)
    else:
        env.pop("SAYFE_KO_FAST_PATH_FD", None)

    worker = subprocess.Popen(
        [
            str(VENV_PYTHON),
            str(
                PROJECT
                / "scripts"
                / "ui_gpu_worker.py"
            ),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=str(PROJECT),
        env=env,
        pass_fds=pass_fds,
    )

    if ko_fast_path_write_fd is not None:
        os.close(ko_fast_path_write_fd)
        ko_fast_path_write_fd = None

    def consume_ko_fast_path_requests():
        if ko_fast_path_read_fd is None or ko_playback is None:
            return

        with os.fdopen(
            ko_fast_path_read_fd,
            "r",
            encoding="utf-8",
        ) as request_pipe:
            for line in request_pipe:
                if not line.strip():
                    continue
                wav_path = Path(line.strip())
                try:
                    chunks = ko_playback.enqueue_wav(wav_path)
                    print(
                        "[KO FAST PATH IPC] "
                        f"queued {wav_path.name} chunks={chunks}",
                        flush=True,
                    )
                except Exception as error:
                    print(
                        "[KO FAST PATH IPC] ERROR:",
                        error,
                        flush=True,
                    )

    ko_fast_path_thread = None
    if ko_fast_path_read_fd is not None:
        ko_fast_path_thread = threading.Thread(
            target=consume_ko_fast_path_requests,
            name="ko-fast-path-ipc",
            daemon=True,
        )
        ko_fast_path_thread.start()

    if (
        worker.stdin is None
        or worker.stdout is None
    ):
        raise RuntimeError(
            "GPU Worker 시작 실패"
        )

    # Wait until models are loaded
    while True:
        line = worker.stdout.readline()

        if not line:
            raise RuntimeError(
                "GPU Worker가 종료되었습니다."
            )

        print(line, end="")

        if "WORKER_READY" in line:
            break

    print()
    print("=" * 70)
    print("REALTIME SAFE PATH READY")
    print("한국어로 말해주세요.")
    print("Ctrl+C : 종료")
    print("=" * 70)

    utterance = 0

    try:
        while True:
            # System Python + Silero VAD
            source = record_one_utterance()

            utterance += 1

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S_%f"
            )[:-3]

            destination = (
                KO_DIR
                / f"{timestamp}_{utterance:04d}.wav"
            )

            shutil.copy2(
                source,
                destination,
            )

            print()
            print(
                "한국어 원음 저장:",
                destination,
            )

            
            if ko_playback is not None:
                try:
                    ko_chunks = ko_playback.enqueue_wav(
                        destination
                    )

                    print(
                        "[KO AURACAST] "
                        f"한국어 원음 queued "
                        f"chunks={ko_chunks}"
                    )

                except Exception as error:
                    print(
                        "[KO AURACAST] ERROR:",
                        error,
                    )

      
            worker.stdin.write(
                str(destination) + "\n"
            )

            worker.stdin.flush()

            
            while True:
                line = worker.stdout.readline()

                if not line:
                    raise RuntimeError(
                        "GPU Worker가 종료되었습니다."
                    )

                print(
                    line,
                    end="",
                )

                if line.startswith(
                    "WORKER_DONE"
                ):
                    break

            print()
            print("=" * 70)
            print("다음 발화를 기다립니다.")
            print("=" * 70)

    except KeyboardInterrupt:
        print()
        print("Ctrl+C : 종료합니다.")

    finally:
        try:
            worker.stdin.write(
                "__QUIT__\n"
            )

            worker.stdin.flush()
        except Exception:
            pass

        try:
            worker.wait(
                timeout=5
            )
        except subprocess.TimeoutExpired:
            worker.terminate()
            try:
                worker.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass

        if ko_fast_path_thread is not None:
            ko_fast_path_thread.join(timeout=1.0)

        if ko_playback is not None:
            try:
                stop_korean_auracast_playback()
            except Exception:
                pass


if __name__ == "__main__":
    main()
