from __future__ import annotations

import csv
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.audio.auracast_output import (
    get_auracast_playback,
    stop_auracast_playback,
)
from src.events.bluetooth_event_listener import (
    start_bluetooth_event_listener,
)
from src.sensors.esp32_ble_receiver import (
    start_esp32_ble_gas_receiver,
)
from datetime import datetime
from pathlib import Path

from src.stt.whisper_engine import (
    start_whisper_server,
    stop_whisper_server,
    transcribe_audio,
)
from src.safety.normalizer import normalize_text
from src.safety.construction_rules import normalize_construction_korean
from src.translation.nllb_engine import (
    load_model,
    translate_dual_safe,
)

ROOT = Path(
    os.getenv(
        "SAYFE_PROJECT_ROOT",
        str(Path(__file__).resolve().parents[1]),
    )
).resolve()
OUT = ROOT / "output" / "realtime_safe_path"
TTS_ROOT = OUT / "tts"
LOG_CSV = OUT / "safe_path_log.csv"

# UI에서 선택한 언어
SELECTED_LANGUAGES = {
    lang.strip()
    for lang in os.environ.get(
        "SAYFE_LANGUAGES",
        "ko,zh,vi",
    ).split(",")
    if lang.strip() in ("ko", "zh", "vi")
}

# GPU worker가 담당하는 번역/TTS 언어
OUTPUT_LANGUAGES = tuple(
    lang
    for lang in ("zh", "vi")
    if lang in SELECTED_LANGUAGES
)

print(
    "[SAY:FE GPU] Selected languages:",
    sorted(SELECTED_LANGUAGES),
    flush=True,
)

print(
    "[SAY:FE GPU] Translation/TTS:",
    OUTPUT_LANGUAGES,
    flush=True,
)

PIPER = Path(
    os.getenv(
        "CONSTRUCTION_SAFETY_PIPER_BIN",
        "piper",
    )
)
PIPER_DIR = PIPER.parent
PIPER_MODEL_DIR = Path(
    os.getenv(
        "CONSTRUCTION_SAFETY_PIPER_MODEL_DIR",
        str(ROOT / "models" / "piper"),
    )
)

MODELS = {
    "en": (
        PIPER_MODEL_DIR / "en_US-lessac-medium.onnx",
        PIPER_MODEL_DIR / "en_US-lessac-medium.onnx.json",
    ),
    "zh": (
        PIPER_MODEL_DIR / "zh_CN-huayan-medium.onnx",
        PIPER_MODEL_DIR / "zh_CN-huayan-medium.onnx.json",
    ),
    "vi": (
        PIPER_MODEL_DIR / "vi_VN-vais1000-medium.onnx",
        PIPER_MODEL_DIR / "vi_VN-vais1000-medium.onnx.json",
    ),
}

for lang in ("zh", "vi"):
    (TTS_ROOT / lang).mkdir(parents=True, exist_ok=True)

OUT.mkdir(parents=True, exist_ok=True)

PIPER_ENV = os.environ.copy()
PIPER_ENV["LD_LIBRARY_PATH"] = (
    str(PIPER_DIR)
    + ":"
    + PIPER_ENV.get("LD_LIBRARY_PATH", "")
)

FIELDS = [
    "timestamp",
    "input_wav",
    "stt_raw",
    "stt_corrected",
    "en",
    "zh",
    "vi",
    "stt_sec",
    "translation_sec",
    "tts_wall_sec",
    "post_utterance_total_sec",
    "fallback_used",
    "all_safe",
    "en_wav",
    "zh_wav",
    "vi_wav",
    "status",
    "error",
]


def append_csv(row):
    new_file = not LOG_CSV.exists()

    with LOG_CSV.open(
        "a",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
            extrasaction="ignore",
        )

        if new_file:
            writer.writeheader()

        writer.writerow(row)


def run_one_tts(lang, text, output_path, _unused_playback=None):
    model, config = MODELS[lang]

    start = time.perf_counter()

    result = subprocess.run(
        [
            str(PIPER),
            "--model", str(model),
            "--config", str(config),
            "--output_file", str(output_path),
        ],
        input=text + "\n",
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=PIPER_ENV,
    )

    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        raise RuntimeError(
            f"{lang} Piper 실패: "
            + result.stderr.strip()
        )

    return elapsed


def run_one_tts_streaming(lang, text, output_path, playback):
    """Keep the archival WAV, while Piper raw PCM reaches Auracast immediately."""
    model, config = MODELS[lang]
    elapsed, chunks = playback.stream_piper(
        lang,
        text,
        piper=PIPER,
        model=model,
        config=config,
        wav_path=output_path,
        env=PIPER_ENV,
    )
    print(
        f"[AURACAST STREAM COMPLETE] {lang.upper()} {chunks} PCM chunks",
        flush=True,
    )
    return elapsed



def warm_up_runtime():
    """
    실제 사용자 첫 발화 전에 Whisper/NLLB/Piper를 한 번 실행하여
    cold-start 지연을 초기화 단계에서 흡수한다.
    """

    print("Runtime warm-up 시작...", flush=True)

    # -----------------------------------------------------
    # 1. Whisper warm-up
    # -----------------------------------------------------
    warmup_wav_candidates = [
        ROOT / "data" / "old_test_audio" / "stt_test.wav",
        ROOT / "vad_test" / "utterance_20260814_222842.wav",
    ]

    warmup_wav = next(
        (p for p in warmup_wav_candidates if p.exists()),
        None,
    )

    if warmup_wav is None:
        raise FileNotFoundError(
            "Whisper warm-up용 WAV를 찾을 수 없습니다."
        )

    start = time.perf_counter()
    _ = transcribe_audio(warmup_wav)
    print(
        f"  Whisper warm-up : {time.perf_counter() - start:.3f}s",
        flush=True,
    )

    # -----------------------------------------------------
    # 2. NLLB warm-up
    # -----------------------------------------------------
    start = time.perf_counter()

    warm_translation = None
    if OUTPUT_LANGUAGES:
        warm_translation = translate_dual_safe(
            "안전모를 착용하세요"
        )
        print(
            f"  NLLB warm-up    : {time.perf_counter() - start:.3f}s",
            flush=True,
        )
    else:
        print("  NLLB warm-up    : skipped (KO only)", flush=True)

    # -----------------------------------------------------
    # 3. EN/ZH/VI Piper warm-up
    # -----------------------------------------------------
    warm_dir = Path("/tmp/construction_safety_tts_warmup")
    warm_dir.mkdir(parents=True, exist_ok=True)

    warm_paths = {
        lang: warm_dir / f"warm_{lang}.wav"
        for lang in OUTPUT_LANGUAGES
    }

    start = time.perf_counter()

    if OUTPUT_LANGUAGES:
        with ThreadPoolExecutor(max_workers=len(OUTPUT_LANGUAGES)) as executor:
            futures = {
                lang: executor.submit(
                    run_one_tts,
                    lang,
                    warm_translation[lang],
                    warm_paths[lang],
                )
                for lang in OUTPUT_LANGUAGES
            }

            for future in futures.values():
                future.result()

    print(
        f"  Piper warm-up   : {time.perf_counter() - start:.3f}s",
        flush=True,
    )

    print("Runtime warm-up 완료", flush=True)


def process_wav(wav_path: Path):
    total_start = time.perf_counter()

    stem = wav_path.stem

    paths = {
        lang: TTS_ROOT / lang / f"{stem}_{lang}.wav"
        for lang in ("zh", "vi")
    }

    row = {
        "timestamp": datetime.now().isoformat(
            timespec="milliseconds"
        ),
        "input_wav": str(wav_path),
        "en_wav": "",
        "zh_wav": (
            str(paths["zh"])
            if "zh" in OUTPUT_LANGUAGES
            else ""
        ),
        "vi_wav": (
            str(paths["vi"])
            if "vi" in OUTPUT_LANGUAGES
            else ""
        ),
        "status": "error",
        "error": "",
    }

    try:
        print()
        print("=" * 70)
        print("REALTIME SAFE PATH")
        print("=" * 70)
        print("INPUT :", wav_path)

        # STT
        start = time.perf_counter()
        raw = transcribe_audio(wav_path)

        if not raw:
            stt_sec = time.perf_counter() - start

            row.update({
                "stt_raw": "",
                "stt_corrected": "",
                "stt_sec": f"{stt_sec:.3f}",
                "status": "stt_dropped",
            })

            print()
            print("[STT]")
            print("DROP      : hallucination / low-value input")
            print(f"TIME      : {stt_sec:.3f} sec")
            print()

            return "stt_dropped"
        stt_sec = time.perf_counter() - start

        stt_corrected = normalize_text(raw)

        construction_result = normalize_construction_korean(
            stt_corrected
        )
        corrected = construction_result["normalized"]

        # -------------------------------------------------
        # 현장관리자 제공 21개 검증 문장 우선 매칭
        #
        # 1순위: Whisper STT 원문
        # 2순위: 일반 정규화 문장
        # 3순위: 건설용어 교정 문장
        #
        # 매칭되면 NLLB를 건너뛰고 검증 ZH/VI를 사용한다.
        # 매칭되지 않으면 기존 NLLB + Safety Guard를 그대로 사용한다.
        # -------------------------------------------------

        from src.translation.verified_site_translations import (
            get_verified_translation,
        )

        verified = (
            get_verified_translation(raw)
            or get_verified_translation(stt_corrected)
            or get_verified_translation(corrected)
        )

        verified_used = False

        # KO-only mode is a direct BTD 700 path.
        if OUTPUT_LANGUAGES:
            if verified is not None:
                start = time.perf_counter()

                tr = {
                    "zh": verified.get("zh", ""),
                    "vi": verified.get("vi", ""),
                    "fallback_used": False,
                    "all_safe": True,
                    "verified_translation_used": True,
                }

                translation_sec = (
                    time.perf_counter() - start
                )

                verified_used = True

                print()
                print("[VERIFIED SITE TRANSLATION]")
                print("MATCHED : YES")
                print("ZH      :", tr["zh"])
                print("VI      :", tr["vi"])

            else:
                start = time.perf_counter()

                tr = translate_dual_safe(
                    corrected
                )

                translation_sec = (
                    time.perf_counter() - start
                )

                verified_used = tr.get(
                    "verified_translation_used",
                    False,
                )

        else:
            tr = {
                "zh": "",
                "vi": "",
                "fallback_used": False,
                "all_safe": True,
            }
            translation_sec = 0.0

        # ZH/VI Piper stdout is streamed to independent queues.  WAV files are
        # still saved for evaluation, but neither WAV completion nor the peer
        # language can delay first Auracast PCM.
        start = time.perf_counter()

        tts_each = {}

        if OUTPUT_LANGUAGES:
            with ThreadPoolExecutor(
                max_workers=len(OUTPUT_LANGUAGES)
            ) as executor:

                playback = get_auracast_playback()

                futures = {
                    lang: executor.submit(
                        run_one_tts_streaming,
                        lang,
                        tr[lang],
                        paths[lang],
                        playback,
                    )
                    for lang in OUTPUT_LANGUAGES
                }

                future_languages = {
                    future: lang
                    for lang, future in futures.items()
                }

                for future in as_completed(
                    future_languages
                ):
                    lang = future_languages[future]
                    tts_each[lang] = future.result()

        tts_wall = time.perf_counter() - start

        total_sec = time.perf_counter() - total_start

        row.update({
            "stt_raw": raw,
            "stt_corrected": corrected,
            "en": "",
            "zh": (
                tr["zh"]
                if "zh" in OUTPUT_LANGUAGES
                else ""
            ),
            "vi": (
                tr["vi"]
                if "vi" in OUTPUT_LANGUAGES
                else ""
            ),
            "stt_sec": f"{stt_sec:.3f}",
            "translation_sec": f"{translation_sec:.3f}",
            "tts_wall_sec": f"{tts_wall:.3f}",
            "post_utterance_total_sec": f"{total_sec:.3f}",
            "fallback_used": tr.get(
                "fallback_used"
            ),
            "all_safe": tr.get(
                "all_safe"
            ),
            "status": "ok",
        })

        print()
        print("[STT]")
        print("RAW       :", raw)
        print("CORRECTED :", corrected)
        print(f"TIME      : {stt_sec:.3f} sec")

        print()
        print("[TRANSLATION]")
        if "zh" in OUTPUT_LANGUAGES:
            print("ZH :", tr["zh"])

        if "vi" in OUTPUT_LANGUAGES:
            print("VI :", tr["vi"])
        print(f"TIME : {translation_sec:.3f} sec")

        print()
        print("[SAFETY]")
        print(
            "Fallback :",
            tr.get("fallback_used"),
        )
        print(
            "All safe :",
            tr.get("all_safe"),
        )

        print()
        print("[TTS - PARALLEL]")
        if "zh" in tts_each:
            print(
                f"ZH : {tts_each['zh']:.3f} sec"
            )

        if "vi" in tts_each:
            print(
                f"VI : {tts_each['vi']:.3f} sec"
            )
        print(
            f"WALL : {tts_wall:.3f} sec"
        )

        print()
        print(
            f"POST-UTTERANCE TOTAL : "
            f"{total_sec:.3f} sec"
        )

        print()
        if "zh" in OUTPUT_LANGUAGES:
            print("ZH WAV :", paths["zh"])

        if "vi" in OUTPUT_LANGUAGES:
            print("VI WAV :", paths["vi"])

    except Exception as exc:
        row["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

        print(
            "WORKER ERROR:",
            row["error"],
        )

    finally:
        append_csv(row)

    return row["status"]


def main():
    print("GPU Worker 초기화 중...")
    print("Whisper + NLLB preload")

    start_whisper_server()
    if OUTPUT_LANGUAGES:
        load_model()
    else:
        print("NLLB preload skipped (KO only)")

    # 실제 사용자 입력 전에 cold-start 제거
    warm_up_runtime()

    # RFCOMM recv/accept are blocking, so Vision events are received by a
    # daemon thread.  It lives in this process to share the existing Fast Path
    # Auracast singleton and its preemption generation.
    bluetooth_listener = start_bluetooth_event_listener()

    # This process inherited SAYFE_KO_FAST_PATH_FD from ui_mic_controller,
    # so gas alerts must enter Fast Path here (never through direct playback).
    def trigger_gas_fast_path(_mq):
        from src.safety.fast_path import trigger_fast_path

        trigger_fast_path("GAS_DANGER")
        print("[SAY:FE GAS] GAS_DANGER triggered", flush=True)

    gas_receiver = start_esp32_ble_gas_receiver(trigger_gas_fast_path)

    print("WORKER_READY", flush=True)

    try:
        for line in sys.stdin:
            path_text = line.strip()

            if not path_text:
                continue

            if path_text == "__QUIT__":
                break

            wav_path = Path(path_text)

            status = process_wav(wav_path)

            print(
                f"WORKER_DONE\t{status}",
                flush=True,
            )

    finally:
        if gas_receiver is not None:
            gas_receiver.stop()
        if bluetooth_listener is not None:
            bluetooth_listener.stop()
        stop_whisper_server()
        stop_auracast_playback()
        print("WORKER_STOPPED", flush=True)


if __name__ == "__main__":
    main()
