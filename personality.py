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
# 文案气质按四维拉开：E 口语热、I 克制诗意；勿让 16 型共用同一句式骨架
PERSONALITIES = {
    "ESCP": {
        "name": "守护者型",
        "subtitle": "喜欢就说清楚，然后用日子把你守住",
        "traits": ["心里有事会摊开讲，不爱让人猜", "日子有章法，承诺更不随便开出口", "想走进你，也想被你认真接住"],
        "strength": "把「我在」变成摸得到的安全感，对方不必猜。",
        "match_tip": "敢接住你认真、也会把喜欢说出口的人。",
    },
    "ESCA": {
        "name": "开明领航型",
        "subtitle": "路我帮你理清楚——风景嘛，咱们一起冲！",
        "traits": ["说话直接，绕弯子太累", "日子有节奏，却随时准备翻新页", "亲密要并肩商量，也要敢往前闯"],
        "strength": "给你方向，也给你余量：靠近变成一起长大。",
        "match_tip": "跟得上你、不怕开新局的人——独立，但肯并肩。",
    },
    "EFCP": {
        "name": "阳光筑巢型",
        "subtitle": "靠近可以很轻松——「以后」这件事，我可当真了！",
        "traits": ["一来就能把气氛焐热，情绪藏不住", "日常随性，最烦被规矩拴死", "玩归玩，说到承诺你偏稳"],
        "strength": "相处像晒太阳：暖、松，明天还看得见。",
        "match_tip": "能一起疯、也肯谈以后的人——别闷成石头，也别飘成风。",
    },
    "EFCA": {
        "name": "浪漫牧者型",
        "subtitle": "喜欢你就藏不住！别走远——这颗心是热的，也想跟你到处晃",
        "traits": ["感情来了嘴比脑子快半拍", "日子要活，一成不变会闷出火星", "想黏着你，也想拉着你去试新的"],
        "strength": "把平淡日子点成记得住的火花。",
        "match_tip": "同样敢靠近、敢试的人——别用管束把火花浇灭。",
    },
    "ESOP": {
        "name": "灯塔型",
        "subtitle": "我可以照亮你，也请让我守好自己的岸",
        "traits": ["话讲清楚，少让人猜忌", "生活有谱，心里有地图", "亲近可以，边界和呼吸也要"],
        "strength": "靠谱却不吞没——靠近有光，分开也不慌。",
        "match_tip": "尊重你节奏的人：认真靠近，也能安静各自站立。",
    },
    "ESOA": {
        "name": "自由先驱型",
        "subtitle": "喜欢你，热烈；做自己，也热烈——少一边都不行！",
        "traits": ["一进场就能带起气场", "有秩序感，但绝不要被绑死", "并肩比占有更让你心动"],
        "strength": "把热情变成同行，不是吞并。",
        "match_tip": "同样完整的人——一起走，别互相化掉。",
    },
    "EFOP": {
        "name": "热心管家型",
        "subtitle": "在乎你的时候会很热络——但请给我留一块自己的空！",
        "traits": ["热情来得快，关心说得出、做得动", "日常不拘小节，讨厌被管太细", "亲近可以，独立也得在", "大事上偏稳，不轻易甩手"],
        "strength": "热情摸得到，却不会黏到喘不过气。",
        "match_tip": "懂你热一阵、也要自己空间的人。",
    },
    "EFOA": {
        "name": "春风旅人型",
        "subtitle": "喜欢燃到哪儿，脚步就跟到哪儿——别拴我，来并肩啊！",
        "traits": ["心里一热就说出口", "随性自由，日程表别太硬", "独立得很，并肩比占有更香", "爱冒险，最怕被拴成宠物"],
        "strength": "让关系变成共同出走，也共同呼吸。",
        "match_tip": "爱玩、不爱笼子的人——并肩走，别互相拴。",
    },
    "ISCP": {
        "name": "静谧港湾型",
        "subtitle": "话不多，却想把安稳悄悄递到你手里",
        "traits": ["慢热，开口少，心意真", "日子沉、有序，不爱起哄", "渴望深度靠近，而非热闹凑合", "态度稳健，宁可静也不闹"],
        "strength": "用安静的陪伴让人落地。",
        "match_tip": "有耐心读你沉默、也敢轻轻邀你聊聊的人。",
    },
    "ISCA": {
        "name": "内秀构建型",
        "subtitle": "心里认真搭着，世界才一点点向外打开",
        "traits": ["含蓄，但每句都落得住", "做事有章法，关系也想盖得牢", "重视亲密，也肯一起慢慢长大", "对变化开放，却不慌不抢"],
        "strength": "把关系盖成可以长期住的地方。",
        "match_tip": "愿慢慢走进你，也愿意带你看见新风景的人。",
    },
    "IFCP": {
        "name": "温柔守望型",
        "subtitle": "柔软随性，承诺却藏在心里最稳的一格",
        "traits": ["细腻内敛，感受比话多", "生活松着走，不赶场", "渴望被靠近、被确认", "大事上偏保守，怕伤到人"],
        "strength": "用柔软接住情绪，让对方敢卸下防备。",
        "match_tip": "稳定且会主动确认关系的人——别让你一直猜。",
    },
    "IFCA": {
        "name": "诗意栖居型",
        "subtitle": "安静地感受，开放地生活；苦过之后，仍信余韵",
        "traits": ["内敛细腻，捕捉微小温度", "随性，不爱非黑即白", "重视亲密氛围多过表象热闹", "心态开放，留得下转弯"],
        "strength": "把日常过出可回味的层次。",
        "match_tip": "懂氛围、不催促的人——一起慢慢展开。",
    },
    "ISOP": {
        "name": "沉思者型",
        "subtitle": "先想清楚，再决定要不要把心递出去",
        "traits": ["情感内敛，厌恶轻飘的喜欢", "生活有序，心思也要排齐", "边界清晰，靠近需要理由", "宁可慢，不可悔"],
        "strength": "清醒地靠近，少一些冲动留下的伤。",
        "match_tip": "尊重你思考时间、不逼表态的人。",
    },
    "ISOA": {
        "name": "孤岛哲人型",
        "subtitle": "独立是底色；开放，是你选过之后的邀请",
        "traits": ["话少，落下来却重", "守着有秩序的自我世界", "自主感很强，容不下被填满", "对人生开放，对交付仍谨慎"],
        "strength": "自我完整，不靠关系填空——靠近才更真。",
        "match_tip": "同样完整、能并肩谈世界的人。",
    },
    "IFOP": {
        "name": "花园隐士型",
        "subtitle": "守着自己的小世界，也守着一份不吵闹的踏实",
        "traits": ["不抢声量，也不急着被看见", "随性呼吸，按自己的节奏活", "独立，却并非冷漠", "稳健，珍惜真正被接住的瞬间"],
        "strength": "不打扰别人，也不愿被廉价黏合。",
        "match_tip": "轻声靠近、愿认真谈谈的人——不侵入，也不假装看不见你。",
    },
    "IFOA": {
        "name": "星尘游吟型",
        "subtitle": "安静自由，心里装着远方；也等一个愿并肩的灵魂",
        "traits": ["感受深，开口却不急", "走走停停，生活随性", "独立完整，不靠黏连证明存在", "开放冒险，却怕一厢情愿的重量"],
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
