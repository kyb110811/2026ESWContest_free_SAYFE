from __future__ import annotations

from typing import Any


SAFETY_FALLBACKS: dict[str, dict[str, str]] = {

 
    "stop": {
        "zh": "请立即停止作业。",
        "vi": "Hãy dừng công việc ngay lập tức.",
    },

    "evacuate": {
        "zh": "请立即撤离。",
        "vi": "Hãy sơ tán ngay lập tức.",
    },

    "no_entry": {
        "zh": "请勿进入或靠近危险区域。",
        "vi": "Không được vào hoặc tiếp cận khu vực nguy hiểm.",
    },

    "power_off": {
        "zh": "请切断电源。",
        "vi": "Hãy ngắt nguồn điện.",
    },

    
    "ventilation": {
        "zh": "请保持通风。",
        "vi": "Hãy duy trì thông gió.",
    },

    
    "keep_ventilation_on": {
        "zh": "请勿关闭通风设备。",
        "vi": "Không được tắt thiết bị thông gió.",
    },

    "keep_ventilation_running": {
        "zh": "请保持通风设备持续运行。",
        "vi": "Hãy giữ thiết bị thông gió hoạt động liên tục.",
    },

 
    "helmet": {
        "zh": "请佩戴安全帽。",
        "vi": "Hãy đội mũ bảo hộ.",
    },

  
    "gas": {
        "zh": "存在有害气体危险。",
        "vi": "Có nguy cơ khí có hại.",
    },

    
    "electric_shock": {
        "zh": "有触电危险。",
        "vi": "Có nguy cơ điện giật.",
    },

   
    "low_oxygen": {
        "zh": "氧气浓度过低。",
        "vi": "Nồng độ oxy quá thấp.",
    },

    "safe_distance": {
        "zh": "请保持安全距离。",
        "vi": "Hãy giữ khoảng cách an toàn.",
    },

   
    "fall_protection": {
        "zh": "请佩戴防坠落安全带。",
        "vi": "Hãy sử dụng dây an toàn chống rơi.",
    },

  
    "hands_off": {
        "zh": "请勿将手伸入危险部位。",
        "vi": "Không được đưa tay vào khu vực nguy hiểm.",
    },

   
    "remove_flammable": {
        "zh": "请清除周围的易燃物。",
        "vi": "Hãy loại bỏ vật liệu dễ cháy xung quanh.",
    },

   
    "no_operation": {
        "zh": "未经许可请勿操作设备。",
        "vi": "Không được vận hành thiết bị khi chưa được phép.",
    },

  
    "keep_clear": {
        "zh": "请清空该区域的人员和物品。",
        "vi": "Hãy đưa người và vật dụng ra khỏi khu vực này.",
    },

    
    "no_material_storage": {
        "zh": "请勿在该区域堆放材料。",
        "vi": "Không được để vật liệu trong khu vực này.",
    },

   
    "start_work_after_prepare": {
        "zh": "准备工作完成后，请开始工作。",
        "vi": "Sau khi hoàn tất công tác chuẩn bị, hãy bắt đầu công việc.",
    },

  
    "concrete_pouring": {
        "zh": "浇筑混凝土。",
        "vi": "Đổ bê tông.",
    },

    "floor_leveling_start": {
        "zh": "开始进行地面找平作业。",
        "vi": "Bắt đầu công việc san phẳng mặt sàn.",
    },

  
    "cement_wall_coating_start": {
        "zh": "开始在墙面涂抹水泥浆。",
        "vi": "Bắt đầu bôi hồ xi măng lên bề mặt tường.",
    },

    "material_move_to_wall": {
        "zh": "请将材料运送到墙体一侧。",
        "vi": "Hãy vận chuyển vật liệu đến phía tường.",
    },

  
    "clear_path_after_transport": {
        "zh": "材料运输完成后，请清理通道。",
        "vi": "Sau khi vận chuyển vật liệu xong, hãy dọn sạch lối đi.",
    },

   
    "clear_area_for_concrete": {
        "zh": "进行混凝土作业前，请清理作业区域周围。",
        "vi": "Trước khi thi công bê tông, hãy dọn khu vực xung quanh.",
    },

  
    "prepare_before_concrete": {
        "zh": "进行混凝土作业前，请完成作业准备。",
        "vi": "Trước khi thi công bê tông, hãy hoàn tất công tác chuẩn bị.",
    },

  
    "prepare_before_formwork": {
        "zh": "进行模板作业前，请完成作业准备。",
        "vi": "Trước khi làm công tác cốp pha, hãy hoàn tất công tác chuẩn bị.",
    },

  
    "prepare_before_scaffold_move": {
        "zh": "移动脚手架前，请完成作业准备。",
        "vi": "Trước khi di chuyển giàn giáo, hãy hoàn tất công tác chuẩn bị.",
    },

  
    "check_floor_before_leveling": {
        "zh": "进行地面找平前，请检查地面状况。",
        "vi": "Trước khi san phẳng mặt sàn, hãy kiểm tra tình trạng sàn.",
    },

    "prepare_leveling_after_transport": {
        "zh": "材料运输完成后，请准备地面找平作业。",
        "vi": "Sau khi vận chuyển vật liệu xong, hãy chuẩn bị công việc san phẳng mặt sàn.",
    },

  
    "person_check": {
        "zh": "请确认该区域是否有人。",
        "vi": "Hãy kiểm tra xem có người trong khu vực hay không.",
    },

    "no_touch": {
        "zh": "请勿触摸。",
        "vi": "Không được chạm vào.",
    },
}


def _normalize_sentence_end(text: str) -> str:
    text = text.strip()

    if not text:
        return ""

    if text[-1] not in ".!?。！？":
        text += "."

    return text



COMPOUND_FALLBACKS: dict[str, dict[str, str]] = {
    "excavator_moving_keep_out": {
        "zh": "挖掘机正在移动。请勿进入作业半径内。",
        "vi": "Máy xúc đang di chuyển. Không được vào trong bán kính làm việc.",
    },
    "excavator_rear_keep_out": {
        "zh": "请勿靠近挖掘机后方。",
        "vi": "Không được tiếp cận phía sau máy xúc.",
    },
    "ventilate_before_entry": {
        "zh": "进入密闭空间前，请充分通风。",
        "vi": "Trước khi vào không gian kín, hãy thông gió đầy đủ.",
    },
    "gas_oxygen_measurement": {
        "zh": "作业前，请测量氧气浓度和有害气体浓度。",
        "vi": "Trước khi làm việc, hãy đo nồng độ oxy và khí độc.",
    },
    "gas_leak_evacuate_safe_area": {
        "zh": "怀疑发生气体泄漏。请撤离到安全区域。",
        "vi": "Nghi có rò rỉ khí. Hãy sơ tán đến khu vực an toàn.",
    },
    "electric_shock_power_off_before_work": {
        "zh": "有触电危险。切断电源后再作业。",
        "vi": "Có nguy cơ điện giật. Chỉ làm việc sau khi ngắt nguồn điện.",
    },
    "welding_remove_flammable": {
        "zh": "焊接作业前，请清除周围的易燃物。",
        "vi": "Trước khi hàn, hãy loại bỏ vật liệu dễ cháy xung quanh.",
    },
    "formwork_prepare_recheck_before_pouring": {
        "zh": "浇筑混凝土前，请再次检查模板作业准备。",
        "vi": "Trước khi đổ bê tông, hãy kiểm tra lại công tác chuẩn bị cốp pha.",
    },
    "material_transport_helmet_passage_move": {
        "zh": "运输材料的工人请佩戴安全帽，并经通道移动。",
        "vi": "Công nhân vận chuyển vật liệu phải đội mũ bảo hộ và di chuyển qua lối đi.",
    },
    "formwork_dismantle_scaffold_person_check": {
        "zh": "开始拆除模板时，请确认脚手架下方无人。",
        "vi": "Khi bắt đầu tháo dỡ cốp pha, hãy kiểm tra không có người dưới giàn giáo.",
    },
    "floor_leveling_no_pass": {
        "zh": "地面找平完成前，请勿从此处通行。",
        "vi": "Không được đi qua đây cho đến khi hoàn thành san phẳng mặt sàn.",
    },
    "formwork_dismantle_clear_below": {
        "zh": "开始拆除模板时，请清除下方区域的人员和物品。",
        "vi": "Khi bắt đầu tháo dỡ cốp pha, hãy dọn người và vật dụng khỏi khu vực phía dưới.",
    },
    "scaffold_helmet_check_before_climb": {
        "zh": "攀登脚手架前，请确认已佩戴安全帽。",
        "vi": "Trước khi leo lên giàn giáo, hãy kiểm tra đã đội mũ bảo hộ.",
    },
    "ventilation_device_start_for_gas": {
        "zh": "由于存在气体危险，请先启动通风设备。",
        "vi": "Vì có nguy cơ khí, hãy khởi động thiết bị thông gió trước.",
    },
    "keep_ventilation_until_work_end": {
        "zh": "请让通风设备持续运行至作业结束。",
        "vi": "Hãy giữ thiết bị thông gió hoạt động liên tục cho đến khi kết thúc công việc.",
    },
    "check_floor_before_leveling_profile": {
        "zh": "进行地面找平前，请检查地面状况。",
        "vi": "Trước khi san phẳng mặt sàn, hãy kiểm tra tình trạng sàn.",
    },
    "cement_coating_do_not_touch_wall": {
        "zh": "墙面正在涂抹水泥浆，请勿触摸墙面。",
        "vi": "Đang bôi hồ xi măng lên tường, không được chạm vào tường.",
    },
}


def apply_safety_fallback(
    chinese: str,
    vietnamese: str,
    zh_missing: list[str],
    vi_missing: list[str],
    source_text: str = "",
) -> dict[str, Any]:
   

    final_zh = chinese.strip()
    final_vi = vietnamese.strip()

    zh_added: list[dict[str, str]] = []
    vi_added: list[dict[str, str]] = []

    # A compound fallback replaces the whole failed unit.  Do not append an
    # unrelated fragment to a defective NLLB sentence.
    compound_ids = [
        concept for concept in set(zh_missing + vi_missing)
        if concept in COMPOUND_FALLBACKS
    ]
    if compound_ids:
        concept = compound_ids[0]
        if zh_missing:
            final_zh = COMPOUND_FALLBACKS[concept]["zh"]
            zh_added.append({"concept": concept, "text": final_zh})
        if vi_missing:
            final_vi = COMPOUND_FALLBACKS[concept]["vi"]
            vi_added.append({"concept": concept, "text": final_vi})
        return {
            "zh": final_zh, "vi": final_vi,
            "zh_added": zh_added, "vi_added": vi_added,
            "fallback_used": bool(zh_added or vi_added),
        }

  
    for concept in zh_missing:

        rule = SAFETY_FALLBACKS.get(concept)

        if not rule:
            continue

        fallback_text = rule.get("zh", "").strip()

        if not fallback_text:
            continue

        final_zh = (
            _normalize_sentence_end(final_zh)
            + " "
            + fallback_text
        ).strip()

        zh_added.append({
            "concept": concept,
            "text": fallback_text,
        })


    for concept in vi_missing:

        rule = SAFETY_FALLBACKS.get(concept)

        if not rule:
            continue

        fallback_text = rule.get("vi", "").strip()

        if not fallback_text:
            continue

        final_vi = (
            _normalize_sentence_end(final_vi)
            + " "
            + fallback_text
        ).strip()

        vi_added.append({
            "concept": concept,
            "text": fallback_text,
        })

    return {
        "zh": final_zh,
        "vi": final_vi,
        "zh_added": zh_added,
        "vi_added": vi_added,
        "fallback_used": bool(
            zh_added or vi_added
        ),
    }



ENGLISH_SAFETY_FALLBACKS: dict[str, str] = {
    "stop": "Stop work immediately.",
    "evacuate": "Evacuate immediately.",
    "no_entry": "Do not enter or approach the hazardous area.",
    "power_off": "Disconnect the power supply.",
    "electric_shock": "There is a risk of electric shock.",
    "gas": "There is a risk of hazardous gas.",
    "low_oxygen": "The oxygen concentration is too low.",
    "ventilation": "Maintain ventilation.",
    "keep_ventilation_on": "Do not turn off the ventilation equipment.",
    "keep_ventilation_running": "Keep the ventilation equipment running.",
    "safe_distance": "Keep a safe distance.",
    "fall_protection": "Wear fall-protection safety equipment.",
    "helmet": "Wear a safety helmet.",
    "remove_flammable": "Remove flammable materials from the surrounding area.",
    "no_operation": "Do not operate the equipment without permission.",
    "hands_off": "Do not put your hands into hazardous parts.",
    "keep_clear": "Keep people and objects clear of this area.",
    "no_material_storage": "Do not store materials in this area.",
    "no_touch": "Do not touch it.",
    "start_work_after_prepare": "Complete the preparation, then start work.",
    "concrete_pouring": "Pour concrete.",
    "floor_leveling_start": "Start leveling the floor.",
    "cement_wall_coating_start": "Start applying cement paste to the wall.",
    "material_move_to_wall": "Move the materials to the wall.",
    "clear_path_after_transport": "After transport, clear the path.",
    "clear_area_for_concrete": "Clear the area around the concrete work.",
    "prepare_before_concrete": "Prepare before concrete work.",
    "prepare_before_formwork": "Prepare before formwork work.",
    "prepare_before_scaffold_move": "Prepare before moving the scaffold.",
    "check_floor_before_leveling": "Check the floor before leveling it.",
    "prepare_leveling_after_transport": "After transport, prepare to level the floor.",
    "person_check": "Check whether there are people in the area.",
}


def apply_safety_fallback_triple(
    english: str,
    chinese: str,
    vietnamese: str,
    en_missing: list[str],
    zh_missing: list[str],
    vi_missing: list[str],
) -> dict[str, Any]:
    """Return language-specific fallback text for the additive triple path."""
    dual = apply_safety_fallback(
        chinese=chinese,
        vietnamese=vietnamese,
        zh_missing=zh_missing,
        vi_missing=vi_missing,
    )
    final_en = english.strip()
    en_added: list[dict[str, str]] = []
    for concept in en_missing:
        fallback_text = ENGLISH_SAFETY_FALLBACKS.get(concept, "").strip()
        if not fallback_text:
            continue
        final_en = (_normalize_sentence_end(final_en) + " " + fallback_text).strip()
        en_added.append({"concept": concept, "text": fallback_text})
    return {
        "en": final_en,
        "zh": dual["zh"],
        "vi": dual["vi"],
        "en_added": en_added,
        "zh_added": dual["zh_added"],
        "vi_added": dual["vi_added"],
        "fallback_used": bool(en_added) or dual["fallback_used"],
    }



if __name__ == "__main__":

    tests = [
        {
            "zh": "试着保持安全.",
            "vi": "Đừng tiếp cận các thiết bị đào phía sau.",
            "zh_missing": ["no_entry"],
            "vi_missing": [],
        },
        {
            "zh": "让气候机关闭. 继续运行空气.",
            "vi": (
                "Đừng tắt máy thông gió. "
                "Hãy tiếp tục hoạt động máy thông gió."
            ),
            "zh_missing": ["keep_ventilation_on"],
            "vi_missing": [],
        },
        {
            "zh": "现在,我们有了风险.",
            "vi": "Có nguy cơ bị viêm.",
            "zh_missing": ["electric_shock"],
            "vi_missing": ["electric_shock"],
        },
    ]

    for test in tests:

        result = apply_safety_fallback(
            chinese=test["zh"],
            vietnamese=test["vi"],
            zh_missing=test["zh_missing"],
            vi_missing=test["vi_missing"],
        )

        print("=" * 70)
        print("ZH :", result["zh"])
        print("VI :", result["vi"])
        print("ZH ADDED :", result["zh_added"])
        print("VI ADDED :", result["vi_added"])
        print("USED :", result["fallback_used"])
