"""匹配池过滤：学校规则 + 黑名单 + 取向。"""

from config import CROSS_SCHOOL_MATCHING_ENABLED
from models import User, Blocklist
from matcher import orientation_compatible


def blocked_partner_ids(user_id):
    """与 user_id 任一方拉黑的对方 ID 集合（双向生效）。"""
    rows = Blocklist.query.filter(
        (Blocklist.user_id == user_id) | (Blocklist.blocked_user_id == user_id)
    ).all()
    ids = set()
    for r in rows:
        ids.add(r.blocked_user_id if r.user_id == user_id else r.user_id)
    return ids


def is_blocked_pair(a_id, b_id):
    if a_id == b_id:
        return True
    return Blocklist.query.filter(
        (
            (Blocklist.user_id == a_id) & (Blocklist.blocked_user_id == b_id)
        ) | (
            (Blocklist.user_id == b_id) & (Blocklist.blocked_user_id == a_id)
        )
    ).first() is not None


def school_compatible(user_a, user_b):
    """同校始终可配；跨校需总闸开启且双方都允许。"""
    if user_a.school == user_b.school:
        return True
    if not CROSS_SCHOOL_MATCHING_ENABLED:
        return False
    return bool(getattr(user_a, "allow_cross_school", False) and getattr(user_b, "allow_cross_school", False))


def vectors_aligned(user_a, user_b):
    va = user_a.feature_vector
    vb = user_b.feature_vector
    return bool(va and vb and len(va) == len(vb))


def eligible_candidates(user, exclude_ids=None):
    """即时匹配候选：学校规则 + 黑名单 + 取向 + 向量维数对齐。"""
    exclude_ids = set(exclude_ids or ())
    exclude_ids.add(user.id)
    blocked = blocked_partner_ids(user.id)

    q = User.query.filter(
        User.email_verified == True,
        User.feature_vector_json.isnot(None),
        User.gender.isnot(None),
    )
    # 未开跨校：只查同校，少扫库
    if not (CROSS_SCHOOL_MATCHING_ENABLED and getattr(user, "allow_cross_school", False)):
        q = q.filter(User.school == user.school)

    out = []
    for c in q.all():
        if c.id in exclude_ids or c.id in blocked:
            continue
        if not school_compatible(user, c):
            continue
        if not orientation_compatible(user, c):
            continue
        if not vectors_aligned(user, c):
            continue
        out.append(c)
    return out
