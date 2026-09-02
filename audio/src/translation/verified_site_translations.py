from __future__ import annotations

import re
from difflib import SequenceMatcher


VERIFIED_SITE_TRANSLATIONS = {


    "오늘 공구리 치니까 가네 먼저 잡아라.": {
        "zh": "今天要浇筑混凝土，先把直角和位置校准好。",
        "vi": "Hôm nay sẽ đổ bê tông, trước tiên hãy căn chỉnh góc vuông và vị trí cho chính xác.",
    },

    "나라기까기 덜 됐어, 다시 한 번 밀어.": {
        "zh": "表面找平还没做好，再找平一遍。",
        "vi": "Bề mặt vẫn chưa được làm phẳng đạt yêu cầu, hãy làm phẳng lại một lượt nữa.",
    },

    "일 빨리 끝내고 야리끼리하자": {
        "zh": "抓紧把活干完，干完就收工。",
        "vi": "Làm nhanh cho xong phần việc rồi kết thúc công việc.",
    },

    "이거 안 깨지니까 오함마 가져와.": {
        "zh": "这个砸不碎，把大锤拿来。",
        "vi": "Cái này đập không vỡ, mang búa tạ lại đây.",
    },

    "아시바 먼저 놓고 위에서 작업해": {
        "zh": "先把脚手架搭好，再到上面作业。",
        "vi": "Lắp giàn giáo trước rồi mới làm việc ở phía trên.",
    },

    "덴고로 조금만 들어서 맞춰봐": {
        "zh": "稍微吊起一点，对准位置。",
        "vi": "Nâng lên một chút rồi căn chỉnh cho đúng vị trí.",
    },


    "취부 안 맞으면 다음 공정 다 틀어진다.": {
        "zh": "定位安装不准确，后续工序都会出问题。",
        "vi": "Nếu lắp đặt căn chỉnh không chính xác, các công đoạn sau đều sẽ bị sai.",
    },

    "이 높이는 말비계면 충분해, 괜히 달지마": {
        "zh": "这个高度使用低型作业脚手架就足够了，不要安装不必要的脚手架。",
        "vi": "Ở độ cao này chỉ cần dùng giàn giáo thấp là đủ, không cần lắp thêm giàn giáo không cần thiết.",
    },

    "여긴 발 디딜 데 없어. 달비계 아니면 작업 안 된다.": {
        "zh": "这里没有落脚的地方，不使用吊脚手架就不能作业。",
        "vi": "Ở đây không có chỗ đặt chân; nếu không dùng giàn giáo treo thì không được làm việc.",
    },

    "벽린제 먼저 치고 외벽 작업 들어가": {
        "zh": "先完成墙体的前置防护和准备工作，再进行外墙作业。",
        "vi": "Hoàn thành công tác chuẩn bị và bảo vệ tường trước, sau đó mới tiến hành công việc tường ngoài.",
    },

    "판넬 순서 잘못 올라갔어, 다시 내려.": {
        "zh": "面板吊装顺序错了，重新放下来。",
        "vi": "Thứ tự nâng các tấm panel lên bị sai, hãy hạ xuống lại.",
    },


    "위험하니까 전부 작업중지해": {
        "zh": "有危险，所有人员立即停止作业。",
        "vi": "Có nguy hiểm, tất cả mọi người phải dừng công việc ngay lập tức.",
    },

    "여긴 접근금지니까 절대 들어오지 마.": {
        "zh": "这里禁止进入，绝对不要进去。",
        "vi": "Khu vực này cấm vào, tuyệt đối không được đi vào.",
    },

    "헬멧이랑 안전화, 보호구 착용부터 해": {
        "zh": "先佩戴安全帽、安全鞋及其他防护用品。",
        "vi": "Trước tiên phải đội mũ bảo hộ, mang giày bảo hộ và các trang bị bảo hộ khác.",
    },

    "여기 추락주의니까 난간 잡고 이동해.": {
        "zh": "这里有坠落危险，移动时要抓稳护栏。",
        "vi": "Khu vực này có nguy cơ rơi ngã, hãy bám chắc lan can khi di chuyển.",
    },

    "전원 살아 있어, 감전에 주의해.": {
        "zh": "电源仍然带电，注意触电。",
        "vi": "Nguồn điện vẫn đang có điện, chú ý nguy cơ điện giật.",
    },

    "여기 화기엄금이니까 불 사용 금지야.": {
        "zh": "此处严禁明火，禁止使用火源。",
        "vi": "Khu vực này cấm lửa, không được sử dụng nguồn lửa.",
    },

    "용접 들어가면 수정 안 돼, 취부 다시 확인해.": {
        "zh": "一旦开始焊接就不能再修改，重新确认定位安装是否正确。",
        "vi": "Một khi bắt đầu hàn sẽ không thể sửa lại, hãy kiểm tra lại việc lắp đặt căn chỉnh.",
    },

    "지금 타설 들어가면 되돌릴 수 없어, 준비 끝났어?": {
        "zh": "现在开始浇筑混凝土后就无法返工，准备工作都完成了吗？",
        "vi": "Khi bắt đầu đổ bê tông thì sẽ không thể làm lại, mọi công tác chuẩn bị đã hoàn tất chưa?",
    },

    "양중 중이니까 아래 전부 비워": {
        "zh": "正在进行吊装作业，下面区域所有人员立即撤离。",
        "vi": "Đang thực hiện công việc nâng hạ, tất cả mọi người phải rời khỏi khu vực phía dưới ngay lập tức.",
    },

    "해체는 위에서부터, 순서 절대 바꾸지 마.": {
        "zh": "拆除作业必须从上往下进行，绝对不得改变作业顺序。",
        "vi": "Công việc tháo dỡ phải thực hiện từ trên xuống dưới, tuyệt đối không được thay đổi trình tự thi công.",
    },
}


def _normalize(text: str) -> str:
    

    text = text.strip()


    text = re.sub(r"\s+", "", text)


    text = re.sub(
        r"[.,!?~…·,:;\"'“”‘’(){}\[\]]",
        "",
        text,
    )

    return text


STT_ALIASES = {
    "여긴 접근근지니까 절대 들어오지 마": "여긴 접근금지니까 절대 들어오지 마.",

    "용답 들어가면 수정 안 돼 취부 다시 확인해": "용접 들어가면 수정 안 돼, 취부 다시 확인해.",
    "용답 들어가면 수정 안 돼 부재 위치 맞춤 및 고정 다시 확인해": "용접 들어가면 수정 안 돼, 취부 다시 확인해.",

    "양종 추리니가 아리전부 피워": "양중 중이니까 아래 전부 비워",
    "양정 중이니까 안의 전복이오": "양중 중이니까 아래 전부 비워",

    "배면 흔한 발견주의 주변 여기 화기 엉덩이니까 불사용금지야": "여기 화기엄금이니까 불 사용 금지야.",

    "나라시가 기별됐어 다시 한 번 밀어": "나라기까기 덜 됐어, 다시 한 번 밀어.",
    "바닥 고르기가 기별됐어 다시 한 번 밀어": "나라기까기 덜 됐어, 다시 한 번 밀어.",

    "양종 중이니까 아래 전부 비워": "양중 중이니까 아래 전부 비워",

    "위험하니까 전부 작업중지에": "위험하니까 전부 작업중지해",
    "위험하니까 전부 작업 중지에": "위험하니까 전부 작업중지해",

    "나라시 깍이 덜 됐어 다시 한 번 밀어": "나라기까기 덜 됐어, 다시 한 번 밀어.",
    "바닥 고르기 깍이 덜 됐어 다시 한 번 밀어": "나라기까기 덜 됐어, 다시 한 번 밀어.",
    "나라시각이 발됐어 다시 한 번 밀어": "나라기까기 덜 됐어, 다시 한 번 밀어.",
    "바닥 고르기각이 발됐어 다시 한 번 밀어": "나라기까기 덜 됐어, 다시 한 번 밀어.",


    "오늘 공구리 찌니까 간을 먼저 잡아라": "오늘 공구리 치니까 가네 먼저 잡아라.",
    "오늘 콘크리트 찌니까 간을 먼저 잡아라": "오늘 공구리 치니까 가네 먼저 잡아라.",

    "오늘 공구리치니까 갈래 먼저 잡아라": "오늘 공구리 치니까 가네 먼저 잡아라.",
    "오늘 콘크리트치니까 갈래 먼저 잡아라": "오늘 공구리 치니까 가네 먼저 잡아라.",
    "오늘 공구리치니까 간에 먼저 잡아라": "오늘 공구리 치니까 가네 먼저 잡아라.",
    "오늘 콘크리트치니까 간에 먼저 잡아라": "오늘 공구리 치니까 가네 먼저 잡아라.",

    "여기 초락주의니까 난간 잡고 이동해": "여기 추락주의니까 난간 잡고 이동해.",
    "된고로 조금만 들어서 맞춰봐": "덴고로 조금만 들어서 맞춰봐",
    "판넬 순서 잘못 올라갔어 다시 내려": "판넬 순서 잘못 올라갔어, 다시 내려.",
    "일 빨리 끝나고 야리끼리 하자": "일 빨리 끝내고 야리끼리하자",
    "일 빨리 끝나고 야리끼리 하죠": "일 빨리 끝내고 야리끼리하자",
}


CANONICAL_ANCHORS = {
    "오늘 공구리 치니까 가네 먼저 잡아라.": ("공구리", "콘크리트"),
    "나라기까기 덜 됐어, 다시 한 번 밀어.": ("나라시", "바닥고르기"),
    "일 빨리 끝내고 야리끼리하자": ("야리끼리",),
    "이거 안 깨지니까 오함마 가져와.": ("오함마", "대형망치"),
    "아시바 먼저 놓고 위에서 작업해": ("아시바", "비계"),
    "덴고로 조금만 들어서 맞춰봐": ("덴고", "된고"),
    "취부 안 맞으면 다음 공정 다 틀어진다.": ("취부",),
    "이 높이는 말비계면 충분해, 괜히 달지마": ("말비계", "우마"),
    "여긴 발 디딜 데 없어. 달비계 아니면 작업 안 된다.": ("달비계",),
    "벽린제 먼저 치고 외벽 작업 들어가": ("벽린제",),
    "판넬 순서 잘못 올라갔어, 다시 내려.": ("판넬", "패널"),
    "위험하니까 전부 작업중지해": ("작업중지", "작업중단"),
    "여긴 접근금지니까 절대 들어오지 마.": ("접근금지",),
    "헬멧이랑 안전화, 보호구 착용부터 해": ("헬멧", "안전화", "보호구"),
    "여기 추락주의니까 난간 잡고 이동해.": ("추락", "초락", "난간"),
    "전원 살아 있어, 감전에 주의해.": ("감전", "전원"),
    "여기 화기엄금이니까 불 사용 금지야.": ("화기엄금", "불사용"),
    "용접 들어가면 수정 안 돼, 취부 다시 확인해.": ("용접",),
    "지금 타설 들어가면 되돌릴 수 없어, 준비 끝났어?": ("타설",),
    "양중 중이니까 아래 전부 비워": ("양중", "양종", "양정"),
    "해체는 위에서부터, 순서 절대 바꾸지 마.": ("해체",),
}

FUZZY_MATCH_MIN_SCORE = 0.78
FUZZY_MATCH_MIN_MARGIN = 0.08


def get_verified_translation(text: str):
  
    normalized = _normalize(text)

  
    for source, translation in (
        VERIFIED_SITE_TRANSLATIONS.items()
    ):
        if _normalize(source) == normalized:
            return translation

  
    for alias, canonical in STT_ALIASES.items():
        if _normalize(alias) == normalized:

            canonical_normalized = _normalize(
                canonical
            )

            for source, translation in (
                VERIFIED_SITE_TRANSLATIONS.items()
            ):
                if _normalize(source) == canonical_normalized:
                    return translation


    candidates = []
    for source, translation in VERIFIED_SITE_TRANSLATIONS.items():
        anchors = CANONICAL_ANCHORS[source]
        if not any(_normalize(anchor) in normalized for anchor in anchors):
            continue

        score = SequenceMatcher(
            None,
            normalized,
            _normalize(source),
        ).ratio()
        candidates.append((score, source, translation))

    if not candidates:
        return None

    candidates.sort(reverse=True, key=lambda item: item[0])
    best_score, _source, best_translation = candidates[0]
    next_score = candidates[1][0] if len(candidates) > 1 else 0.0

    if (
        best_score >= FUZZY_MATCH_MIN_SCORE
        and best_score - next_score >= FUZZY_MATCH_MIN_MARGIN
    ):
        return best_translation

    return None
