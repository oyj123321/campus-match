"""
恋爱人格报告（冷启动：交卷立刻可分享）

4 维 × 2 极 → 16 型；纯规则，无 LLM。
结果写入 users.mbti_json（kind=love_personality）。
"""

from __future__ import annotations

DIM_META = {
    "expression": {"high": ("E", "外放热烈"), "low": ("I", "内敛含蓄"), "label": "情感表达"},
    "rhythm": {"high": ("S", "结构秩序"), "low": ("F", "随性自由"), "label": "生活节奏"},
    "boundary": {"high": ("C", "亲密融合"), "low": ("O", "独立自主"), "label": "关系边界"},
    "risk": {"high": ("P", "稳健保守"), "low": ("A", "开放冒险"), "label": "风险态度"},
}

# 16 型：code → 名称、副标题、特质、优势、适合谁
PERSONALITIES = {
    "ESCP": {
        "name": "守护者型",
        "subtitle": "你想要一个可以依靠的肩膀，而不是一场冒险的旅程",
        "traits": ["用行动把在乎落到实处", "关系里愿意靠近、也期待被接住", "更看重长期承诺而非一时激情"],
        "strength": "稳定付出，让对方感到「有人在」。",
        "match_tip": "感性、愿意回应你的人——能接住你的认真，也给你一点仪式感。",
    },
    "ESCA": {
        "name": "开明领航型",
        "subtitle": "认真经营关系，也愿意一起看见更大的世界",
        "traits": ["表达直接，推进感强", "生活有节奏，但不死板", "对未来持开放态度"],
        "strength": "能把关系带向清晰方向，同时留出探索空间。",
        "match_tip": "独立又愿意同行的人——既跟得上你的节奏，也不怕新计划。",
    },
    "EFCP": {
        "name": "阳光筑巢型",
        "subtitle": "松弛地靠近，认真地成家",
        "traits": ["情感外放，气氛感强", "日常随性，讨厌过度规矩", "对承诺偏稳健"],
        "strength": "让关系轻松有温度，又不失长期感。",
        "match_tip": "能一起玩、也谈得拢以后的人——别太闷，也别太飘。",
    },
    "EFCA": {
        "name": "浪漫牧者型",
        "subtitle": "热烈、自由，想把喜欢过成一场旅途",
        "traits": ["表达热烈", "生活灵活多变", "亲密与冒险可以并存"],
        "strength": "点燃日常，把相处变成值得回忆的体验。",
        "match_tip": "同样外放、敢尝试的人——别用过度管束浇灭热情。",
    },
    "ESOP": {
        "name": "灯塔型",
        "subtitle": "给你稳定的光，也保留自己的岸",
        "traits": ["表达清晰", "生活有序", "需要个人空间与清晰边界"],
        "strength": "靠谱且边界清楚，减少消耗型纠缠。",
        "match_tip": "尊重你节奏的人——靠近时认真，分开时也不焦虑。",
    },
    "ESOA": {
        "name": "自由先驱型",
        "subtitle": "热烈地喜欢，也热烈地做自己",
        "traits": ["情感外放", "秩序感偏强", "独立、开放、不喜欢被绑死"],
        "strength": "带动气氛，同时守住自我。",
        "match_tip": "同样独立的人——并肩而非吞并。",
    },
    "EFOP": {  # E F O P — 外放随性独立保守：热心管家/亲密但留白
        "name": "热心管家型",
        "subtitle": "对喜欢的人很热络，生活随性，边界也在",
        "traits": ["表达外放", "日常不拘小节", "亲近里保留独立", "对大事偏稳"],
        "strength": "热情但不黏到窒息。",
        "match_tip": "能接受你「热一阵、也要自己空间」的人。",
    },
    "EFOA": {
        "name": "春风旅人型",
        "subtitle": "走到哪，喜欢就燃到哪",
        "traits": ["表达热烈", "随性自由", "独立自主", "开放冒险"],
        "strength": "把关系变成共同探险。",
        "match_tip": "爱玩、不爱束缚的人——一起走，而不是互相拴。",
    },
    "ISCP": {
        "name": "静谧港湾型",
        "subtitle": "不吵不闹，却想把安全感给你",
        "traits": ["情感含蓄", "生活有序", "渴望深度融合", "态度稳健"],
        "strength": "深度陪伴，让人安静下来。",
        "match_tip": "温柔有耐心的人——读得懂你的慢热。",
    },
    "ISCA": {
        "name": "内秀构建型",
        "subtitle": "内心认真，向外慢慢打开世界",
        "traits": ["含蓄但真心", "做事有章法", "重视亲密", "对变化开放"],
        "strength": "把关系盖成可长期住的结构。",
        "match_tip": "愿意慢慢走进你世界、也带你看新风景的人。",
    },
    "IFCP": {
        "name": "温柔守望型",
        "subtitle": "柔软、随性，却把承诺放在心里",
        "traits": ["情感细腻内敛", "生活松弛", "渴望靠近", "大事上偏保守"],
        "strength": "用柔软接住对方的情绪。",
        "match_tip": "稳定且会主动确认关系的人——别让你一直猜。",
    },
    "IFCA": {
        "name": "诗意栖居型",
        "subtitle": "安静地感受，开放地生活",
        "traits": ["内敛细腻", "随性", "重视亲密氛围", "心态开放"],
        "strength": "把日常过出一点诗意。",
        "match_tip": "懂氛围、不催促的人——一起慢慢展开。",
    },
    "ISOP": {
        "name": "沉思者型",
        "subtitle": "先想清楚，再决定要不要靠近",
        "traits": ["情感内敛", "生活有序", "边界清晰", "态度稳健"],
        "strength": "理性清醒，减少冲动伤害。",
        "match_tip": "尊重思考时间、不逼表态的人。",
    },
    "ISOA": {
        "name": "孤岛哲人型",
        "subtitle": "独立是底色，开放是选择",
        "traits": ["含蓄", "有秩序", "很需要自主", "对人生持开放态度"],
        "strength": "自我完整，不靠关系填空。",
        "match_tip": "同样完整、能并肩讨论世界的人。",
    },
    "IFOP": {
        "name": "花园隐士型",
        "subtitle": "有自己的小世界，也守着一份踏实",
        "traits": ["内敛", "随性", "独立", "稳健"],
        "strength": "不打扰别人，也不愿被过度打扰。",
        "match_tip": "轻声靠近、不侵入你节奏的人。",
    },
    "IFOA": {
        "name": "星尘游吟型",
        "subtitle": "安静，自由，心里装着远方",
        "traits": ["情感内敛", "生活随性", "独立", "开放冒险"],
        "strength": "给关系留下想象与呼吸。",
        "match_tip": "不强迫黏连、愿一起出走的人。",
    },
}

# 修正：字母组合是 E/I + S/F + C/O + P/A
# EFOP = E+F+O+P, EFOA = E+F+O+A
# I already have EFOP/EFOA and IFOP/IFOA
# Missing from first draft: used EFOP instead of wrong "EFCP 变体"

assert len(PERSONALITIES) == 16


def _norm_answers(answers):
    out = {}
    for k, v in (answers or {}).items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            continue
    return out


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


def _scale(answers, qid, default=3):
    try:
        return max(1, min(5, int(answers.get(qid, default))))
    except (TypeError, ValueError):
        return default


def _multi(answers, qid):
    raw = answers.get(qid) or []
    return list(raw) if isinstance(raw, (list, tuple)) else []


def _scale_to_100(v, invert=False):
    """量表 1–5 → 0–100；invert 时 1 为高分。"""
    v = max(1, min(5, int(v)))
    if invert:
        return (6 - v - 1) * 25.0  # 1→100, 5→0
    return (v - 1) * 25.0  # 1→0, 5→100


def compute_dimension_scores(answers):
    """
    高分含义：
      expression↑ = 外放 E
      rhythm↑ = 秩序 S
      boundary↑ = 亲密 C
      risk↑ = 保守 P
    计分按问卷实际左右端校准（非照搬有误的附录方向）。
    """
    a = _norm_answers(answers)

    # 情感表达：直接说爱/拥抱↑；浪漫(左)↑；希望陪伴(左)↑
    love = _multi(a, 18)
    expr = 50.0
    if "直接说爱与赞美" in love:
        expr += 25
    if "拥抱牵手等接触" in love:
        expr += 12
    if "准备礼物惊喜" in love:
        expr -= 10
    if "帮对方做事" in love:
        expr -= 20
    expr_parts = [
        _clamp(expr),
        _scale_to_100(_scale(a, 22), invert=True),  # 左浪漫 → 外放
        _scale_to_100(_scale(a, 21), invert=True),  # 左陪伴 → 外放
    ]
    expression = sum(expr_parts) / len(expr_parts)

    # 生活节奏：早睡/整洁/规划/户外 → 秩序
    rhythm_parts = [
        _scale_to_100(_scale(a, 9), invert=True),   # 左早
        _scale_to_100(_scale(a, 12), invert=True),  # 左整洁
        _scale_to_100(_scale(a, 16), invert=True),  # 左规划
        _scale_to_100(_scale(a, 29), invert=True),  # 左户外→秩序（按 spec）
    ]
    rhythm = sum(rhythm_parts) / len(rhythm_parts)

    # 关系边界：优先伴侣/少独处/不介意社交 → 亲密
    boundary_parts = [
        _scale_to_100(_scale(a, 7), invert=True),   # 左优先伴侣
        _scale_to_100(_scale(a, 19), invert=True),  # 左不需独处 → 亲密
        _scale_to_100(_scale(a, 20), invert=True),  # 左不介意 → 亲密
    ]
    boundary = sum(boundary_parts) / len(boundary_parts)

    # 风险态度：储蓄/必须结婚/一定要孩子 → 保守
    risk_parts = [
        _scale_to_100(_scale(a, 4), invert=True),
        _scale_to_100(_scale(a, 5), invert=True),
        _scale_to_100(_scale(a, 6), invert=True),
    ]
    risk = sum(risk_parts) / len(risk_parts)

    return {
        "expression": _clamp(expression),
        "rhythm": _clamp(rhythm),
        "boundary": _clamp(boundary),
        "risk": _clamp(risk),
    }


def _polarize(scores):
    dims = {}
    code_letters = []
    for key in ("expression", "rhythm", "boundary", "risk"):
        score = scores[key]
        meta = DIM_META[key]
        if score >= 50:
            letter, pole = meta["high"]
        else:
            letter, pole = meta["low"]
        dims[key] = {
            "letter": letter,
            "pole": pole,
            "score": round(score, 1),
            "label": meta["label"],
        }
        code_letters.append(letter)
    return "".join(code_letters), dims


def build_love_personality(answers):
    scores = compute_dimension_scores(answers)
    code, dims = _polarize(scores)
    profile = PERSONALITIES.get(code) or PERSONALITIES["ISCP"]

    return {
        "kind": "love_personality",
        "code": code,
        "name": profile["name"],
        "subtitle": profile["subtitle"],
        "dimensions": dims,
        "traits": list(profile["traits"]),
        "strength": profile["strength"],
        "match_tip": profile["match_tip"],
        "disclaimer": "本结果由恋爱问卷规则生成，仅供娱乐与破冰，不构成心理诊断，也不代表匹配算法结论。",
        "source": "love_personality_v1",
        # 兼容旧匹配页字段名（便于渐进替换）
        "type": code,
        "label": profile["name"],
        "summary": profile["subtitle"],
    }
