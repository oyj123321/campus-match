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
# 文案气质：敢把在乎说清楚、独立仍愿交心、苦后留余韵、靠近不入账（非引用任何私人原文）
PERSONALITIES = {
    "ESCP": {
        "name": "守护者型",
        "subtitle": "靠近不是冲动，是愿意把在乎说清楚、放长久",
        "traits": ["喜欢用行动证明「我在」", "愿意走进关系，也渴望被认真接住", "宁可慢一点谈明白，也不想轻轻带过"],
        "strength": "把稳定变成可感知的安全感，让对方不必猜。",
        "match_tip": "会回应你的认真、也敢把喜欢说出口的人。",
    },
    "ESCA": {
        "name": "开明领航型",
        "subtitle": "一边把关系经营清楚，一边邀请对方看见更远的风景",
        "traits": ["表达直接，不爱绕弯", "日子有节奏，却留得下意外", "对未来开放，也肯并肩商量"],
        "strength": "给方向，也给余地——让靠近变成一起长大。",
        "match_tip": "独立却肯同行的人：跟得上你，也不怕新的一页。",
    },
    "EFCP": {
        "name": "阳光筑巢型",
        "subtitle": "轻松地靠近，却把「以后」放在心上",
        "traits": ["情感外放，能把气氛焐热", "日常随性，讨厌被规矩拴住", "承诺这件事，你偏稳健"],
        "strength": "让相处像日光：暖、松，却看得见明天。",
        "match_tip": "能一起玩、也肯谈以后的人——别太闷，也别太飘。",
    },
    "EFCA": {
        "name": "浪漫牧者型",
        "subtitle": "热烈可以自由，喜欢值得被过成一段路",
        "traits": ["表达热烈，藏不住喜欢", "生活灵活，讨厌一成不变", "亲密与出走，可以同时发生"],
        "strength": "把平凡日子点燃成记得住的瞬间。",
        "match_tip": "同样敢靠近、敢尝试的人——别用管束浇灭火花。",
    },
    "ESOP": {
        "name": "灯塔型",
        "subtitle": "愿意照亮你，也守着自己的岸",
        "traits": ["表达清晰，少猜忌", "生活有序，心里有谱", "亲近里仍要边界与呼吸"],
        "strength": "靠谱而不吞没——靠近有光，分开也不慌。",
        "match_tip": "尊重你节奏的人：认真靠近，也能安静各自站立。",
    },
    "ESOA": {
        "name": "自由先驱型",
        "subtitle": "热烈地喜欢，也热烈地做完整的自己",
        "traits": ["情感外放，带动场", "秩序感在，却拒绝被绑死", "独立开放，并肩比占有更吸引你"],
        "strength": "把热情变成同行，而不是吞并。",
        "match_tip": "同样完整的人——一起走，而不是互相消融。",
    },
    "EFOP": {
        "name": "热心管家型",
        "subtitle": "对在乎的人很热络，也留得下自己的空",
        "traits": ["表达外放，热情来得快", "日常不拘小节", "亲近里仍保有独立", "大事上偏稳，不轻易甩手"],
        "strength": "热情可感，却不黏到窒息。",
        "match_tip": "懂你热一阵、也要自己空间的人。",
    },
    "EFOA": {
        "name": "春风旅人型",
        "subtitle": "喜欢燃到哪儿，脚步就跟到哪儿",
        "traits": ["表达热烈", "随性自由", "独立自主", "开放冒险，怕被拴住"],
        "strength": "把关系变成共同的出走与呼吸。",
        "match_tip": "爱玩、不爱束缚的人——并肩，而不是互相拴。",
    },
    "ISCP": {
        "name": "静谧港湾型",
        "subtitle": "话不多，却想把安稳悄悄递到你手里",
        "traits": ["情感含蓄，慢热却真", "生活有序，心里沉", "渴望深度靠近", "态度稳健，不爱闹"],
        "strength": "用安静的陪伴让人落地。",
        "match_tip": "有耐心读你沉默、也敢邀你聊聊的人。",
    },
    "ISCA": {
        "name": "内秀构建型",
        "subtitle": "内心认真，向外慢慢打开世界",
        "traits": ["含蓄但句句真心", "做事有章法", "重视亲密，也肯一起长大", "对变化开放，不慌"],
        "strength": "把关系盖成可以长期住的地方。",
        "match_tip": "愿慢慢走进你，也带你看见新风景的人。",
    },
    "IFCP": {
        "name": "温柔守望型",
        "subtitle": "柔软随性，却把承诺藏在心里最稳的地方",
        "traits": ["细腻内敛，感受很深", "生活松弛，不赶场", "渴望被靠近、被确认", "大事上偏保守，怕伤人"],
        "strength": "用柔软接住情绪，让对方敢卸下防备。",
        "match_tip": "稳定且会主动确认关系的人——别让你一直猜。",
    },
    "IFCA": {
        "name": "诗意栖居型",
        "subtitle": "安静地感受，开放地生活；苦过之后，仍信余韵",
        "traits": ["内敛细腻，捕捉微小温度", "随性，不爱非黑即白", "重视亲密氛围", "心态开放，留得下转弯"],
        "strength": "把日常过出可回味的层次。",
        "match_tip": "懂氛围、不催促的人——一起慢慢展开。",
    },
    "ISOP": {
        "name": "沉思者型",
        "subtitle": "先想清楚，再决定要不要把心递出去",
        "traits": ["情感内敛，厌恶轻飘", "生活有序", "边界清晰", "态度稳健，宁可慢不可悔"],
        "strength": "清醒地靠近，减少冲动的伤。",
        "match_tip": "尊重你思考时间、不逼表态的人。",
    },
    "ISOA": {
        "name": "孤岛哲人型",
        "subtitle": "独立是底色；开放，是你选择后的邀请",
        "traits": ["含蓄，话少但重", "有秩序的自我世界", "很需要自主", "对人生持开放，却不随便交付"],
        "strength": "自我完整，不靠关系填空——靠近才更真。",
        "match_tip": "同样完整、能并肩谈世界的人。",
    },
    "IFOP": {
        "name": "花园隐士型",
        "subtitle": "守着自己的小世界，也守着一份不吵闹的踏实",
        "traits": ["内敛，不抢声量", "随性，按自己的节奏呼吸", "独立，却并非冷漠", "稳健，珍惜真正被接住的瞬间"],
        "strength": "不打扰别人，也不愿被廉价黏合。",
        "match_tip": "轻声靠近、愿认真谈谈的人——不侵入，也不假装看不见你。",
    },
    "IFOA": {
        "name": "星尘游吟型",
        "subtitle": "安静自由，心里装着远方；也等一个愿并肩的灵魂",
        "traits": ["情感内敛，长于感受", "生活随性，走走停停", "独立完整", "开放冒险，却怕一厢情愿的重量"],
        "strength": "给关系留下想象与呼吸，也留下可以说清楚的缝隙。",
        "match_tip": "不强迫黏连、愿一起出走、也敢把心里话说开的人。",
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
