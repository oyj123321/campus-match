"""
问卷 → MBTI 娱乐推演（阶段 A）

非官方 MBTI® 测评；由恋爱问卷量表近似映射，仅供展示与破冰。
不参与匹配打分。
"""

from __future__ import annotations

# 更合拍：只写字母（用户拍板）
COMPATIBLE = {
    "INFP": ["ENFJ", "ENTJ"],
    "INFJ": ["ENFP", "ENTP"],
    "INTP": ["ENTJ", "ENFJ"],
    "INTJ": ["ENFP", "ENTP"],
    "ISFP": ["ENFJ", "ESFJ"],
    "ISFJ": ["ESFP", "ESTP"],
    "ISTP": ["ESFJ", "ESTJ"],
    "ISTJ": ["ESFP", "ESTP"],
    "ENFP": ["INFJ", "INTJ"],
    "ENFJ": ["INFP", "ISFP"],
    "ENTP": ["INFJ", "INTJ"],
    "ENTJ": ["INFP", "INTP"],
    "ESFP": ["ISFJ", "ISTJ"],
    "ESFJ": ["ISFP", "ISTP"],
    "ESTP": ["ISFJ", "ISTJ"],
    "ESTJ": ["ISFP", "INFP"],
}

# 正经语气；昵称保留简短中性标签便于页面标题
TYPE_COPY = {
    "INFP": {
        "label": "调停者",
        "summary": "重视真实与意义，排斥虚伪的客套。",
        "self": "你倾向按内心标准做选择，需要被理解，而不是被催促改变。",
        "love": "感情上往往慢热，一旦建立信任会投入很深；需要情感安全感与表达空间。",
        "caution": "留意把小摩擦放大成价值冲突。",
    },
    "INFJ": {
        "label": "提倡者",
        "summary": "关注深层连接，习惯在行动前先想清楚。",
        "self": "你对关系与氛围敏感，宁可少而深，也不愿维持表面热闹。",
        "love": "会认真筛选对象；合适的人会得到稳定的耐心与长期投入。",
        "caution": "避免过度预判对方意图而不直接沟通。",
    },
    "INTP": {
        "label": "逻辑学家",
        "summary": "以分析与好奇驱动，需要独立思考的空间。",
        "self": "你习惯先厘清逻辑再做决定，对空洞说教缺乏兴趣。",
        "love": "讲得清的关系更让你安心；需要独处与智力上的交流。",
        "caution": "正确不等于被接住，重要时也需照顾对方情绪。",
    },
    "INTJ": {
        "label": "建筑师",
        "summary": "目标清晰，不喜欢无效消耗。",
        "self": "你倾向长远规划，对敷衍与反复无常缺乏耐心。",
        "love": "认定对象后会把关系纳入生活安排；需要对等的认真。",
        "caution": "关心有时表现为安排与建议，需说明动机以免显得疏离。",
    },
    "ISFP": {
        "label": "探险家",
        "summary": "重视体验与当下感受，表达方式偏含蓄。",
        "self": "你温和而有主见，压力大时会先退回自己的节奏。",
        "love": "偏好自然发生的相处；陪伴与气氛比宏大承诺更重要。",
        "caution": "不适时请直接说明，避免对方误判为无事。",
    },
    "ISFJ": {
        "label": "守卫者",
        "summary": "可靠、体贴，重视责任与细节。",
        "self": "你记得他人说过的小事，习惯用行动表达在意。",
        "love": "愿意付出稳定的照顾，也需要被同等珍惜，而非被视为理所当然。",
        "caution": "避免长期单向付出导致耗竭。",
    },
    "ISTP": {
        "label": "鉴赏家",
        "summary": "务实、冷静，临场处理能力强。",
        "self": "你不喜欢戏剧化表达，更看重实际出现与解决问题。",
        "love": "愿意给时间与协助即是在意；需要尊重个人空间。",
        "caution": "沉默容易被解读为不在乎，关键时刻请补一句说明。",
    },
    "ISTJ": {
        "label": "物流师",
        "summary": "守信、重秩序，承诺一旦说出就会执行。",
        "self": "你重视可预期的安排与边界，讨厌反复改口。",
        "love": "长期稳定是你的默认选项；混乱与失约会明显减分。",
        "caution": "在灵活变通上可适当放松，以免显得刻板。",
    },
    "ENFP": {
        "label": "竞选者",
        "summary": "热情、联想丰富，对可能性敏感。",
        "self": "你容易点燃气氛，也需要被认真看见，而不只是「很好玩」。",
        "love": "表达相对直接；共同体验与情感回应都很重要。",
        "caution": "开局热情之后，请记得维持日常的稳定联系。",
    },
    "ENFJ": {
        "label": "主人公",
        "summary": "关注他人成长与关系和谐，带动能力强。",
        "self": "你习惯照顾现场情绪，也容易把别人的状态扛在自己肩上。",
        "love": "投入深，愿意成全对方；同时需要有人反过来关心你。",
        "caution": "不必为对方的全部情绪负责。",
    },
    "ENTP": {
        "label": "辩论家",
        "summary": "点子多、反应快，厌恶无聊的停滞。",
        "self": "你享受思想碰撞，抬杠常常是一种互动方式而非否定。",
        "love": "需要智力刺激与空间；过于沉闷的关系难以持久。",
        "caution": "争论时先确认对方感到被尊重。",
    },
    "ENTJ": {
        "label": "指挥官",
        "summary": "决断力强，习惯推进与定方向。",
        "self": "你不喜欢拖泥带水，认定后愿意投入资源与时间。",
        "love": "约会与规划往往高效；也需要学习留下柔软的协作空间。",
        "caution": "避免把感情管理成单纯的项目管理。",
    },
    "ESFP": {
        "label": "表演者",
        "summary": "活在当下，重视现场感受与共同快乐。",
        "self": "你擅长带动气氛，排斥说教式相处。",
        "love": "惊喜与陪伴并重；需要对方一起参与，而不是只旁观。",
        "caution": "重要议题出现时，请认真进入讨论，而不仅用轻松带过。",
    },
    "ESFJ": {
        "label": "执政官",
        "summary": "重视和谐、责任与关系中的温度。",
        "self": "你在意他人是否舒服，仪式感与日常照顾往往并行。",
        "love": "愿意经营相处细节；也需要明确的回应与肯定。",
        "caution": "不必为了维持表面和谐而压抑真实需求。",
    },
    "ESTP": {
        "label": "企业家",
        "summary": "行动导向，临场适应快。",
        "self": "你偏好实践胜过空谈，对纯粹理论争执缺乏耐心。",
        "love": "见面与共同经历比长时间文字拉扯更有效。",
        "caution": "涉及承诺时请说清楚，以免被理解为轻率。",
    },
    "ESTJ": {
        "label": "总经理",
        "summary": "组织力强，标准明确，重视对等负责。",
        "self": "你希望规则清楚、执行到位，反感含糊与甩锅。",
        "love": "愿意承担具体责任；也期待对方同样靠谱。",
        "caution": "在坚持标准的同时保留温柔与协商余地。",
    },
}


def _norm_answers(answers):
    out = {}
    for k, v in (answers or {}).items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            continue
    return out


def _scale(answers, qid, default=3):
    try:
        return max(1, min(5, int(answers.get(qid, default))))
    except (TypeError, ValueError):
        return default


def _multi(answers, qid):
    raw = answers.get(qid) or []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    return []


def _interest_breadth(answers):
    n = 0
    exclusive_skip = {"不玩游戏", "不运动", "不太看书", "不太参加", "什么都听", "暂不确定"}
    for qid in (25, 26, 27, 28, 30, 31, 32):
        for opt in _multi(answers, qid):
            if opt not in exclusive_skip:
                n += 1
    return n


def score_dimensions(answers):
    """
    返回各维得分：正值偏后字母（I/N/F/P），负值偏前字母（E/S/T/J）。
    绝对值越大越偏向该侧。
    """
    a = _norm_answers(answers)

    # E(-) / I(+)
    ei = 0.0
    ei += (_scale(a, 19) - 3) * 1.4          # 独处：高→I
    ei += (_scale(a, 23) - 3) * 0.9          # 沟通频率：右「不必天天」→I
    ei += (3 - _scale(a, 38)) * 0.8          # 左「和朋友」→E
    ei += (_scale(a, 29) - 3) * 0.5          # 右宅家→I
    relax = _multi(a, 32)
    if "和朋友聊天" in relax:
        ei -= 1.0
    if "刷社交媒体" in relax:
        ei -= 0.4
    if "看书/写作" in relax or "睡觉" in relax:
        ei += 0.6
    love = _multi(a, 18)
    if "直接说爱与赞美" in love:
        ei -= 0.5
    if len(love) >= 3:
        ei -= 0.4

    # S(-) / N(+)
    sn = 0.0
    sn += (_scale(a, 2) - 3) * 1.0           # 开放→N
    sn += (_scale(a, 16) - 3) * 0.4          # 随性旅行略→N/P，弱贡献 N
    breadth = _interest_breadth(a)
    if breadth >= 12:
        sn += 1.2
    elif breadth >= 7:
        sn += 0.5
    elif breadth <= 3:
        sn -= 0.8
    reading = _multi(a, 27)
    if any(x in reading for x in ("科幻/奇幻", "历史/哲学", "心理学/自我提升")):
        sn += 0.8
    if "不太看书" in reading or "学术/专业书籍" in reading:
        sn -= 0.3
    film = _multi(a, 25)
    if any(x in film for x in ("科幻/奇幻", "纪录片")):
        sn += 0.5
    if "纪录片" not in film and any(x in film for x in ("喜剧", "动作/冒险")):
        sn -= 0.2
    places = _multi(a, 34)
    if "海外" in places or "暂不确定" in places:
        sn += 0.4
    if places and set(places) <= {"一线城市", "二线城市"}:
        sn -= 0.3

    # T(-) / F(+)
    tf = 0.0
    tf += (3 - _scale(a, 22)) * 1.2          # 左浪漫→F；右实际→T
    tf += (3 - _scale(a, 21)) * 0.9          # 左陪伴安慰→F
    tf += (3 - _scale(a, 7)) * 0.4           # 左优先伴侣→略 F
    if "直接说爱与赞美" in love or "准备礼物惊喜" in love:
        tf += 0.6
    if "帮对方做事" in love and "直接说爱与赞美" not in love:
        tf -= 0.3
    # 重要题若偏情感维度，略推 F
    # （important 在 build 时另传则更好；此处仅用答案）

    # J(-) / P(+)
    jp = 0.0
    jp += (_scale(a, 16) - 3) * 1.3          # 随性旅行→P；精致规划→J
    jp += (_scale(a, 39) - 3) * 1.1          # 灵活家务→P
    jp += (_scale(a, 12) - 3) * 0.9          # 整洁：需看 left=整洁
    # Q12: left 整洁 right 随意 — 高分→P
    jp += (_scale(a, 36) - 3) * 0.5          # 快推进略→P；慢热略→J
    jp += (_scale(a, 4) - 3) * 0.4           # 享受当下→P；储蓄→J

    return {"EI": ei, "SN": sn, "TF": tf, "JP": jp}


def letters_from_scores(scores):
    ei = "I" if scores["EI"] >= 0 else "E"
    sn = "N" if scores["SN"] >= 0 else "S"
    tf = "F" if scores["TF"] >= 0 else "T"
    jp = "P" if scores["JP"] >= 0 else "J"
    return ei + sn + tf + jp


def _hit_lines(answers, mbti_type):
    a = _norm_answers(answers)
    lines = []

    solitude = _scale(a, 19)
    if solitude >= 4:
        lines.append("在独处需求上，你的选择更接近内向一侧，与类型中的 I/E 倾向一致。")
    elif solitude <= 2:
        lines.append("在相处密度上，你更偏好较高联结，与外向一侧的倾向相符。")

    travel = _scale(a, 16)
    if travel <= 2:
        lines.append("旅行风格偏规划清单，与 J 型常见的秩序偏好一致。")
    elif travel >= 4:
        lines.append("旅行风格偏随性，与 P 型常见的灵活偏好一致。")

    love = _multi(a, 18)
    if love:
        lines.append("表达爱意方面，你选择了「" + "、".join(love[:2]) + "」，这比含糊的「都可以」更清晰。")

    film = _multi(a, 25)
    if film:
        lines.append("影视偏好包含「" + film[0] + "」，适合作为破冰时的具体话题。")

    spicy = _scale(a, 10)
    if spicy >= 4:
        lines.append("你对辛辣口味接受度较高：共同用餐时可作为轻松的开场信息。")
    elif spicy <= 2:
        lines.append("你对辛辣口味偏谨慎：共同用餐时值得提前说明。")

    # 去重保序，最多 3 条
    out = []
    for x in lines:
        if x not in out:
            out.append(x)
        if len(out) >= 3:
            break
    if not out:
        out.append(f"当前推演类型为 {mbti_type}，由恋爱问卷近似映射，供参考。")
    return out


def build_mbti_report(answers):
    """生成可 JSON 序列化的报告 dict。"""
    scores = score_dimensions(answers)
    code = letters_from_scores(scores)
    copy = TYPE_COPY.get(code) or TYPE_COPY["INFP"]
    compatible = COMPATIBLE.get(code, [])

    return {
        "type": code,
        "label": copy["label"],
        "summary": copy["summary"],
        "self": copy["self"],
        "love": copy["love"],
        "caution": copy["caution"],
        "compatible": compatible,
        "hits": _hit_lines(answers, code),
        "disclaimer": (
            "本结果由 CampusMatch 恋爱问卷近似映射，并非正式 MBTI 测验，"
            "仅供娱乐与破冰参考，不代表匹配算法结论。"
        ),
        "source": "questionnaire_v1",
    }
