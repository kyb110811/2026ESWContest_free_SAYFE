# -*- coding: utf-8 -*-
"""
construction_rules.py

임베디드SW경진대회 건설안전 다국어 안내 시스템용
건설현장 은어/현장용어 -> 표준 한국어 정규화 규칙

설계 원칙
1) 관리자 발화의 STT 결과를 바로 외국어로 번역하지 않고,
   먼저 현장 은어/일본어투/축약 표현을 표준 한국어로 정규화한다.
2) 위험 Fast Path에는 이 규칙을 사용하지 않는다.
   Fast Path는 사전 검증된 안전문구/음원을 사용한다.
3) "가스·밀폐공간" 관련 문장은 안전 의미가 달라지지 않도록
   가능한 한 명확한 표준 안전표현으로 바꾼다.

출처 구분
- USER_PRIOR: 이전 '건설용어 은어 교정' 대화에서 사용자가 제공한 정의
- FIELD_GLOSSARY: 건설현장 용어 자료에서 확인한 현장용례
- SAFETY_STANDARD: KOSHA/고용노동부의 밀폐공간·유해가스 안전용어에 맞춘 표준화
- DEMO_PATTERN: 시연용 관리자 발화 패턴. '공식 은어'라고 주장하지 않으며,
                실제 현장 인터뷰/교수 검토 후 확정 권장
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# 1. 핵심 건설 은어/현장용어 사전
# ---------------------------------------------------------------------------

TERM_RULES: Dict[str, Dict[str, str]] = {
    # ===== 이전 대화에서 사용자가 직접 제공한 항목 =====
    "가베": {
        "standard": "벽체",
        "category": "구조/위치",
        "source": "USER_PRIOR",
        "note": "조적벽, 콘크리트벽, 목재벽 등 벽체를 지칭하는 현장 표현",
    },
    "곰방": {
        "standard": "자재 운반",
        "category": "운반/작업",
        "source": "USER_PRIOR",
        "note": "벽돌, 모래, 시멘트 등 각종 자재를 필요한 위치로 운반하는 작업",
    },
    "나라시": {
        "standard": "바닥 고르기",
        "category": "토공/미장",
        "source": "USER_PRIOR",
        "note": "콘크리트, 흙, 모래 등의 바닥면을 평평하게 고르는 작업",
    },
    "노리비끼": {
        "standard": "시멘트풀칠",
        "category": "방수/미장",
        "source": "USER_PRIOR",
        "note": "방수재 또는 시멘트풀을 벽체 하단 등에 밀도 있게 바르는 작업",
    },

    # ===== 현장 용어 자료에서 확인한 항목 =====
    "가꾸목": {"standard": "각목", "category": "목공", "source": "FIELD_GLOSSARY", "note": ""},
    "갑빠": {"standard": "방수포", "category": "자재/보호", "source": "FIELD_GLOSSARY", "note": "자재를 덮는 큰 포장"},
    "고데": {"standard": "흙손", "category": "공구", "source": "FIELD_GLOSSARY", "note": ""},
    "가다와꾸": {"standard": "거푸집", "category": "형틀", "source": "FIELD_GLOSSARY", "note": ""},
    "와꾸": {"standard": "틀", "category": "형틀", "source": "FIELD_GLOSSARY", "note": ""},
    "가다": {"standard": "틀", "category": "형틀", "source": "FIELD_GLOSSARY", "note": ""},
    "가따": {"standard": "절단기", "category": "공구", "source": "FIELD_GLOSSARY", "note": "철사나 못 등을 자르는 공구"},
    "구배": {"standard": "기울기", "category": "시공", "source": "FIELD_GLOSSARY", "note": ""},
    "다루끼": {"standard": "각재", "category": "목공", "source": "FIELD_GLOSSARY", "note": "현장에 따라 치수 의미가 달라질 수 있음"},
    "데모도": {"standard": "보조 작업자", "category": "인력", "source": "FIELD_GLOSSARY", "note": ""},
    "데꼬보꼬": {"standard": "요철", "category": "상태", "source": "FIELD_GLOSSARY", "note": "울퉁불퉁한 상태"},
    "데코보코": {"standard": "요철", "category": "상태", "source": "FIELD_GLOSSARY", "note": ""},
    "덴조": {"standard": "천장", "category": "구조/위치", "source": "FIELD_GLOSSARY", "note": ""},
    "덴죠": {"standard": "천장", "category": "구조/위치", "source": "FIELD_GLOSSARY", "note": ""},
    "도끼다시": {"standard": "바닥 연마", "category": "마감", "source": "FIELD_GLOSSARY", "note": ""},
    "도비": {"standard": "비계공", "category": "인력", "source": "FIELD_GLOSSARY", "note": ""},
    "루베": {"standard": "세제곱미터", "category": "단위", "source": "FIELD_GLOSSARY", "note": "m³"},
    "헤베": {"standard": "제곱미터", "category": "단위", "source": "FIELD_GLOSSARY", "note": "m²"},
    "메지": {"standard": "줄눈", "category": "조적/마감", "source": "FIELD_GLOSSARY", "note": ""},
    "고소리": {"standard": "시멘트 풀", "category": "재료", "source": "FIELD_GLOSSARY", "note": ""},
    "몰탈": {"standard": "모르타르", "category": "재료", "source": "FIELD_GLOSSARY", "note": ""},
    "미다시": {"standard": "콘크리트 면 마감", "category": "마감", "source": "FIELD_GLOSSARY", "note": ""},
    "바라시": {"standard": "거푸집 해체", "category": "형틀", "source": "FIELD_GLOSSARY", "note": ""},
    "반생이": {"standard": "굵은 철사", "category": "자재", "source": "FIELD_GLOSSARY", "note": ""},
    "반생": {"standard": "굵은 철사", "category": "자재", "source": "FIELD_GLOSSARY", "note": ""},
    "보르방": {"standard": "탁상 드릴", "category": "공구", "source": "FIELD_GLOSSARY", "note": ""},
    "뿌레카": {"standard": "콘크리트 파쇄기", "category": "공구/장비", "source": "FIELD_GLOSSARY", "note": ""},
    "빠데": {"standard": "퍼티", "category": "마감재", "source": "FIELD_GLOSSARY", "note": ""},
    "빠루": {"standard": "쇠지렛대", "category": "공구", "source": "FIELD_GLOSSARY", "note": ""},
    "사뽀도": {"standard": "지지대", "category": "가설/구조", "source": "FIELD_GLOSSARY", "note": ""},
    "삿보도": {"standard": "지지대", "category": "가설/구조", "source": "FIELD_GLOSSARY", "note": ""},
    "사시꼬미": {"standard": "콘센트", "category": "전기", "source": "FIELD_GLOSSARY", "note": "자료에 따라 꽂이쇠 의미도 있어 문맥 확인 필요"},
    "스미": {"standard": "먹줄", "category": "측량/마킹", "source": "FIELD_GLOSSARY", "note": ""},
    "스미다시": {"standard": "먹매김", "category": "측량/마킹", "source": "FIELD_GLOSSARY", "note": ""},
    "스페샤": {"standard": "스페이서", "category": "철근/형틀", "source": "FIELD_GLOSSARY", "note": ""},
    "시루시": {"standard": "표시", "category": "마킹", "source": "FIELD_GLOSSARY", "note": ""},
    "시아게": {"standard": "마감", "category": "마감", "source": "FIELD_GLOSSARY", "note": ""},
    "아시바": {"standard": "비계", "category": "가설", "source": "FIELD_GLOSSARY", "note": "현장에 따라 비계 파이프/발판 의미"},
    "야리가다": {"standard": "규준틀 설치", "category": "측량/기초", "source": "FIELD_GLOSSARY", "note": ""},
    "양중": {"standard": "기계 자재 운반", "category": "운반/장비", "source": "FIELD_GLOSSARY", "note": ""},
    "오도리바": {"standard": "계단참", "category": "구조/위치", "source": "FIELD_GLOSSARY", "note": ""},
    "오비끼": {"standard": "각재", "category": "목공", "source": "FIELD_GLOSSARY", "note": "현장에 따라 규격 의미가 달라질 수 있음"},
    "우마": {"standard": "말비계", "category": "가설", "source": "FIELD_GLOSSARY", "note": ""},
    "우메모도시": {"standard": "되메우기", "category": "토공", "source": "FIELD_GLOSSARY", "note": ""},
    "유까": {"standard": "바닥", "category": "구조/위치", "source": "FIELD_GLOSSARY", "note": ""},
    "젠다이": {"standard": "선반", "category": "마감/설비", "source": "FIELD_GLOSSARY", "note": ""},
    "코아": {"standard": "코어 천공", "category": "장비/작업", "source": "FIELD_GLOSSARY", "note": "콘크리트 벽 등을 원형으로 천공"},
    "하스리": {"standard": "쪼아내기", "category": "철거/파쇄", "source": "FIELD_GLOSSARY", "note": ""},
    "함마드릴": {"standard": "해머 드릴", "category": "공구", "source": "FIELD_GLOSSARY", "note": ""},
    "후앙": {"standard": "환풍기", "category": "환기/가스", "source": "FIELD_GLOSSARY", "note": "fan의 현장식 표현"},
    "히사시": {"standard": "처마", "category": "구조/위치", "source": "FIELD_GLOSSARY", "note": ""},
    "단도리": {"standard": "작업 준비", "category": "일반 작업", "source": "FIELD_GLOSSARY", "note": "채비, 준비"},
    "구루마": {"standard": "손수레", "category": "운반", "source": "FIELD_GLOSSARY", "note": ""},
    "공구리": {"standard": "콘크리트", "category": "재료", "source": "FIELD_GLOSSARY", "note": ""},
    "기리바리": {"standard": "버팀대", "category": "가설/구조", "source": "FIELD_GLOSSARY", "note": ""},
    "낫도": {"standard": "너트", "category": "철물", "source": "FIELD_GLOSSARY", "note": ""},
    "네지": {"standard": "나사", "category": "철물", "source": "FIELD_GLOSSARY", "note": ""},
    "닛빠": {"standard": "니퍼", "category": "공구", "source": "FIELD_GLOSSARY", "note": ""},
    "리야까": {"standard": "손수레", "category": "운반", "source": "FIELD_GLOSSARY", "note": ""},
    "쇼오트": {"standard": "합선", "category": "전기/안전", "source": "FIELD_GLOSSARY", "note": ""},

    # ===== 건설현장 안전 작업 용어집 추가 =====

    "나라시까기": {
        "standard": "표면 평탄화 작업",
        "category": "토공/미장",
        "source": "FIELD_GLOSSARY",
        "note": "표면을 고르게 만들기 위한 정리 및 평탄 작업",
    },

    "오함마": {
        "standard": "대형 망치",
        "category": "공구",
        "source": "FIELD_GLOSSARY",
        "note": "콘크리트 파쇄·철거 등에 사용하는 큰 망치",
    },

    "데꼬": {
        "standard": "쇠지렛대",
        "category": "공구",
        "source": "FIELD_GLOSSARY",
        "note": "지렛대 원리로 무거운 물체를 들어 올리거나 움직이는 공구",
    },

    "덴고": {
        "standard": "쇠지렛대",
        "category": "공구",
        "source": "FIELD_GLOSSARY",
        "note": "책자 예문에서 확인된 현장 표현",
    },

    "취부": {
        "standard": "부재 위치 맞춤 및 고정",
        "category": "설치/조립",
        "source": "FIELD_GLOSSARY",
        "note": "부재를 정확한 위치에 맞춰 고정하는 작업",
    },

    "말비계": {
        "standard": "이동식 비계",
        "category": "가설",
        "source": "FIELD_GLOSSARY",
        "note": "바닥에 세워 사용하는 이동식 비계",
    },

    "달비계": {
        "standard": "매달린 비계",
        "category": "가설",
        "source": "FIELD_GLOSSARY",
        "note": "구조물에 매달아 사용하는 비계",
    },

    "벽린제": {
        "standard": "외벽 추락방지망",
        "category": "가설/안전",
        "source": "FIELD_GLOSSARY",
        "note": "외벽 작업 시 작업자의 추락을 방지하는 안전 가림망",
    },

    "판넬": {
        "standard": "패널",
        "category": "외장/자재",
        "source": "FIELD_GLOSSARY",
        "note": "외벽·내벽 등에 사용하는 판형 자재",
    },

    "작업중지": {
        "standard": "작업 중지",
        "category": "안전/작업중지",
        "source": "FIELD_GLOSSARY",
        "note": "위험 발생 시 작업을 즉시 중단하는 지시",
    },

    "접근금지": {
        "standard": "접근 금지",
        "category": "안전/출입",
        "source": "FIELD_GLOSSARY",
        "note": "위험 구역의 출입 또는 접근 금지",
    },

    "추락주의": {
        "standard": "추락 주의",
        "category": "안전/추락",
        "source": "FIELD_GLOSSARY",
        "note": "높은 곳에서 떨어질 위험에 대한 경고",
    },

    "감전주의": {
        "standard": "감전 주의",
        "category": "안전/전기",
        "source": "FIELD_GLOSSARY",
        "note": "전기에 의한 감전 위험 경고",
    },

    "화기엄금": {
        "standard": "화기 엄금",
        "category": "안전/화재",
        "source": "FIELD_GLOSSARY",
        "note": "불꽃·흡연 등 화기 사용 금지",
    },

    "타설": {
        "standard": "콘크리트 타설",
        "category": "콘크리트",
        "source": "FIELD_GLOSSARY",
        "note": "콘크리트를 거푸집 내부에 붓는 작업",
    },

    "용접": {
        "standard": "용접",
        "category": "용접/화기",
        "source": "FIELD_GLOSSARY",
        "note": "금속을 가열·융착하여 접합하는 작업",
    },

    "조립": {
        "standard": "조립",
        "category": "설치/조립",
        "source": "FIELD_GLOSSARY",
        "note": "부재를 순서에 맞게 결합하는 작업",
    },

    "해체": {
        "standard": "해체",
        "category": "철거/해체",
        "source": "FIELD_GLOSSARY",
        "note": "설치된 구조물이나 시설물을 분해·철거하는 작업",
    },

    "가네": {
        "standard": "수직·수평 맞춤",
        "category": "설치/측량",
        "source": "FIELD_GLOSSARY",
        "note": "부재의 수직·수평이나 기준을 맞추는 현장 표현",
    },

}


# ---------------------------------------------------------------------------
# 2. 가스·밀폐공간 안전 문장 정규화
#
# 아래 DEMO_PATTERN은 "현장에서 반드시 이렇게 말한다"는 뜻이 아니다.
# 경진대회 시연에서 관리자가 자연스럽게 말할 수 있는 축약형을
# KOSHA/고용노동부 안전표현으로 명확하게 바꾸기 위한 규칙이다.
# ---------------------------------------------------------------------------

SAFETY_PHRASE_RULES: List[Tuple[str, str, str]] = [
    # 건설현장 용어집 문장형 정규화
    (r"오늘\s*공구리\s*치니까\s*가네\s*먼저\s*잡아라",
     "오늘 콘크리트를 타설하니까 수직·수평을 먼저 맞춰라",
     "FIELD_GLOSSARY"),

    (r"일\s*빨리\s*끝내고\s*야리끼리하자",
     "일을 빨리 끝내고 오늘 작업을 마치자", "FIELD_GLOSSARY"),

    (r"감전에\s*주의(해|해줘|해주세요|하세요)",
     "감전 위험에 주의해 주세요", "FIELD_GLOSSARY"),

    # (입력 패턴, 표준 한국어, 출처구분)
    (r"가스\s*(한번\s*)?체크(해|해줘|해주세요|해\s*봐|해봐)",
     "유해가스 농도를 확인해 주세요", "DEMO_PATTERN"),
    (r"가스\s*(한번\s*)?찍어\s*(봐|봐줘|주세요)",
     "유해가스 농도를 측정해 주세요", "DEMO_PATTERN"),
    (r"산소\s*(한번\s*)?찍어\s*(봐|봐줘|주세요)",
     "산소 농도를 측정해 주세요", "DEMO_PATTERN"),
    (r"산소\s*(한번\s*)?체크(해|해줘|해주세요|해\s*봐|해봐)",
     "산소 농도를 확인해 주세요", "DEMO_PATTERN"),
    (r"후앙\s*(좀\s*)?(돌려|돌려줘|돌려주세요|켜|켜줘|켜주세요)",
     "환풍기를 작동해 주세요", "DEMO_PATTERN"),
    (r"환기\s*(좀\s*)?(돌려|돌려줘|돌려주세요|시켜|시켜줘|시켜주세요)",
     "환기장치를 작동해 충분히 환기해 주세요", "DEMO_PATTERN"),
    (r"가스\s*경보기\s*(켜|켜줘|켜주세요|확인해|확인해줘|확인해주세요)",
     "가스누설경보기를 작동 상태로 확인해 주세요", "DEMO_PATTERN"),
    (r"맨홀\s*(안에\s*)?(들어가|들어가자|들어가세요|진입해|진입하세요)",
     "밀폐공간에 진입합니다", "DEMO_PATTERN"),
    (r"들어가기\s*전에\s*가스\s*(체크|확인)",
     "밀폐공간 진입 전에 유해가스 농도를 측정해 주세요", "DEMO_PATTERN"),
    (r"들어가기\s*전에\s*산소\s*(체크|확인)",
     "밀폐공간 진입 전에 산소 농도를 측정해 주세요", "DEMO_PATTERN"),
    (r"송기\s*마스크\s*(써|써라|써요|쓰세요|착용해|착용하세요)",
     "송기마스크를 착용해 주세요", "SAFETY_STANDARD"),
    (r"공기\s*호흡기\s*(써|써라|써요|쓰세요|착용해|착용하세요)",
     "공기호흡기를 착용해 주세요", "SAFETY_STANDARD"),
    (r"가스\s*나왔어",
     "유해가스가 감지되었습니다", "DEMO_PATTERN"),
    (r"가스\s*검출됐어",
     "유해가스가 감지되었습니다", "DEMO_PATTERN"),
    (r"산소\s*부족해",
     "산소 농도가 안전기준보다 낮습니다", "DEMO_PATTERN"),
    (r"질식\s*위험(이야|입니다|있어|있습니다)?",
     "질식 위험이 있습니다", "SAFETY_STANDARD"),
]


# ---------------------------------------------------------------------------
# 3. 안전 관련 표준어 메모
# ---------------------------------------------------------------------------

SAFETY_STANDARD_TERMS: Dict[str, str] = {
    "밀폐공간": "환기가 불충분해 산소결핍, 유해가스, 화재·폭발 등의 위험이 있는 공간",
    "산소결핍": "공기 중 산소 농도가 18% 미만인 상태",
    "유해가스": "인체에 유해한 영향을 미치는 가스",
    "가스누설경보기": "건설현장에서 발생하는 가연성가스 등을 탐지하여 경보하는 장치",
    "환기": "밀폐공간의 유해가스 제거 및 적정공기 유지를 위한 공기 교환",
    "송기마스크": "외부 급기원에서 공기를 공급받는 호흡용 보호구",
    "공기호흡기": "호흡용 공기를 자체적으로 공급하는 보호구",
}


def _normalize_spacing(text: str) -> str:
    """기본 공백 정리."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_terms(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    단어 단위 현장용어를 표준 한국어로 치환한다.

    Returns
    -------
    normalized_text : str
    matched_terms : list[dict]
        어떤 용어가 어떤 표준어로 바뀌었는지 UI/로그에 표시할 때 사용.
    """
    normalized = text
    matched: List[Dict[str, str]] = []

    # 긴 표현을 먼저 처리한다.
    for slang in sorted(TERM_RULES.keys(), key=len, reverse=True):
        info = TERM_RULES[slang]

        # 일반 한국어 문장 내부에서 우연히 포함될 위험이 큰 짧은 용어는
        # 독립된 현장용어로 사용된 경우에만 치환한다.
        if slang == "양중":
            pattern = r"(?<![가-힣])양중(?=\s*작업|\s|$|[,.!?])"
            updated, count = re.subn(
                pattern,
                info["standard"],
                normalized,
            )

        elif slang == "가다":
            pattern = r"(?<![가-힣])가다(?=\\s|$|[,.!?])"
            updated, count = re.subn(
                pattern,
                info["standard"],
                normalized,
            )

        else:
            count = normalized.count(slang)
            updated = normalized.replace(
                slang,
                info["standard"],
            ) if count else normalized

        if count:
            normalized = updated
            matched.append({
                "original": slang,
                "standard": info["standard"],
                "category": info["category"],
                "source": info["source"],
            })

    return _normalize_spacing(normalized), matched


def normalize_safety_phrases(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    가스/밀폐공간 관련 축약 지시를 안전 의미가 명확한 문장으로 바꾼다.
    """
    normalized = text
    matched: List[Dict[str, str]] = []

    for pattern, replacement, source in SAFETY_PHRASE_RULES:
        if re.search(pattern, normalized):
            before = normalized
            normalized = re.sub(pattern, replacement, normalized)
            matched.append({
                "original": before,
                "standard": normalized,
                "category": "가스/밀폐공간",
                "source": source,
            })

    return _normalize_spacing(normalized), matched


def normalize_construction_korean(text: str) -> Dict[str, object]:
    """
    STT 결과 -> 건설현장 표준 한국어 정규화.

    사용 예
    -------
    result = normalize_construction_korean(
        "가베 쪽 곰방 끝나면 맨홀 들어가기 전에 가스 한번 찍어봐"
    )
    print(result["normalized"])
    """
    original = _normalize_spacing(text)

    # 문장 패턴을 먼저 처리한 뒤 일반 은어를 처리한다.
    stage1, safety_matches = normalize_safety_phrases(original)
    stage2, term_matches = normalize_terms(stage1)

    return {
        "original": original,
        "normalized": stage2,
        "matches": safety_matches + term_matches,
    }


if __name__ == "__main__":
    tests = [
        "가베 쪽으로 곰방해 주세요",
        "가베 쪽 곰방 끝나면 나라시 해주세요",
        "맨홀 들어가기 전에 가스 한번 찍어봐",
        "후앙 좀 돌려주세요",
        "산소 체크하고 송기마스크 써",
        "바라시 하기 전에 아시바 쪽 확인해",
        "공구리 치기 전에 와꾸 단도리해",
    ]

    for sentence in tests:
        result = normalize_construction_korean(sentence)
        print("=" * 70)
        print("입력 :", result["original"])
        print("출력 :", result["normalized"])
        print("교정 :", result["matches"])
