from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import ctranslate2
from transformers import AutoTokenizer


# =========================================================
# 기본 설정
# =========================================================

PROJECT_DIR = Path(__file__).resolve().parents[2]

NLLB_MODEL_NAME = "facebook/nllb-200-distilled-600M"

# 모델 경로는 환경변수로 바꿀 수 있게 구성
CT2_MODEL_DIR = Path(
    os.getenv(
        "CONSTRUCTION_SAFETY_NLLB_MODEL",
        str(PROJECT_DIR / "models" / "nllb_600m_ct2_int8"),
    )
)

TRANSLATION_DEVICE = os.getenv(
    "CONSTRUCTION_SAFETY_TRANSLATION_DEVICE",
    "cpu",
).strip().lower()

SOURCE_LANGUAGE = "kor_Hang"

LANGUAGES: dict[str, dict[str, Any]] = {
    "en": {
        "name": "English",
        "nllb_code": "eng_Latn",
    },
    "zh": {
        "name": "Chinese",
        "nllb_code": "zho_Hans",
    },
    "vi": {
        "name": "Vietnamese",
        "nllb_code": "vie_Latn",
    },
}

BEAM_SIZE = 1
MAX_DECODING_LENGTH = 48


# =========================================================
# 전역 모델 객체
# 프로그램 시작 시 한 번만 로드
# =========================================================

_tokenizer = None
_translator = None


# =========================================================
# 모델 검증
# =========================================================

def validate_model() -> None:
    required_files = [
        CT2_MODEL_DIR / "model.bin",
        CT2_MODEL_DIR / "config.json",
        CT2_MODEL_DIR / "shared_vocabulary.json",
    ]

    missing = [
        path for path in required_files
        if not path.exists()
    ]

    if missing:
        message = "\n".join(str(path) for path in missing)

        raise FileNotFoundError(
            "NLLB CTranslate2 모델 파일이 없습니다.\n"
            f"{message}"
        )


# =========================================================
# 모델 로드
# =========================================================

def load_model():
    global _tokenizer
    global _translator

    if _tokenizer is not None and _translator is not None:
        return _tokenizer, _translator

    validate_model()

    print("========================================")
    print("NLLB Translation Engine")
    print("========================================")
    print(f"Model path : {CT2_MODEL_DIR}")
    print(f"Device     : {TRANSLATION_DEVICE}")

    _tokenizer = AutoTokenizer.from_pretrained(
        NLLB_MODEL_NAME,
        src_lang=SOURCE_LANGUAGE,
    )

    compute_type = (
        "int8"
        if TRANSLATION_DEVICE == "cpu"
        else "int8_float16"
    )

    _translator = ctranslate2.Translator(
        str(CT2_MODEL_DIR),
        device=TRANSLATION_DEVICE,
        device_index=0,
        compute_type=compute_type,
        inter_threads=1,
        intra_threads=4 if TRANSLATION_DEVICE == "cpu" else 2,
    )

    print(f"Compute    : {compute_type}")
    print("Model load : OK")
    print("========================================")

    return _tokenizer, _translator


# =========================================================
# 출력 디코딩
# =========================================================

def _decode_result(
    tokenizer,
    result,
    target_token: str,
) -> str:

    if not result.hypotheses:
        raise RuntimeError(
            "NLLB 번역 결과가 비어 있습니다."
        )

    output_tokens = list(
        result.hypotheses[0]
    )

    if (
        output_tokens
        and output_tokens[0] == target_token
    ):
        output_tokens = output_tokens[1:]

    output_ids = tokenizer.convert_tokens_to_ids(
        output_tokens
    )

    translated = tokenizer.decode(
        output_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    ).strip()

    if not translated:
        raise RuntimeError(
            "NLLB 디코딩 결과가 비어 있습니다."
        )

    return translated


# =========================================================
# 중국어 + 베트남어 Batch Translation
# =========================================================

def translate_dual_batch(
    korean_text: str,
) -> dict[str, Any]:

    normalized = " ".join(
        korean_text.strip().split()
    )

    if not normalized:
        raise ValueError(
            "번역할 한국어 문장이 없습니다."
        )

    tokenizer, translator = load_model()

    tokenizer.src_lang = SOURCE_LANGUAGE

    encoded = tokenizer(
        normalized,
        add_special_tokens=True,
        truncation=True,
        max_length=192,
        return_attention_mask=False,
    )

    source_tokens = tokenizer.convert_ids_to_tokens(
        encoded["input_ids"]
    )

    target_codes = [
        LANGUAGES["zh"]["nllb_code"],
        LANGUAGES["vi"]["nllb_code"],
    ]

    target_tokens = []

    for target_code in target_codes:

        target_id = tokenizer.convert_tokens_to_ids(
            target_code
        )

        if target_id == tokenizer.unk_token_id:
            raise ValueError(
                f"NLLB 언어 토큰을 찾을 수 없습니다: "
                f"{target_code}"
            )

        target_token = tokenizer.convert_ids_to_tokens(
            [target_id]
        )[0]

        target_tokens.append(
            target_token
        )

    start = time.perf_counter()

    results = translator.translate_batch(
        [
            source_tokens,
            source_tokens,
        ],
        target_prefix=[
            [target_tokens[0]],
            [target_tokens[1]],
        ],
        beam_size=BEAM_SIZE,
        max_decoding_length=MAX_DECODING_LENGTH,
        repetition_penalty=1.05,
        return_scores=False,
    )

    elapsed = time.perf_counter() - start

    chinese = _decode_result(
        tokenizer,
        results[0],
        target_tokens[0],
    )

    vietnamese = _decode_result(
        tokenizer,
        results[1],
        target_tokens[1],
    )

    return {
        "source": normalized,
        "zh": chinese,
        "vi": vietnamese,
        "translation_time": elapsed,
        "device": TRANSLATION_DEVICE,
    }


# =========================================================
# English + Chinese + Vietnamese Batch Translation
#
# The legacy dual functions above are intentionally left unchanged so
# existing ZH/VI callers and benchmark baselines retain their API.
# =========================================================

def translate_triple_batch(
    korean_text: str,
) -> dict[str, Any]:
    """Translate one Korean input to English, Chinese, and Vietnamese."""

    normalized = " ".join(korean_text.strip().split())
    if not normalized:
        raise ValueError("번역할 한국어 문장이 없습니다.")

    tokenizer, translator = load_model()
    tokenizer.src_lang = SOURCE_LANGUAGE
    encoded = tokenizer(
        normalized,
        add_special_tokens=True,
        truncation=True,
        max_length=192,
        return_attention_mask=False,
    )
    source_tokens = tokenizer.convert_ids_to_tokens(encoded["input_ids"])

    language_keys = ("en", "zh", "vi")
    target_tokens: list[str] = []
    for language_key in language_keys:
        target_code = LANGUAGES[language_key]["nllb_code"]
        target_id = tokenizer.convert_tokens_to_ids(target_code)
        if target_id == tokenizer.unk_token_id:
            raise ValueError(
                f"NLLB 언어 토큰을 찾을 수 없습니다: {target_code}"
            )
        target_tokens.append(tokenizer.convert_ids_to_tokens([target_id])[0])

    start = time.perf_counter()
    results = translator.translate_batch(
        [source_tokens] * len(language_keys),
        target_prefix=[[token] for token in target_tokens],
        beam_size=BEAM_SIZE,
        max_decoding_length=MAX_DECODING_LENGTH,
        repetition_penalty=1.05,
        return_scores=False,
    )
    elapsed = time.perf_counter() - start

    translations = {
        language_key: _decode_result(tokenizer, result, target_token)
        for language_key, result, target_token in zip(
            language_keys,
            results,
            target_tokens,
        )
    }
    return {
        "source": normalized,
        **translations,
        "translation_time": elapsed,
        "device": TRANSLATION_DEVICE,
    }


def translate_triple_safe(
    korean_text: str,
) -> dict[str, Any]:
    """Safety-aware EN/ZH/VI translation without changing the dual path."""

    from src.translation.safety_preprocessor import preprocess_for_translation
    from src.translation.safety_guard import validate_translation_triple
    from src.translation.safety_fallback import apply_safety_fallback_triple

    normalized = " ".join(korean_text.strip().split())
    if not normalized:
        raise ValueError("번역할 한국어 문장이 없습니다.")

    safe_result = preprocess_for_translation(normalized)
    processed = safe_result["processed"]
    units = safe_result.get("units", []) or [processed]

    final_units = {key: [] for key in ("en", "zh", "vi")}
    raw_units = {key: [] for key in ("en", "zh", "vi")}
    unit_results: list[dict[str, Any]] = []
    total_translation_time = 0.0
    fallback_used_any = False

    for unit in units:
        unit = " ".join(unit.strip().split())
        if not unit:
            continue

        result = translate_triple_batch(unit)
        raw = {key: result[key].strip() for key in ("en", "zh", "vi")}
        elapsed = float(result.get("translation_time", 0.0))
        total_translation_time += elapsed

        initial_validation = validate_translation_triple(
            unit, raw["en"], raw["zh"], raw["vi"]
        )
        fallback = apply_safety_fallback_triple(
            english="",
            chinese="",
            vietnamese="",
            en_missing=initial_validation["en_missing"],
            zh_missing=initial_validation["zh_missing"],
            vi_missing=initial_validation["vi_missing"],
        )
        final = dict(raw)
        replaced = {}
        for key in ("en", "zh", "vi"):
            fallback_text = fallback[key].strip()
            replaced[key] = bool(fallback_text)
            if fallback_text:
                final[key] = fallback_text
        fallback_used_any = fallback_used_any or fallback["fallback_used"]

        final_validation = validate_translation_triple(
            unit, final["en"], final["zh"], final["vi"]
        )
        for key in final_units:
            raw_units[key].append(raw[key])
            final_units[key].append(final[key])
        unit_results.append({
            "ko": unit,
            "raw_en": raw["en"], "raw_zh": raw["zh"], "raw_vi": raw["vi"],
            "en": final["en"], "zh": final["zh"], "vi": final["vi"],
            "required_concepts": initial_validation["required_concepts"],
            "initial_safety_validation": initial_validation,
            "safety_validation": final_validation,
            "en_replaced": replaced["en"],
            "zh_replaced": replaced["zh"],
            "vi_replaced": replaced["vi"],
            "translation_time": elapsed,
        })

    if not unit_results:
        raise RuntimeError("번역 가능한 안전 문장이 없습니다.")

    final = {key: " ".join(values).strip() for key, values in final_units.items()}
    raw = {key: " ".join(values).strip() for key, values in raw_units.items()}
    final_validation = validate_translation_triple(
        processed, final["en"], final["zh"], final["vi"]
    )
    initial_validation = validate_translation_triple(
        processed, raw["en"], raw["zh"], raw["vi"]
    )
    return {
        "source": normalized,
        "processed": processed,
        "units": units,
        **final,
        "raw_en": raw["en"], "raw_zh": raw["zh"], "raw_vi": raw["vi"],
        "unit_results": unit_results,
        "translation_time": total_translation_time,
        "device": TRANSLATION_DEVICE,
        "preprocess_matches": safe_result.get("matches", []),
        "fallback_used": fallback_used_any,
        "initial_safety_validation": initial_validation,
        "safety_validation": final_validation,
        **{
            key: value
            for key, value in final_validation.items()
            if key != "details"
        },
        "initial_en_safe": initial_validation["en_safe"],
        "initial_zh_safe": initial_validation["zh_safe"],
        "initial_vi_safe": initial_validation["vi_safe"],
        "initial_en_missing": initial_validation["en_missing"],
        "initial_zh_missing": initial_validation["zh_missing"],
        "initial_vi_missing": initial_validation["vi_missing"],
    }



# =========================================================
# Safety-aware Dual Translation
# =========================================================

def translate_dual_safe(
    korean_text: str,
) -> dict[str, Any]:
    """
    건설안전 문장을 의미 단위로 분리한 뒤 번역한다.

    각 의미 단위마다 Safety Guard를 적용하고,
    안전 의미가 누락된 언어만 Safety Fallback으로
    교체한다.

    따라서 정상 번역은 최대한 유지하고,
    위험한 번역만 안전 문장으로 대체한다.
    """

    from src.translation.safety_preprocessor import (
        preprocess_for_translation,
    )
    from src.translation.safety_guard import (
        validate_translation,
    )
    from src.translation.safety_fallback import (
        COMPOUND_FALLBACKS,
        apply_safety_fallback,
    )

    normalized = " ".join(
        korean_text.strip().split()
    )

    if not normalized:
        raise ValueError(
            "번역할 한국어 문장이 없습니다."
        )

    # -----------------------------------------------------
    # 0. 현장관리자 검증 문장 확인
    # -----------------------------------------------------

    from src.translation.verified_site_translations import (
        get_verified_translation,
    )

    verified_translation = get_verified_translation(
        normalized
    )

    # -----------------------------------------------------
    # 1. 안전 전처리 + 의미 단위 분리
    # -----------------------------------------------------

    safe_result = preprocess_for_translation(
        normalized
    )

    processed = safe_result["processed"]
    units = safe_result.get("units", [])

    if not units:
        units = [processed]

    final_zh_units: list[str] = []
    final_vi_units: list[str] = []

    unit_results: list[dict[str, Any]] = []

    total_translation_time = 0.0
    fallback_used_any = False

    # -----------------------------------------------------
    # 2. 의미 단위별 NLLB 번역
    # -----------------------------------------------------

    for unit in units:

        unit = " ".join(
            unit.strip().split()
        )

        if not unit:
            continue

        result = translate_dual_batch(
            unit
        )

        raw_zh = result["zh"].strip()
        raw_vi = result["vi"].strip()

        elapsed = float(
            result.get(
                "translation_time",
                0.0,
            )
        )

        total_translation_time += elapsed

        # -------------------------------------------------
        # 3. 해당 의미 단위의 NLLB 결과 검증
        # -------------------------------------------------

        initial_validation = validate_translation(
            unit,
            raw_zh,
            raw_vi,
        )

        required_concepts = initial_validation[
            "required_concepts"
        ]

        zh_missing = initial_validation[
            "zh_missing"
        ]

        vi_missing = initial_validation[
            "vi_missing"
        ]

        # 기본적으로 NLLB 결과를 사용
        final_zh = raw_zh
        final_vi = raw_vi

        zh_replaced = False
        vi_replaced = False

        zh_fallback = ""
        vi_fallback = ""

        # -------------------------------------------------
        # 4. 중국어 실패 시 중국어 unit만 교체
        # -------------------------------------------------

        if zh_missing:

            fallback = apply_safety_fallback(
                chinese="",
                vietnamese="",
                zh_missing=zh_missing,
                vi_missing=[],
            )

            fallback_text = fallback[
                "zh"
            ].strip()

            if fallback_text:
                final_zh = fallback_text
                zh_fallback = fallback_text
                zh_replaced = True
                fallback_used_any = True

        # -------------------------------------------------
        # 5. 베트남어 실패 시 베트남어 unit만 교체
        # -------------------------------------------------

        if vi_missing:

            fallback = apply_safety_fallback(
                chinese="",
                vietnamese="",
                zh_missing=[],
                vi_missing=vi_missing,
            )

            fallback_text = fallback[
                "vi"
            ].strip()

            if fallback_text:
                final_vi = fallback_text
                vi_fallback = fallback_text
                vi_replaced = True
                fallback_used_any = True

        # -------------------------------------------------
        # 6. 교체 후 해당 unit 재검증
        # -------------------------------------------------

        final_validation = validate_translation(
            unit,
            final_zh,
            final_vi,
        )

        final_zh_units.append(
            final_zh
        )

        final_vi_units.append(
            final_vi
        )

        unit_results.append({
            "ko": unit,

            "raw_zh": raw_zh,
            "raw_vi": raw_vi,

            "zh": final_zh,
            "vi": final_vi,

            "required_concepts": required_concepts,

            "initial_zh_safe": initial_validation[
                "zh_safe"
            ],
            "initial_vi_safe": initial_validation[
                "vi_safe"
            ],

            "initial_zh_missing": zh_missing,
            "initial_vi_missing": vi_missing,

            "zh_replaced": zh_replaced,
            "vi_replaced": vi_replaced,

            "zh_fallback": zh_fallback,
            "vi_fallback": vi_fallback,

            "final_zh_safe": final_validation[
                "zh_safe"
            ],
            "final_vi_safe": final_validation[
                "vi_safe"
            ],

            "final_zh_missing": final_validation[
                "zh_missing"
            ],
            "final_vi_missing": final_validation[
                "vi_missing"
            ],

            "translation_time": elapsed,
        })

    if not unit_results:
        raise RuntimeError(
            "번역 가능한 안전 문장이 없습니다."
        )

    # -----------------------------------------------------
    # 7. 최종 의미 단위 결합
    # -----------------------------------------------------

    chinese = " ".join(
        final_zh_units
    ).strip()

    vietnamese = " ".join(
        final_vi_units
    ).strip()

    # -----------------------------------------------------
    # 8. 전체 문장 최종 Safety Guard
    # -----------------------------------------------------

    final_validation = validate_translation(
        processed,
        chinese,
        vietnamese,
    )

    # Units are translated independently, so a compound concept spanning two
    # source sentences is not visible to the per-unit fallback above.  Apply
    # its complete fallback only after the joined result has been checked.
    for language, missing_key, fallback_key in (
        ("zh", "zh_missing", "zh"),
        ("vi", "vi_missing", "vi"),
    ):
        compound_missing = [
            concept
            for concept in final_validation[missing_key]
            if concept in COMPOUND_FALLBACKS
        ]
        if len(compound_missing) != 1:
            continue

        fallback = apply_safety_fallback(
            chinese="",
            vietnamese="",
            zh_missing=compound_missing if language == "zh" else [],
            vi_missing=compound_missing if language == "vi" else [],
        )
        fallback_text = fallback[fallback_key].strip()
        if not fallback_text:
            continue

        if language == "zh":
            chinese = fallback_text
        else:
            vietnamese = fallback_text
        fallback_used_any = True

    # -----------------------------------------------------
    # 8-1. 현장관리자 검증 번역 최종 우선 적용
    # -----------------------------------------------------

    verified_used = False

    if verified_translation is not None:

        verified_zh = verified_translation.get(
            "zh",
            "",
        ).strip()

        verified_vi = verified_translation.get(
            "vi",
            "",
        ).strip()

        if verified_zh:
            chinese = verified_zh

        if verified_vi:
            vietnamese = verified_vi

        verified_used = bool(
            verified_zh or verified_vi
        )

    # 검증 번역 적용 후 최종 Safety Guard 재검증
    final_validation = validate_translation(
        processed,
        chinese,
        vietnamese,
    )

    # -----------------------------------------------------
    # 9. 초기 NLLB 전체 결과도 평가용으로 생성
    # -----------------------------------------------------

    raw_chinese = " ".join(
        item["raw_zh"]
        for item in unit_results
    ).strip()

    raw_vietnamese = " ".join(
        item["raw_vi"]
        for item in unit_results
    ).strip()

    initial_validation = validate_translation(
        processed,
        raw_chinese,
        raw_vietnamese,
    )

    return {
        "source": normalized,
        "processed": processed,
        "units": units,

        # 최종 송출용 결과
        "zh": chinese,
        "vi": vietnamese,

        # NLLB 원본 결과
        "raw_zh": raw_chinese,
        "raw_vi": raw_vietnamese,

        "unit_results": unit_results,

        "translation_time": total_translation_time,
        "device": TRANSLATION_DEVICE,

        "preprocess_matches": safe_result.get(
            "matches",
            [],
        ),

        "required_concepts": final_validation[
            "required_concepts"
        ],

        # 최종 결과
        "zh_safe": final_validation[
            "zh_safe"
        ],
        "vi_safe": final_validation[
            "vi_safe"
        ],

        "zh_missing": final_validation[
            "zh_missing"
        ],
        "vi_missing": final_validation[
            "vi_missing"
        ],

        "all_safe": final_validation[
            "all_safe"
        ],

        # Fallback 사용 여부
        "fallback_used": fallback_used_any,

        # 현장관리자 검증 번역 사용 여부
        "verified_translation_used": verified_used,

        # Fallback 전 상태
        "initial_zh_safe": initial_validation[
            "zh_safe"
        ],
        "initial_vi_safe": initial_validation[
            "vi_safe"
        ],

        "initial_zh_missing": initial_validation[
            "zh_missing"
        ],
        "initial_vi_missing": initial_validation[
            "vi_missing"
        ],

        "initial_safety_validation":
            initial_validation,

        "safety_validation":
            final_validation,
    }


# =========================================================
# 단독 실행 테스트
# =========================================================

if __name__ == "__main__":

    test_text = (
        "작업자는 중장비 위험구역에서 "
        "즉시 벗어나십시오."
    )

    result = translate_dual_batch(
        test_text
    )

    print("\n[Korean]")
    print(result["source"])

    print("\n[Chinese]")
    print(result["zh"])

    print("\n[Vietnamese]")
    print(result["vi"])

    print(
        f"\nTranslation time: "
        f"{result['translation_time']:.3f} sec"
    )
