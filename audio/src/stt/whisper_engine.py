from __future__ import annotations

import http.client
import json
import os
import re
import wave
import socket
import subprocess
import time
import uuid
from pathlib import Path


PROJECT_DIR = Path(
    os.getenv(
        "SAYFE_PROJECT_ROOT",
        str(Path(__file__).resolve().parents[2]),
    )
).resolve()

WHISPER_SERVER_EXE = Path(
    os.getenv(
        "CONSTRUCTION_SAFETY_WHISPER_SERVER",
        "whisper-server",
    )
)

WHISPER_MODEL = Path(
    os.getenv(
        "CONSTRUCTION_SAFETY_WHISPER_MODEL",
        str(PROJECT_DIR / "models" / "ggml-small.bin"),
    )
)

WHISPER_LANGUAGE = "ko"

WHISPER_THREADS = int(
    os.getenv(
        "CONSTRUCTION_SAFETY_WHISPER_THREADS",
        "4",
    )
)

WHISPER_HOST = os.getenv(
    "CONSTRUCTION_SAFETY_WHISPER_HOST",
    "127.0.0.1",
)

WHISPER_PORT = int(
    os.getenv(
        "CONSTRUCTION_SAFETY_WHISPER_PORT",
        "8080",
    )
)

WHISPER_TIMEOUT = float(
    os.getenv(
        "CONSTRUCTION_SAFETY_WHISPER_TIMEOUT",
        "60",
    )
)

_whisper_process: subprocess.Popen | None = None


# =========================================================
# Whisper hallucination guard
# BridgeCast 최종본의 필터 구조를 건설안전용으로 이식
# =========================================================

HALLUCINATION_EXACT = {
    "[끝]",
    "(끝)",
    "<끝>",
    "[감사합니다]",
    "(감사합니다)",
}


def _audio_duration_seconds(
    wav_path: Path,
) -> float:
    try:
        with wave.open(str(wav_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()

        if rate <= 0:
            return 0.0

        return frames / float(rate)

    except Exception:
        return 0.0


def _compact_korean(
    text: str,
) -> str:
    return re.sub(
        r"[^가-힣A-Za-z0-9]+",
        "",
        text,
    )


def is_hallucination_text(
    text: str,
) -> bool:
    """
    Whisper가 무음/잡음을 실제 발화처럼 생성한
    명백한 메타성 결과를 제거한다.
    """

    normalized = " ".join(
        text.strip().split()
    )

    if not normalized:
        return True

    if normalized in HALLUCINATION_EXACT:
        return True

    # 짧은 괄호/대괄호 메타성 출력
    # 예: (끝), [구독&좋아요]
    if re.fullmatch(
        r"[\[\(<].{0,20}[\]\)>]",
        normalized,
    ):
        return True

    return False


def is_low_value_short_transcript(
    text: str,
    duration_seconds: float,
) -> bool:
    """
    BridgeCast의 short transcript guard를
    건설안전 키워드에 맞춰 적용한다.

    2초 미만 입력은 더 엄격하게 검사하되,
    실제 안전 핵심어가 있으면 유지한다.
    """

    if duration_seconds >= 2.0:
        return False

    normalized = text.strip()

    if not normalized:
        return True

    important = (
        "가스",
        "산소",
        "환기",
        "후앙",
        "위험",
        "안전",
        "작업",
        "중단",
        "대피",
        "굴착기",
        "장비",
        "정지",
        "전원",
        "화재",
        "용접",
        "곰방",
        "가베",
        "공구리",
        "단도리",
        "와꾸",
        "바라시",
        "아시바",
        "하이바",
        "나라시",
        "노리비끼",
    )

    if any(
        keyword in normalized
        for keyword in important
    ):
        return False

    # BridgeCast와 동일하게 짧고 정보량이 낮은
    # 비안전 발화 후보를 제거
    if len(
        _compact_korean(normalized)
    ) <= 12:
        return True

    return False



def validate_environment() -> None:
    if not WHISPER_SERVER_EXE.exists():
        raise FileNotFoundError(
            f"whisper-server가 없습니다: {WHISPER_SERVER_EXE}"
        )

    if not WHISPER_MODEL.exists():
        raise FileNotFoundError(
            f"Whisper 모델이 없습니다: {WHISPER_MODEL}"
        )


def _server_is_ready() -> bool:
    try:
        sock = socket.create_connection(
            (WHISPER_HOST, WHISPER_PORT),
            timeout=1.0,
        )
        sock.close()
        return True
    except Exception:
        return False


def start_whisper_server() -> None:
    global _whisper_process

    validate_environment()

    if (
        _whisper_process is not None
        and _whisper_process.poll() is None
    ):
        return

    cmd = [
        str(WHISPER_SERVER_EXE),
        "-m",
        str(WHISPER_MODEL),
        "-l",
        WHISPER_LANGUAGE,
        "-t",
        str(WHISPER_THREADS),
        "-bs",
        "5",
        "-bo",
        "5",
        "-fa",
        "--host",
        WHISPER_HOST,
        "--port",
        str(WHISPER_PORT),
    ]

    print("========================================")
    print("Whisper STT Engine")
    print("========================================")
    print(f"Server : {WHISPER_SERVER_EXE}")
    print(f"Model  : {WHISPER_MODEL}")
    print(f"Host   : {WHISPER_HOST}:{WHISPER_PORT}")

    _whisper_process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    deadline = time.time() + 45.0

    while time.time() < deadline:
        if _whisper_process.poll() is not None:
            detail = ""

            if _whisper_process.stderr is not None:
                detail = _whisper_process.stderr.read()

            raise RuntimeError(
                "whisper-server 시작 실패\n"
                + detail
            )

        if _server_is_ready():
            print("Whisper server : READY")
            print("========================================")
            return

        time.sleep(0.25)

    stop_whisper_server()

    raise TimeoutError(
        "whisper-server 시작 시간 초과"
    )


def stop_whisper_server() -> None:
    global _whisper_process

    process = _whisper_process
    _whisper_process = None

    if process is None:
        return

    try:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _multipart_body(
    wav_path: Path,
) -> tuple[bytes, str]:

    boundary = (
        f"----ConstructionSafety"
        f"{uuid.uuid4().hex}"
    )

    wav_bytes = wav_path.read_bytes()

    parts: list[bytes] = []

    def add_field(
        name: str,
        value: str,
    ) -> None:

        parts.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; '
                    f'name="{name}"\r\n\r\n'
                ).encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )

    parts.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; '
                f'name="file"; '
                f'filename="{wav_path.name}"\r\n'
            ).encode(),
            b"Content-Type: audio/wav\r\n\r\n",
            wav_bytes,
            b"\r\n",
        ]
    )

    add_field("temperature", "0.0")
    add_field("response_format", "json")
    add_field("language", "ko")
    add_field("translate", "false")

    # 건설현장 안전관리 도메인 initial prompt
    # 전체 평가문장을 넣지 않고 핵심 용어만 제공한다.
    add_field(
        "prompt",
        (
            "건설현장 안전관리 음성입니다. "
            "작업자, 중장비, 위험구역, 굴착기, 지게차, "
            "유해가스, 가스 누출, 산소 농도, 환기, 후앙, "
            "안전모, 안전대, 안전난간, 대피, 정지, 차단, "
            "곰방, 가베, 공구리, 와꾸, 단도리, 나라시, "
            "노리비끼, 바라시, 아시바, 하이바 등의 "
            "건설안전 및 현장용어가 포함될 수 있습니다."
        ),
    )
    add_field("carry_initial_prompt", "true")

    parts.append(
        f"--{boundary}--\r\n".encode()
    )

    return b"".join(parts), boundary


def transcribe_audio(
    audio_path: str | Path,
) -> str:

    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(
            f"STT 입력 WAV가 없습니다: {audio_path}"
        )

    if (
        _whisper_process is None
        or _whisper_process.poll() is not None
    ):
        start_whisper_server()

    body, boundary = _multipart_body(
        audio_path
    )

    conn = http.client.HTTPConnection(
        WHISPER_HOST,
        WHISPER_PORT,
        timeout=WHISPER_TIMEOUT,
    )

    try:
        conn.request(
            "POST",
            "/inference",
            body=body,
            headers={
                "Content-Type":
                    f"multipart/form-data; "
                    f"boundary={boundary}",
                "Content-Length":
                    str(len(body)),
            },
        )

        response = conn.getresponse()

        raw = response.read().decode(
            "utf-8",
            errors="replace",
        )

        if not (
            200 <= response.status < 300
        ):
            raise RuntimeError(
                f"Whisper STT 실패 "
                f"(HTTP {response.status})\n"
                f"{raw}"
            )

    finally:
        conn.close()

    payload = json.loads(raw)

    if isinstance(payload, dict):
        text = str(
            payload.get("text")
            or payload.get("transcription")
            or payload.get("transcript")
            or ""
        ).strip()
    else:
        text = ""

    if not text:
        return ""

    duration_seconds = _audio_duration_seconds(
        audio_path
    )

    if is_hallucination_text(text):
        print(
            "[STT GUARD] Hallucination DROP:",
            repr(text),
        )
        return ""

    if is_low_value_short_transcript(
        text,
        duration_seconds,
    ):
        print(
            "[STT GUARD] Short/low-value DROP:",
            repr(text),
            f"duration={duration_seconds:.3f}s",
        )
        return ""

    return text
