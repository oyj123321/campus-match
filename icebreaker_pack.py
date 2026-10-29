"""揭晓后的破冰扩展包。

只加开口提示：额外话题、可复制开场句、以及匹配时已经算好的差异。
不改配对对象、排序、分数或联系方式。
结算预留支付宝手机网站支付（给手机浏览器里的站点）。不向支付宝下单。
"""

import os
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from icebreakers import icebreaker_text, pick_icebreakers
from models import db, IcebreakerPackEntitlement, IcebreakerPackOrder

PACK_PRICE_CENTS = 660
PACK_PRICE_LABEL = "¥6.6"
PACK_CURRENCY = "CNY"
FREE_ICEBREAKER_COUNT = 3
PACK_ICEBREAKER_COUNT = 6

# 手机网站支付：同学在手机浏览器里打开站点，跳到支付宝收银台。
# 当面付是柜台扫码，不适合这个页面。三项未齐就不算已配置；齐了也不会请求支付宝。
ALIPAY_PRODUCT = "alipay.trade.wap.pay"
ALIPAY_ENV_KEYS = (
    "ALIPAY_APP_ID",
    "ALIPAY_APP_PRIVATE_KEY",
    "ALIPAY_PUBLIC_KEY",
)

_FALLBACK_OPENERS = (
    "这周校园里有没有一件小事想吐槽，随便说一个就行",
    "你一般在哪自习，图书馆还是宿舍",
    "最近有没有吃到一家想再去的店",
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
    """免费卡只给纯文本话题，不带可复制开场句。"""
    out = []
    for item in (insight or {}).get("icebreakers") or []:
        text = icebreaker_text(item).strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= FREE_ICEBREAKER_COUNT:
            break
    return out


def _decorate(line):
    text = (line or "").strip()
    tip = text
    for sep in ("，", ","):
        idx = text.find(sep)
        if idx >= 4:
            tip = text[:idx].strip()
            break
    return {"tip": tip, "send": text}


def _alt_seed(seed):
    if isinstance(seed, (list, tuple)) and len(seed) >= 2:
        try:
            return (int(seed[0]) ^ 0x5A17, int(seed[1]) ^ 0xC0FF)
        except (TypeError, ValueError):
            pass
    return ("pack", str(seed))


def build_pack_icebreakers(stored, shared_tags, seed, my_school, their_school):
    """保留原来的 3 条，再按同一对人的稳定种子补 3 条，并附上可复制开场句。"""
    base = []
    for item in stored or []:
        text = icebreaker_text(item).strip()
        if text and text not in base:
            base.append(text)
        if len(base) >= FREE_ICEBREAKER_COUNT:
            break
    fresh = pick_icebreakers(
        shared_tags=shared_tags, seed=seed, n=12,
        my_school=my_school, their_school=their_school,
    )
    if len(base) < FREE_ICEBREAKER_COUNT:
        for line in fresh:
            if line not in base:
                base.append(line)
            if len(base) >= FREE_ICEBREAKER_COUNT:
                break
    seen = set(base)
    extras = []
    pools = [fresh]
    if len([line for line in fresh if line not in seen]) < 3:
        pools.append(pick_icebreakers(
            shared_tags=shared_tags, seed=_alt_seed(seed), n=12,
            my_school=my_school, their_school=their_school,
        ))
    for pool in pools:
        for line in pool:
            if line not in seen:
                extras.append(line)
                seen.add(line)
            if len(extras) >= 3:
                break
        if len(extras) >= 3:
            break
    n = 0
    while len(extras) < 3 and n < 12:
        line = _FALLBACK_OPENERS[n % len(_FALLBACK_OPENERS)]
        if n >= len(_FALLBACK_OPENERS):
            line = f"{line}（{n}）"
        n += 1
        if line not in seen:
            extras.append(line)
            seen.add(line)
    lines = (base + extras)[:PACK_ICEBREAKER_COUNT]
    return [_decorate(line) for line in lines if line]


def apply_pack_view(item, insight, match, viewer_id, my_school, their_school, active):
    """按权益改写当前响应。不写匹配表，不改联系方式字段。"""
    if not icebreaker_pack_enabled() or not active or match is None:
        return item
    insight = insight or {}
    entitled = has_icebreaker_pack(match.id, viewer_id)
    item["match_id"] = match.id
    if entitled:
        item["icebreakers"] = build_pack_icebreakers(
            insight.get("icebreakers") or [],
            insight.get("shared_tags") or [],
            seed=(match.user1_id, match.user2_id),
            my_school=my_school,
            their_school=their_school,
        )
        diffs = []
        for line in insight.get("differences") or []:
            text = str(line or "").strip()
            if text:
                diffs.append(text)
            if len(diffs) >= 4:
                break
        item["differences"] = diffs
        item["differences_count"] = insight.get("total_differences", len(diffs)) or len(diffs)
    else:
        item["icebreakers"] = free_icebreaker_strings(insight)
        item["differences"] = []
        item["differences_count"] = 0
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
