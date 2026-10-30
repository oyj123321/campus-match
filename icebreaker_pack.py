"""揭晓后的破冰扩展包。

付费内容只有 3 句可复制开场白：按这一次揭晓双方的问卷答案和共同标签写成。
免费的破冰话题仍是原来的 3 条；问卷差异（量表差距较大的那些）始终展示，不看是否购买。
不从静态话题库再加 3 条，也不改配对对象、排序、分数或联系方式。
结算预留支付宝手机网站支付（给手机浏览器里的站点）。不向支付宝下单。
"""

import os
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from icebreakers import icebreaker_text
from models import db, IcebreakerPackEntitlement, IcebreakerPackOrder, User
from questionnaire import QUESTIONS

PACK_PRICE_CENTS = 660
PACK_PRICE_LABEL = "¥6.6"
PACK_CURRENCY = "CNY"
FREE_ICEBREAKER_COUNT = 3
OPENER_COUNT = 3

# 手机网站支付：同学在手机浏览器里打开站点，跳到支付宝收银台。
# 当面付是柜台扫码，不适合这个页面。三项未齐就不算已配置；齐了也不会请求支付宝。
ALIPAY_PRODUCT = "alipay.trade.wap.pay"
ALIPAY_ENV_KEYS = (
    "ALIPAY_APP_ID",
    "ALIPAY_APP_PRIVATE_KEY",
    "ALIPAY_PUBLIC_KEY",
)

# 与问卷洞察一致：婚姻、孩子、出轨、吸烟、前任不做开口草稿。宗教也不写进可复制的第一句。
_SKIP_SCALE_QIDS = {3, 5, 6, 8, 13, 24}

# qid -> (话题, 偏左时的说法, 偏右时的说法)。只给适合当开场的题。
_SCALE_OPENERS = {
    1: ("时间和精力", "事业", "家庭"),
    2: ("生活方式", "偏传统", "偏开放"),
    4: ("花钱", "先存着", "先花着"),
    7: ("伴侣和朋友撞期时", "先顾伴侣", "先顾朋友"),
    9: ("作息", "早睡", "夜猫子"),
    10: ("吃辣", "不怎么吃辣", "无辣不欢"),
    11: ("运动", "经常运动", "几乎不运动"),
    12: ("房间整洁", "喜欢整齐", "不太拘小节"),
    14: ("喝酒", "不太喝", "会小酌"),
    15: ("养宠物", "想养", "不想养"),
    16: ("旅行", "喜欢做计划", "走到哪算哪"),
    17: ("吵架之后", "当下就说", "先冷静再说"),
    19: ("独处", "喜欢腻在一起", "需要自己的空间"),
    20: ("对方的社交", "不太介意", "会在意边界"),
    21: ("情绪低的时候", "希望被陪着", "希望自己待一会儿"),
    22: ("恋爱里更看重", "仪式感", "实际和稳定"),
    23: ("联系频率", "想经常聊", "有事再说"),
    29: ("周末", "想出门", "想宅着"),
    33: ("约会账单", "倾向 AA", "倾向轮流请"),
    35: ("见面频率", "想常见面", "线上联络也行"),
    36: ("节奏", "想慢一点", "聊得来就想推进"),
    37: ("异地", "可以接受异地", "更想同城"),
    38: ("约会形式", "可以跟朋友一起", "更想两人单独"),
    39: ("家务", "想先分工", "看谁有空再分"),
}

# 问卷和共同标签都不够 3 句时才用。不是校园静态话题库。
_FILLER_OPENERS = (
    {
        "tip": "先问一件具体的小事",
        "send": "问卷上能对上的具体点不多。你这周有没有一件小事想吐槽，随便说一个就行",
    },
    {
        "tip": "问对方平时待在哪",
        "send": "你一般在哪待着，图书馆、宿舍还是外面。我想知道你平时是什么节奏",
    },
    {
        "tip": "问最近的一件小事",
        "send": "最近有没有吃到或看到一件想再来一次的，丢一个名字就行",
    },
)


def _flag(name, default="false"):
    return str(os.environ.get(name, default)).strip().lower() in ("1", "true", "on", "yes")


def icebreaker_pack_enabled():
    """运行时读取。默认关闭，未设置环境变量时为 false。"""
    return _flag("ICEBREAKER_PACK_ENABLED", "false")


def mock_grant_allowed():
    """仅当显式打开模拟开通时，匹配页才能不经支付写入权益。"""
    return _flag("ICEBREAKER_PACK_MOCK_GRANT", "false")


def alipay_configured():
    return all(str(os.environ.get(key) or "").strip() for key in ALIPAY_ENV_KEYS)


def payment_scaffold_status():
    """不发起任何商户请求。缺应用号或密钥为 unconfigured，三项都有仍为 not_wired。"""
    if not alipay_configured():
        return "unconfigured"
    return "not_wired"


def has_icebreaker_pack(match_id, user_id):
    if not match_id or not user_id:
        return False
    return (
        IcebreakerPackEntitlement.query.filter_by(
            match_id=match_id, user_id=user_id
        ).first()
        is not None
    )


def grant_icebreaker_pack(match, user_id, provider):
    """写入订单与权益。同一人、同一次揭晓只保留一份。"""
    if provider not in ("mock", "admin"):
        raise ValueError("unsupported provider")
    existing = IcebreakerPackEntitlement.query.filter_by(
        match_id=match.id, user_id=user_id
    ).first()
    if existing:
        return existing, False
    order = IcebreakerPackOrder(
        match_id=match.id,
        user_id=user_id,
        amount_cents=PACK_PRICE_CENTS,
        currency=PACK_CURRENCY,
        status="granted",
        provider=provider,
        paid_at=datetime.utcnow(),
    )
    db.session.add(order)
    try:
        db.session.flush()
        ent = IcebreakerPackEntitlement(
            match_id=match.id,
            user_id=user_id,
            order_id=order.id,
        )
        db.session.add(ent)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = IcebreakerPackEntitlement.query.filter_by(
            match_id=match.id, user_id=user_id
        ).first()
        return existing, False
    return ent, True


def free_icebreaker_strings(insight):
    """免费卡只给原来的纯文本话题，不附带可复制开场句。"""
    out = []
    for item in (insight or {}).get("icebreakers") or []:
        text = icebreaker_text(item).strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= FREE_ICEBREAKER_COUNT:
            break
    return out


def _seed_int(seed):
    if isinstance(seed, int):
        return seed & 0xFFFFFFFF
    n = 0
    if isinstance(seed, (list, tuple)):
        parts = seed
    else:
        parts = (seed,)
    for part in parts:
        try:
            piece = int(part)
        except (TypeError, ValueError):
            piece = sum(ord(ch) for ch in str(part))
        n = ((n * 1_000_003) ^ piece) & 0xFFFFFFFF
    return n


def _rotate(items, seed):
    if len(items) <= 1:
        return list(items)
    start = _seed_int(seed) % len(items)
    return list(items[start:]) + list(items[:start])


def _norm_answers(raw):
    out = {}
    for key, value in (raw or {}).items():
        try:
            out[int(key)] = value
        except (TypeError, ValueError):
            continue
    return out


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _side_phrase(value, left, right):
    if value <= 2:
        return left
    if value >= 4:
        return right
    return None


def _tag_opener(tag):
    return {
        "tip": f"共同标签：{tag}",
        "send": f"问卷里我们都勾了「{tag}」。你最近有在看、听或者玩的吗，想互相丢一个的话直接发我就行",
    }


def _gap_opener(topic, mine, theirs):
    return {
        "tip": f"从「{topic}」开口",
        "send": f"「{topic}」我更靠近{mine}，你看起来更靠近{theirs}。想听听你实际是怎么过的，不是来辩论",
    }


def _same_opener(topic, side):
    return {
        "tip": f"从「{topic}」开口",
        "send": f"「{topic}」我们好像都更靠近{side}。你平时也是这样，还是问卷上随手点的",
    }


def _viewer_opener(topic, side):
    return {
        "tip": f"从「{topic}」开口",
        "send": f"我在「{topic}」上更靠近{side}。你呢，随便说你的真实习惯就行",
    }


def _shared_from_answers(mine, theirs):
    found = []
    for question in QUESTIONS:
        if question.get("type") != "multi":
            continue
        left = mine.get(question["id"]) or []
        right = theirs.get(question["id"]) or []
        if not isinstance(left, (list, tuple)) or not isinstance(right, (list, tuple)):
            continue
        both = {str(item) for item in left} & {str(item) for item in right}
        for option in question.get("options") or []:
            if option in both and option not in found:
                found.append(option)
    return found


def _unique_tags(shared_tags, mine, theirs):
    tags = []
    for tag in list(shared_tags or []) + _shared_from_answers(mine, theirs):
        text = str(tag or "").strip()
        if text and text not in tags:
            tags.append(text)
    return tags


def _scale_candidates(mine, theirs):
    gaps = []
    sames = []
    for qid, (topic, left, right) in _SCALE_OPENERS.items():
        if qid in _SKIP_SCALE_QIDS:
            continue
        mine_value = _num(mine.get(qid))
        their_value = _num(theirs.get(qid))
        if mine_value is None or their_value is None:
            continue
        mine_side = _side_phrase(mine_value, left, right)
        their_side = _side_phrase(their_value, left, right)
        if not mine_side or not their_side:
            continue
        diff = abs(mine_value - their_value)
        if diff >= 3 and mine_side != their_side:
            gaps.append((diff, qid, _gap_opener(topic, mine_side, their_side)))
        elif diff <= 1 and mine_side == their_side:
            sames.append((qid, _same_opener(topic, mine_side)))
    gaps.sort(key=lambda item: (-item[0], item[1]))
    sames.sort(key=lambda item: item[0])
    return [item[2] for item in gaps], [item[1] for item in sames]


def _viewer_only_candidates(mine, theirs):
    lines = []
    for qid, (topic, left, right) in _SCALE_OPENERS.items():
        if qid in _SKIP_SCALE_QIDS:
            continue
        if _num(theirs.get(qid)) is not None:
            continue
        mine_value = _num(mine.get(qid))
        if mine_value is None:
            continue
        side = _side_phrase(mine_value, left, right)
        if side:
            lines.append(_viewer_opener(topic, side))
    return lines


def _take(candidates, avoid, limit):
    chosen = []
    seen = set(avoid or ())
    for item in candidates:
        send = str((item or {}).get("send") or "").strip()
        tip = str((item or {}).get("tip") or "").strip()
        if not send or not tip or send in seen:
            continue
        chosen.append({"tip": tip, "send": send})
        seen.add(send)
        if len(chosen) >= limit:
            break
    return chosen


def build_match_openers(viewer_answers, partner_answers, shared_tags, seed=None, avoid=None):
    """3 句可复制草稿。同一对人、同一视角、同一组答案，结果稳定。

    不读取校园静态话题库。优先用共同标签，再用双方都答了的量表
    （差距 ≥3 的差异，以及靠在同一侧的相近点）。材料不够再用购买者自己的倾向，最后才用备用句。
    """
    mine = _norm_answers(viewer_answers)
    theirs = _norm_answers(partner_answers)
    tags = _unique_tags(shared_tags, mine, theirs)
    rotated = _rotate(tags, seed)
    lead = [_tag_opener(rotated[0])] if rotated else []
    rest_tags = [_tag_opener(tag) for tag in tags if not rotated or tag != rotated[0]]
    gaps, sames = _scale_candidates(mine, theirs)
    candidates = (
        lead
        + gaps
        + sames
        + rest_tags
        + _viewer_only_candidates(mine, theirs)
        + list(_FILLER_OPENERS)
    )
    chosen = _take(candidates, avoid, OPENER_COUNT)
    n = 0
    while len(chosen) < OPENER_COUNT and n < 6:
        base = _FILLER_OPENERS[n % len(_FILLER_OPENERS)]
        extra = dict(base)
        if n >= len(_FILLER_OPENERS):
            extra["send"] = f"{base['send']}（{n}）"
        chosen = _take(chosen + [extra], avoid, OPENER_COUNT)
        n += 1
    return chosen


def _stored_answers(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return {}
    try:
        return user.answers or {}
    except (TypeError, ValueError):
        return {}


def _pair_answers(match, viewer_id):
    if viewer_id == match.user1_id:
        return _stored_answers(match.user1_id), _stored_answers(match.user2_id)
    return _stored_answers(match.user2_id), _stored_answers(match.user1_id)


def apply_pack_view(item, insight, match, viewer_id, my_school, their_school, active):
    """按权益改写当前响应。不写匹配表，不改联系方式字段。

    学校参数保留给调用方，付费草稿不使用校园静态话题库。
    差异沿用匹配卡上已经放好的问卷洞察，锁定时也不清空。
    """
    del my_school, their_school
    if not icebreaker_pack_enabled() or not active or match is None:
        return item
    insight = insight or {}
    entitled = has_icebreaker_pack(match.id, viewer_id)
    item["match_id"] = match.id
    free_lines = free_icebreaker_strings(insight)
    item["icebreakers"] = free_lines
    if entitled:
        mine, theirs = _pair_answers(match, viewer_id)
        item["openers"] = build_match_openers(
            mine,
            theirs,
            insight.get("shared_tags") or [],
            seed=(viewer_id, match.user1_id, match.user2_id),
            avoid=free_lines,
        )
    else:
        item["openers"] = []
    item["icebreaker_pack"] = {
        "enabled": True,
        "entitled": entitled,
        "price_cents": PACK_PRICE_CENTS,
        "price_label": PACK_PRICE_LABEL,
        "currency": PACK_CURRENCY,
        "pay_provider": "alipay",
        "pay_product": ALIPAY_PRODUCT,
        "mock_grant": bool(mock_grant_allowed() and not entitled),
    }
    return item
