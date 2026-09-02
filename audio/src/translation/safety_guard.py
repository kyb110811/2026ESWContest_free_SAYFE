from __future__ import annotations

from typing import Any


# =========================================================
# Safety Semantic Guard
# =========================================================
#
# 목적
# - NLLB 번역에서 안전 핵심 의미가 누락되었는지 검사
# - 평가문장 전체를 1:1 매핑하지 않음
# - 위험/행동/금지/보호구 등의 의미 단위를 검사
#
# 주의
# - 이것은 완전한 의미 이해 모델이 아니라
#   안전 핵심 의미 보존 여부를 확인하는 rule-based guard
# =========================================================


SAFETY_CONCEPTS = {

    # -----------------------------------------------------
    # 작업 / 장비 즉시 정지
    # -----------------------------------------------------
    "stop": {
        "ko": [
            "멈추십시오",
            "작업을 멈추",
            "작업을 중단",
            "장비를 정지",
        ],
        "zh": [
            "停止",
            "停下",
        ],
        "vi": [
            "dừng",
            "ngừng",
        ],
    },

    # -----------------------------------------------------
    # 대피
    # -----------------------------------------------------
    "evacuate": {
        "ko": [
            "대피",
        ],
        "zh": [
            "撤离",
            "离开",
            "逃离",
            "逃到",
        ],
        "vi": [
            "sơ tán",
            "rời",
            "thoát",
            "chạy trốn",
        ],
    },

    # -----------------------------------------------------
    # 접근 / 진입 / 통행 금지
    # -----------------------------------------------------
    "no_entry": {
        "ko": [
            "들어가지 마십시오",
            "들어오지 마십시오",
            "접근하지 마십시오",
            "통행하지 마십시오",
            "지나가지 마십시오",

            "들어가지 마세요",
            "들어오지 마세요",
            "접근하지 마세요",
            "다니지 마세요",
            "지나가지 마세요",
        ],
        "zh": [
            "不要进入",
            "别进入",
            "请勿进入",
            "不要靠近",
            "请勿靠近",
            "不要接近",
            "请勿接近",
            "不要通过",
            "请勿通过",
            "不要走",
            "别走",
            "不要过",
            "别过",
        ],
        "vi": [
            "đừng vào",
            "không được vào",
            "đừng tiếp cận",
            "không được tiếp cận",
            "đừng đi",
            "không được đi",
        ],
    },

    # -----------------------------------------------------
    # 전원 차단
    # -----------------------------------------------------
    "power_off": {
        "ko": [
            "전원을 완전히 차단",
            "전원을 차단",
        ],
        "zh": [
            "切断电源",
            "关闭电源",
            "断电",
        ],
        "vi": [
            "tắt điện",
            "ngắt điện",
            "ngắt nguồn",
        ],
    },

    # -----------------------------------------------------
    # 감전
    # -----------------------------------------------------
    "electric_shock": {
        "ko": [
            "감전",
        ],
        "zh": [
            "触电",
            "电击",
        ],
        "vi": [
            "điện giật",
        ],
    },

    # -----------------------------------------------------
    # 유해가스 / 가스누출
    # -----------------------------------------------------
    "gas": {
        "ko": [
            "유해가스",
            "유해 가스",
            "해로운 가스",
            "가스 누출",
        ],
        "zh": [
            "有害气体",
            "危害气体",
            "气体泄漏",
            "气体泄露",
        ],
        "vi": [
            "khí độc",
            "khí có hại",
            "khí gây hại",
            "rò rỉ khí",
        ],
    },

    # -----------------------------------------------------
    # 저산소
    # -----------------------------------------------------
    "low_oxygen": {
        "ko": [
            "산소 농도가 낮",
            "산소가 부족",
        ],
        "zh": [
            "氧气低",
            "氧气浓度低",
            "氧气浓度过低",
            "氧气含量低",
            "氧气含量过低",
            "低氧",
            "缺氧",
        ],
        "vi": [
            "oxy thấp",
            "thiếu oxy",
        ],
    },

    # -----------------------------------------------------
    # 환기 일반
    # -----------------------------------------------------
    "ventilation": {
        "ko": [
            "환기",
            "환기 장치",
        ],
        "zh": [
            "通风",
            "换气",
            "空气",
        ],
        "vi": [
            "thông gió",
        ],
    },

    # -----------------------------------------------------
    # 환기장치 정지 금지
    # "끄지 마십시오"의 부정 명령까지 확인
    # -----------------------------------------------------
    "keep_ventilation_on": {
        "ko": [
            "환기 장치를 끄지 마십시오",
            "환풍기 끄지 말고",
        ],
        "zh": [
            "请勿关闭",
            "不要关闭",
            "不要关",
            "别关闭",
            "别关",
        ],
        "vi": [
            "đừng tắt",
            "không tắt",
        ],
    },

    # -----------------------------------------------------
    # 환기장치 계속 운전
    # -----------------------------------------------------
    "keep_ventilation_running": {
        "ko": [
            "환기 장치를 계속 작동",
            "환풍기 계속 돌",
        ],
        "zh": [
            "继续运行",
            "继续通风",
            "保持通风",
        ],
        "vi": [
            "tiếp tục hoạt động",
            "tiếp tục thông gió",
            "duy trì thông gió",
            "hoạt động liên tục",
            "giữ thiết bị thông gió hoạt động liên tục",
        ],
    },

    # -----------------------------------------------------
    # 안전거리 확보
    # -----------------------------------------------------
    "safe_distance": {
        "ko": [
            "안전거리를 확보",
            "안전 거리",
        ],
        "zh": [
            "安全距离",
            "安全空间",
        ],
        "vi": [
            "khoảng cách an toàn",
        ],
    },

    # -----------------------------------------------------
    # 추락방지 안전대
    # -----------------------------------------------------
    "fall_protection": {
        "ko": [
            "안전대를 착용",
            "추락 방지용 안전대",
        ],
        "zh": [
            "安全带",
        ],
        "vi": [
            "dây an toàn",
            "dây đai an toàn",
        ],
    },

    # -----------------------------------------------------
    # 안전모
    # -----------------------------------------------------
    "helmet": {
        "ko": [
            "안전모",
            "하이바",
        ],
        "zh": [
            "安全帽",
        ],
        "vi": [
            "mũ bảo hộ",
            "mũ an toàn",
        ],
    },

    # -----------------------------------------------------
    # 가연물 제거
    # -----------------------------------------------------
    "remove_flammable": {
        "ko": [
            "가연물을 제거",
            "가연물 제거",
        ],
        "zh": [
            "易燃",
            "可燃",
            "清除",
            "移除",
        ],
        "vi": [
            "vật liệu dễ cháy",
            "chất dễ cháy",
            "loại bỏ",
        ],
    },

    # -----------------------------------------------------
    # 장비 조작 금지
    # -----------------------------------------------------
    "no_operation": {
        "ko": [
            "장비를 조작하지",
        ],
        "zh": [
            "不要操纵",
            "不要操作",
            "不得操作",
        ],
        "vi": [
            "không được điều khiển",
            "không điều khiển",
            "đừng điều khiển",
            "không được vận hành",
        ],
    },

    # -----------------------------------------------------
    # 위험부 손 투입 금지
    # -----------------------------------------------------
    "hands_off": {
        "ko": [
            "손을 넣지",
            "손을 대지",
        ],
        "zh": [
            "不要把手",
            "不要伸手",
            "别把手",
            "别伸手",
            "请勿将手伸入",
        ],
        "vi": [
            "đừng đưa tay",
            "không đưa tay",
            "không được đưa tay",
            "đừng chạm",
            "không chạm",
        ],
    },

    # -----------------------------------------------------
    # 자재 적치 금지
    # -----------------------------------------------------
    "no_material_storage": {
        "ko": [
            "자재 두지",
            "자재를 두지",
            "자재 쌓아두지",
            "자재를 쌓아두지",
        ],
        "zh": [
            "不要把材料",
            "不要堆",
            "不得堆",
            "不能放",
            "请勿在该区域堆放材料",
        ],
        "vi": [
            "đừng để vật liệu",
            "không để vật liệu",
            "không được để vật liệu",
            "đừng chất vật liệu",
            "không chất vật liệu",
        ],
    },

    # -----------------------------------------------------
    # 접촉 금지
    # -----------------------------------------------------
    "no_touch": {
        "ko": [
            "만지지 마십시오",
            "건드리지 마세요",
        ],
        "zh": [
            "不要碰",
            "别碰",
            "不要触摸",
            "请勿触摸",
        ],
        "vi": [
            "đừng chạm",
            "không chạm",
            "không được chạm",
            "không được chạm vào",
            "đừng sờ",
        ],
    },

    # -----------------------------------------------------
    # 작업 준비 완료 후 작업 시작
    # -----------------------------------------------------
    "start_work_after_prepare": {
        "ko": [
            "작업 준비가 끝나면 작업을 시작",
            "작업 준비 후 작업을 시작",
        ],
        "zh": [
            "准备完成后",
            "准备好后",
            "准备工作完成后",
            "开始工作",
        ],
        "vi": [
            "sau khi chuẩn bị",
            "sau khi chuẩn bị xong",
            "khi chuẩn bị xong",
            "bắt đầu công việc",
        ],
    },

    # -----------------------------------------------------
    # 콘크리트 타설
    # -----------------------------------------------------
    "concrete_pouring": {
        "ko": [
            "콘크리트를 타설",
            "콘크리트 타설",
        ],
        "zh": [
            "浇筑混凝土",
            "混凝土浇筑",
        ],
        "vi": [
            "đổ bê tông",
            "thi công bê tông",
        ],
    },

    # -----------------------------------------------------
    # 바닥 평탄화 작업 시작
    # -----------------------------------------------------
    "floor_leveling_start": {
        "ko": [
            "바닥을 평평하게 고르는 작업을 시작",
            "바닥 평탄화 작업을 시작",
        ],
        "zh": [
            "地面",
            "平整",
            "开始",
        ],
        "vi": [
            "sàn",
            "san phẳng",
            "bắt đầu",
        ],
    },

    # -----------------------------------------------------
    # 벽면 시멘트 풀 바르기 작업 시작
    # -----------------------------------------------------
    "cement_wall_coating_start": {
        "ko": [
            "시멘트 풀을 벽면에 바르는 작업",
            "벽면에 시멘트 풀을 바르는 작업",
        ],
        "zh": [
            "水泥浆",
            "墙面",
            "涂",
            "开始",
        ],
        "vi": [
            "hồ xi măng",
            "tường",
            "bôi",
            "bắt đầu",
        ],
    },

    # -----------------------------------------------------
    # 자재를 벽체 쪽으로 운반
    # -----------------------------------------------------
    "material_move_to_wall": {
        "ko": [
            "자재를 저쪽 벽체 쪽으로 운반",
            "벽체 쪽으로 자재 운반",
        ],
        "zh": [
            "材料",
            "墙",
            "运送",
            "运输",
        ],
        "vi": [
            "vật liệu",
            "tường",
            "vận chuyển",
        ],
    },

    # -----------------------------------------------------
    # 자재 운반 후 통로 정리
    # -----------------------------------------------------
    "clear_path_after_transport": {
        "ko": [
            "자재 운반이 끝나면 통로를 정리",
            "자재 운반 끝나면 통로 정리",
        ],
        "zh": [
            "运输",
            "通道",
            "清理",
            "整理",
        ],
        "vi": [
            "vận chuyển",
            "lối đi",
            "dọn",
        ],
    },

    # -----------------------------------------------------
    # 콘크리트 작업 전 주변 정리
    # -----------------------------------------------------
    "clear_area_for_concrete": {
        "ko": [
            "콘크리트 작업이 있으므로 작업 구역 주변을 정리",
            "콘크리트 작업 전에 주변을 정리",
        ],
        "zh": [
            "混凝土",
            "周围",
            "清理",
            "整理",
        ],
        "vi": [
            "bê tông",
            "khu vực",
            "dọn",
        ],
    },

    # -----------------------------------------------------
    # 콘크리트 작업 전 준비
    # -----------------------------------------------------
    "prepare_before_concrete": {
        "ko": [
            "콘크리트 작업을 시작하기 전에 작업 준비를 완료",
            "콘크리트 작업 전에 작업 준비",
        ],
        "zh": [
            "混凝土",
            "准备",
        ],
        "vi": [
            "bê tông",
            "chuẩn bị",
        ],
    },

    # -----------------------------------------------------
    # 콘크리트 틀 작업 전 준비
    # -----------------------------------------------------
    "prepare_before_formwork": {
        "ko": [
            "콘크리트 틀 작업을 시작하기 전에 작업 준비를 완료",
            "틀 작업 전에 작업 준비",
        ],
        "zh": [
            "模板",
            "准备",
        ],
        "vi": [
            "cốp pha",
            "ván khuôn",
            "chuẩn bị",
        ],
    },

    # -----------------------------------------------------
    # 작업용 발판 이동 전 준비
    # -----------------------------------------------------
    "prepare_before_scaffold_move": {
        "ko": [
            "작업용 발판을 이동하기 전에 작업 준비를 완료",
            "작업용 발판 옮길 작업 준비",
            "비계(작업용 발판) 옮길 작업 준비",
        ],
        "zh": [
            "脚手架",
            "移动",
            "准备",
        ],
        "vi": [
            "giàn giáo",
            "di chuyển",
            "chuẩn bị",
        ],
    },

    # -----------------------------------------------------
    # 바닥 평탄화 전 바닥 상태 확인
    # -----------------------------------------------------
    "check_floor_before_leveling": {
        "ko": [
            "바닥 평탄화 작업을 시작하기 전에 바닥 상태를 확인",
            "바닥을 평평하게 고르기 전에 바닥 확인",
        ],
        "zh": [
            "地面",
            "找平",
            "检查",
            "确认",
        ],
        "vi": [
            "sàn",
            "san phẳng",
            "kiểm tra",
        ],
    },

    # -----------------------------------------------------
    # 자재 운반 후 바닥 평탄화 준비
    # -----------------------------------------------------
    "prepare_leveling_after_transport": {
        "ko": [
            "자재 운반이 끝나면 바닥 평탄화 작업을 준비",
            "자재 운반 끝나면 바닥 평탄화 작업 준비",
        ],
        "zh": [
            "运输",
            "地面",
            "找平",
            "准备",
        ],
        "vi": [
            "vận chuyển",
            "sàn",
            "san phẳng",
            "chuẩn bị",
        ],
    },

    # -----------------------------------------------------
    # 작업구역 인원 확인
    # -----------------------------------------------------
    "person_check": {
        "ko": [
            "사람이 있는지 확인",
            "사람이 없는지 확인",
        ],
        "zh": [
            "检查",
            "确认",
            "有人",
            "没有人",
        ],
        "vi": [
            "kiểm tra",
            "xem có ai",
            "không có người",
        ],
    },

    # -----------------------------------------------------
    # 주변 / 아래쪽 비우기
    # -----------------------------------------------------
    "keep_clear": {
        "ko": [
            "사람과 물건을 치우십시오",
            "통로 비워",
            "아래쪽 비워",
        ],
        "zh": [
            "清除",
            "搬走",
            "移开",
        ],
        "vi": [
            "dọn",
            "di chuyển người",
            "đưa người",
        ],
    },
}


def _contains_any(
    text: str,
    keywords: list[str],
) -> bool:
    lowered = text.lower()

    return any(
        keyword.lower() in lowered
        for keyword in keywords
    )


# Source-specific sentence answers are deliberately not stored here.  These are
# reusable construction *meaning bundles*: the source clues select a bundle and
# every listed target-language unit must survive.  A bundle prevents a single
# word such as 安全帽 from incorrectly passing a transport instruction.
SEMANTIC_CONCEPTS: dict[str, dict[str, list[str]]] = {
    "excavator_moving_keep_out": {
        "ko": ["굴착기", "이동 중", "작업 반경"],
        "zh": ["挖掘机", "移动", "作业半径", "请勿进入"],
        "vi": ["máy xúc", "di chuyển", "bán kính", "không được vào"],
    },
    "excavator_rear_keep_out": {
        "ko": ["굴착기", "후방", "접근하지"],
        "zh": ["挖掘机", "后方", "请勿靠近"],
        "vi": ["máy xúc", "phía sau", "không được tiếp cận"],
    },
    "ventilate_before_entry": {
        "ko": ["밀폐 공간", "들어가기", "환기"],
        "zh": ["密闭空间", "进入", "充分通风"],
        "vi": ["không gian kín", "vào", "thông gió đầy đủ"],
    },
    "gas_oxygen_measurement": {
        "ko": ["산소", "가스 농도", "측정"],
        "zh": ["氧气浓度", "有害气体浓度", "测量"],
        "vi": ["nồng độ oxy", "khí độc", "đo"],
    },
    "gas_leak_evacuate_safe_area": {
        "ko": ["가스 누출", "안전구역", "대피"],
        "zh": ["气体泄漏", "安全区域", "撤离"],
        "vi": ["rò rỉ khí", "khu vực an toàn", "sơ tán"],
    },
    "electric_shock_power_off_before_work": {
        "ko": ["감전", "전원", "차단", "후 작업"],
        "zh": ["触电", "切断电源", "后", "作业"],
        "vi": ["điện giật", "ngắt nguồn", "sau khi", "làm việc"],
    },
    "welding_remove_flammable": {
        "ko": ["용접", "가연물", "제거"],
        "zh": ["焊接", "易燃物", "清除"],
        "vi": ["hàn", "vật liệu dễ cháy", "loại bỏ"],
    },
    "formwork_prepare_recheck_before_pouring": {
        "ko": ["타설", "거푸집", "준비", "다시 확인"],
        "zh": ["浇筑混凝土", "模板", "准备", "再次检查", "前"],
        "vi": ["đổ bê tông", "cốp pha", "chuẩn bị", "kiểm tra lại", "trước khi"],
    },
    "material_transport_helmet_passage_move": {
        "ko": ["자재를 운반", "작업자", "안전모", "통로", "이동"],
        "zh": ["材料", "运输", "工人", "安全帽", "通道", "移动"],
        "vi": ["vật liệu", "vận chuyển", "công nhân", "mũ bảo hộ", "lối đi", "di chuyển"],
    },
    "formwork_dismantle_scaffold_person_check": {
        "ko": ["거푸집", "해체", "비계", "사람이 없는지", "확인"],
        "zh": ["模板", "拆除", "脚手架", "无人", "确认"],
        "vi": ["cốp pha", "tháo dỡ", "giàn giáo", "không có người", "kiểm tra"],
    },
    "floor_leveling_no_pass": {
        "ko": ["바닥", "평평하게", "통행하지"],
        "zh": ["地面找平", "通行", "请勿"],
        "vi": ["san phẳng mặt sàn", "đi qua", "không được"],
    },
    "formwork_dismantle_clear_below": {
        "ko": ["거푸집", "해체", "아래쪽", "사람과 물건"],
        "zh": ["模板", "拆除", "下方", "清除"],
        "vi": ["cốp pha", "tháo dỡ", "phía dưới", "dọn"],
    },
    "scaffold_helmet_check_before_climb": {
        "ko": ["비계", "안전모", "올라가기", "확인"],
        "zh": ["脚手架", "安全帽", "攀登", "确认"],
        "vi": ["giàn giáo", "mũ bảo hộ", "leo", "kiểm tra"],
    },
    "ventilation_device_start_for_gas": {
        "ko": ["가스 위험", "환기 장치", "먼저", "작동"],
        "zh": ["气体", "通风设备", "先", "启动"],
        "vi": ["nguy cơ khí", "thiết bị thông gió", "trước", "khởi động"],
    },
    "keep_ventilation_until_work_end": {
        "ko": ["작업이 끝날 때까지", "환기 장치", "계속 작동"],
        "zh": ["作业结束", "通风设备", "持续运行"],
        "vi": ["kết thúc công việc", "thiết bị thông gió", "hoạt động liên tục"],
    },
    "check_floor_before_leveling_profile": {
        "ko": ["바닥 평탄화", "전에", "바닥 상태", "확인"],
        "zh": ["地面找平", "前", "地面状况", "检查"],
        "vi": ["san phẳng mặt sàn", "trước khi", "tình trạng sàn", "kiểm tra"],
    },
    "cement_coating_do_not_touch_wall": {
        "ko": ["시멘트 풀", "벽면", "바르는 중", "만지지"],
        "zh": ["水泥浆", "墙面", "涂抹", "请勿触摸"],
        "vi": ["hồ xi măng", "tường", "bôi", "không được chạm"],
    },
}


def _all_source_clues(text: str, clues: list[str]) -> bool:
    return all(clue in text for clue in clues)


def detect_required_concepts(
    korean_text: str,
) -> list[str]:

    required = []

    for concept, languages in SAFETY_CONCEPTS.items():

        # "시작하기 전에" is a precondition, not an instruction to start.
        # Treating it as both made a correct "check before leveling" fallback
        # fail by demanding a newly invented start action.
        if (
            concept == "floor_leveling_start"
            and "시작하기 전에" in korean_text
        ):
            continue

        if _contains_any(
            korean_text,
            languages["ko"],
        ):
            required.append(concept)

    for concept, languages in SEMANTIC_CONCEPTS.items():
        if _all_source_clues(korean_text, languages["ko"]):
            required.append(concept)

    return required


def validate_translation(
    korean_text: str,
    chinese: str,
    vietnamese: str,
) -> dict[str, Any]:

    required = detect_required_concepts(
        korean_text
    )

    zh_missing = []
    vi_missing = []

    details = []

    for concept in required:

        rules = (
            SEMANTIC_CONCEPTS[concept]
            if concept in SEMANTIC_CONCEPTS
            else SAFETY_CONCEPTS[concept]
        )

        # 복합 의미는 핵심 의미들이 모두 보존되어야 통과
        if concept == "start_work_after_prepare":

            zh_prepare_ok = _contains_any(
                chinese,
                [
                    "准备",
                    "准备工作",
                ],
            )

            zh_start_ok = _contains_any(
                chinese,
                [
                    "开始工作",
                    "开始作业",
                ],
            )

            zh_ok = (
                zh_prepare_ok
                and zh_start_ok
            )

            vi_prepare_ok = _contains_any(
                vietnamese,
                [
                    "chuẩn bị",
                    "công tác chuẩn bị",
                ],
            )

            vi_start_ok = _contains_any(
                vietnamese,
                [
                    "bắt đầu",
                    "bắt đầu công việc",
                ],
            )

            vi_ok = (
                vi_prepare_ok
                and vi_start_ok
            )

        elif concept == "concrete_pouring":

            zh_ok = _contains_any(
                chinese,
                [
                    "浇筑混凝土",
                    "混凝土浇筑",
                ],
            )

            vi_ok = _contains_any(
                vietnamese,
                [
                    "đổ bê tông",
                    "thi công bê tông",
                ],
            )

        elif concept == "floor_leveling_start":

            zh_floor_ok = _contains_any(
                chinese,
                [
                    "地面",
                    "地板",
                ],
            )

            zh_level_ok = _contains_any(
                chinese,
                [
                    "平整",
                    "找平",
                    "整平",
                ],
            )

            zh_start_ok = _contains_any(
                chinese,
                [
                    "开始",
                ],
            )

            zh_ok = (
                zh_floor_ok
                and zh_level_ok
                and zh_start_ok
            )

            vi_floor_ok = _contains_any(
                vietnamese,
                [
                    "sàn",
                    "mặt sàn",
                ],
            )

            vi_level_ok = _contains_any(
                vietnamese,
                [
                    "san phẳng",
                    "làm phẳng",
                ],
            )

            vi_start_ok = _contains_any(
                vietnamese,
                [
                    "bắt đầu",
                ],
            )

            vi_ok = (
                vi_floor_ok
                and vi_level_ok
                and vi_start_ok
            )

        elif concept == "cement_wall_coating_start":

            zh_cement_ok = _contains_any(
                chinese,
                [
                    "水泥浆",
                ],
            )

            zh_wall_ok = _contains_any(
                chinese,
                [
                    "墙面",
                    "墙壁",
                ],
            )

            zh_apply_ok = _contains_any(
                chinese,
                [
                    "涂",
                    "涂抹",
                ],
            )

            zh_start_ok = _contains_any(
                chinese,
                [
                    "开始",
                ],
            )

            zh_ok = (
                zh_cement_ok
                and zh_wall_ok
                and zh_apply_ok
                and zh_start_ok
            )

            vi_cement_ok = _contains_any(
                vietnamese,
                [
                    "hồ xi măng",
                    "vữa xi măng",
                ],
            )

            vi_wall_ok = _contains_any(
                vietnamese,
                [
                    "tường",
                    "bề mặt tường",
                ],
            )

            vi_apply_ok = _contains_any(
                vietnamese,
                [
                    "bôi",
                    "trát",
                    "quét",
                ],
            )

            vi_start_ok = _contains_any(
                vietnamese,
                [
                    "bắt đầu",
                ],
            )

            vi_ok = (
                vi_cement_ok
                and vi_wall_ok
                and vi_apply_ok
                and vi_start_ok
            )

        elif concept == "material_move_to_wall":
            zh_ok = (
                _contains_any(chinese, ["材料", "物料"])
                and _contains_any(chinese, ["墙", "墙体", "墙面"])
                and _contains_any(chinese, ["运送", "运输", "搬运"])
            )
            vi_ok = (
                _contains_any(vietnamese, ["vật liệu"])
                and _contains_any(vietnamese, ["tường"])
                and _contains_any(vietnamese, ["vận chuyển"])
            )

        elif concept == "clear_path_after_transport":
            zh_ok = (
                _contains_any(chinese, ["运输", "搬运"])
                and _contains_any(chinese, ["通道", "路线"])
                and _contains_any(chinese, ["清理", "整理"])
            )
            vi_ok = (
                _contains_any(vietnamese, ["vận chuyển"])
                and _contains_any(vietnamese, ["lối đi", "đường đi"])
                and _contains_any(vietnamese, ["dọn"])
            )

        elif concept == "clear_area_for_concrete":
            zh_ok = (
                _contains_any(chinese, ["混凝土"])
                and _contains_any(chinese, ["周围", "区域"])
                and _contains_any(chinese, ["清理", "整理"])
            )
            vi_ok = (
                _contains_any(vietnamese, ["bê tông"])
                and _contains_any(vietnamese, ["khu vực", "xung quanh"])
                and _contains_any(vietnamese, ["dọn"])
            )

        elif concept == "keep_ventilation_on":
            # "끄지 말 것"뿐 아니라 대상이 환기장치인지 함께 검증
            zh_ok = (
                _contains_any(
                    chinese,
                    ["通风设备", "通风装置", "换气设备"]
                )
                and _contains_any(
                    chinese,
                    ["请勿关闭", "不要关闭", "不要关", "别关闭", "别关"]
                )
            )

            vi_ok = (
                _contains_any(
                    vietnamese,
                    ["thiết bị thông gió", "máy thông gió"]
                )
                and _contains_any(
                    vietnamese,
                    ["đừng tắt", "không được tắt", "không tắt"]
                )
            )

        elif concept == "keep_ventilation_running":
            # "계속 작동"만으로 통과시키지 않고
            # 반드시 환기장치 + 지속운전 의미가 함께 있어야 함
            zh_ok = (
                _contains_any(
                    chinese,
                    ["通风设备", "通风装置", "换气设备"]
                )
                and _contains_any(
                    chinese,
                    ["持续运行", "继续运行", "保持运行"]
                )
            )

            vi_ok = (
                _contains_any(
                    vietnamese,
                    ["thiết bị thông gió", "máy thông gió"]
                )
                and _contains_any(
                    vietnamese,
                    [
                        "hoạt động liên tục",
                        "tiếp tục hoạt động",
                        "tiếp tục chạy",
                        "duy trì hoạt động",
                    ]
                )
            )

        elif concept == "prepare_before_concrete":
            zh_ok = (
                _contains_any(chinese, ["混凝土"])
                and _contains_any(chinese, ["准备"])
            )
            vi_ok = (
                _contains_any(vietnamese, ["bê tông"])
                and _contains_any(vietnamese, ["chuẩn bị"])
            )

        elif concept == "prepare_before_formwork":
            zh_ok = (
                _contains_any(chinese, ["模板"])
                and _contains_any(chinese, ["准备"])
            )
            vi_ok = (
                _contains_any(vietnamese, ["cốp pha", "ván khuôn"])
                and _contains_any(vietnamese, ["chuẩn bị"])
            )

        elif concept == "prepare_before_scaffold_move":
            zh_ok = (
                _contains_any(chinese, ["脚手架"])
                and _contains_any(chinese, ["移动"])
                and _contains_any(chinese, ["准备"])
            )
            vi_ok = (
                _contains_any(vietnamese, ["giàn giáo"])
                and _contains_any(vietnamese, ["di chuyển"])
                and _contains_any(vietnamese, ["chuẩn bị"])
            )

        elif concept == "check_floor_before_leveling":
            zh_ok = (
                _contains_any(chinese, ["地面", "地板"])
                and _contains_any(chinese, ["找平", "平整"])
                and _contains_any(chinese, ["检查", "确认"])
            )
            vi_ok = (
                _contains_any(vietnamese, ["sàn", "mặt sàn"])
                and _contains_any(vietnamese, ["san phẳng", "làm phẳng"])
                and _contains_any(vietnamese, ["kiểm tra"])
            )

        elif concept == "prepare_leveling_after_transport":
            zh_ok = (
                _contains_any(chinese, ["运输", "搬运"])
                and _contains_any(chinese, ["地面", "地板"])
                and _contains_any(chinese, ["找平", "平整"])
                and _contains_any(chinese, ["准备"])
            )
            vi_ok = (
                _contains_any(vietnamese, ["vận chuyển"])
                and _contains_any(vietnamese, ["sàn", "mặt sàn"])
                and _contains_any(vietnamese, ["san phẳng", "làm phẳng"])
                and _contains_any(vietnamese, ["chuẩn bị"])
            )

        elif concept in SEMANTIC_CONCEPTS:
            # All units are mandatory for a compound construction instruction.
            zh_ok = _all_source_clues(chinese, rules["zh"])
            vi_ok = _all_source_clues(vietnamese.lower(), [item.lower() for item in rules["vi"]])

        else:
            zh_ok = _contains_any(
                chinese,
                rules["zh"],
            )

            vi_ok = _contains_any(
                vietnamese,
                rules["vi"],
            )

        if not zh_ok:
            zh_missing.append(
                concept
            )

        if not vi_ok:
            vi_missing.append(
                concept
            )

        details.append({
            "concept": concept,
            "zh_ok": zh_ok,
            "vi_ok": vi_ok,
        })

    # 검사 개념 자체가 없는 경우를
    # "안전성 검증 성공"으로 오해하지 않도록 별도 표시
    checked = len(required) > 0

    return {
        "required_concepts": required,
        "checked": checked,

        "zh_safe": (
            len(zh_missing) == 0
            if checked
            else None
        ),

        "vi_safe": (
            len(vi_missing) == 0
            if checked
            else None
        ),

        "zh_missing": zh_missing,
        "vi_missing": vi_missing,

        "all_safe": (
            (
                len(zh_missing) == 0
                and len(vi_missing) == 0
            )
            if checked
            else None
        ),

        "details": details,
    }


if __name__ == "__main__":

    tests = [
        {
            "ko": "굴착 장비 후방에는 접근하지 마십시오.",
            "zh": "试着保持安全.",
            "vi": "Đừng tiếp cận các thiết bị đào phía sau.",
        },

        {
            "ko": "작업을 즉시 멈추십시오.",
            "zh": "现在就停止工作.",
            "vi": "Hãy dừng lại ngay lập tức.",
        },

        {
            "ko": "감전 위험이 있습니다.",
            "zh": "现在,我们有了风险.",
            "vi": "Có nguy cơ bị viêm.",
        },

        {
            "ko": (
                "환기 장치를 끄지 마십시오. "
                "환기 장치를 계속 작동하십시오."
            ),
            "zh": "让气候机关闭. 继续运行空气.",
            "vi": (
                "Đừng tắt máy thông gió. "
                "Hãy tiếp tục hoạt động máy thông gió."
            ),
        },

        {
            "ko": "작업용 발판 밑에는 자재 두지 마세요.",
            "zh": "没有任何东西可以在工作板下放.",
            "vi": "Đừng để tài liệu dưới bàn làm việc.",
        },
    ]

    for item in tests:

        result = validate_translation(
            item["ko"],
            item["zh"],
            item["vi"],
        )

        print("=" * 72)
        print("KO :", item["ko"])
        print("ZH :", item["zh"])
        print("VI :", item["vi"])
        print(
            "REQUIRED :",
            result["required_concepts"],
        )
        print(
            "CHECKED  :",
            result["checked"],
        )
        print(
            "ZH SAFE  :",
            result["zh_safe"],
        )
        print(
            "VI SAFE  :",
            result["vi_safe"],
        )
        print(
            "ZH MISS  :",
            result["zh_missing"],
        )
        print(
            "VI MISS  :",
            result["vi_missing"],
        )


# =========================================================
# EN/ZH/VI Triple Safety Guard
# Existing ZH/VI validate_translation() remains unchanged.
# =========================================================

ENGLISH_SAFETY_TERMS: dict[str, list[str]] = {
    "stop": ["stop", "halt", "cease"],
    "evacuate": ["evacuate", "leave", "exit"],
    "no_entry": [
        "do not enter", "don't enter",
        "do not approach", "keep out", "do not pass",
    ],
    "power_off": [
        "disconnect the power", "turn off the power",
        "cut off the power", "shut off the power",
    ],
    "electric_shock": ["electric shock", "electrocution"],
    "gas": ["harmful gas", "hazardous gas", "toxic gas"],
    "low_oxygen": [
        "low oxygen",
        "oxygen level is low",
        "oxygen concentration is low",
    ],
    "ventilation": [
        "ventilation", "ventilate",
        "air circulation", "fan",
    ],
    "keep_ventilation_on": [
        "do not turn off the ventilation",
        "keep the ventilation on",
        "keep the fan on",
    ],
    "keep_ventilation_running": [
        "keep the ventilation running",
        "keep the ventilation equipment running",
        "continue to operate the ventilation",
        "keep the fan on",
    ],
    "safe_distance": ["safe distance", "keep a distance"],
    "fall_protection": [
        "fall protection", "safety harness", "fall arrest",
    ],
    "helmet": ["safety helmet", "hard hat"],
    "remove_flammable": [
        "remove flammable", "remove combustible",
    ],
    "no_operation": [
        "do not operate", "must not operate",
        "without permission",
    ],
    "hands_off": [
        "do not put your hands",
        "keep your hands",
        "do not place your hands",
    ],
    "no_material_storage": [
        "do not store materials",
        "do not stack materials",
        "no material storage",
    ],
    "no_touch": ["do not touch", "don't touch"],
    "start_work_after_prepare": [
        "preparation", "start work",
    ],
    "concrete_pouring": [
        "pour concrete", "concrete pouring",
    ],
    "floor_leveling_start": [
        "level the floor", "floor leveling", "start leveling",
    ],
    "cement_wall_coating_start": [
        "cement paste", "wall", "start",
    ],
    "material_move_to_wall": [
        "materials", "wall", "move",
    ],
    "clear_path_after_transport": [
        "transport", "path", "clear",
    ],
    "clear_area_for_concrete": [
        "concrete", "area", "clear",
    ],
    "prepare_before_concrete": [
        "concrete", "prepare",
    ],
    "prepare_before_formwork": [
        "formwork", "prepare",
    ],
    "prepare_before_scaffold_move": [
        "scaffold", "move", "prepare",
    ],
    "check_floor_before_leveling": [
        "floor", "level", "check",
    ],
    "prepare_leveling_after_transport": [
        "transport", "floor", "level", "prepare",
    ],
    "person_check": [
        "check", "person", "people", "anyone",
    ],
    "keep_clear": [
        "keep clear", "clear the area", "remove people",
    ],
}


def _english_concept_ok(
    concept: str,
    english: str,
) -> bool:

    text = english.lower()
    terms = ENGLISH_SAFETY_TERMS.get(concept, [])

    # 영어 규칙이 아직 정의되지 않은 기존 concept는
    # 기존 ZH/VI 판정을 깨뜨리지 않기 위해 통과시킨다.
    if not terms:
        return True

    if concept in {
        "start_work_after_prepare",
        "cement_wall_coating_start",
        "material_move_to_wall",
        "clear_path_after_transport",
        "clear_area_for_concrete",
        "prepare_before_concrete",
        "prepare_before_formwork",
        "prepare_before_scaffold_move",
        "check_floor_before_leveling",
        "prepare_leveling_after_transport",
    }:
        return all(term in text for term in terms)

    return _contains_any(text, terms)


def validate_translation_triple(
    korean_text: str,
    english: str,
    chinese: str,
    vietnamese: str,
) -> dict[str, Any]:

    # 기존 ZH/VI Guard를 그대로 재사용
    dual = validate_translation(
        korean_text,
        chinese,
        vietnamese,
    )

    checked = dual["checked"]

    en_missing = [
        concept
        for concept in dual["required_concepts"]
        if not _english_concept_ok(concept, english)
    ]

    details = []

    for item in dual["details"]:
        concept = item["concept"]
        details.append({
            **item,
            "en_ok": concept not in en_missing,
        })

    return {
        **dual,
        "en_safe":
            len(en_missing) == 0
            if checked else None,
        "en_missing": en_missing,
        "all_safe":
            (
                len(en_missing) == 0
                and len(dual["zh_missing"]) == 0
                and len(dual["vi_missing"]) == 0
            )
            if checked else None,
        "details": details,
    }
