"""匹配池过滤：学校规则 + 黑名单 + 取向 + 是否进池。"""

from config import CROSS_SCHOOL_MATCHING_ENABLED
from models import EDUCATION_LEVELS, User, Blocklist, Match
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
    """同校始终可配；跨校需总闸开启且双方白名单互相包含对方学校。"""
    if user_a.school == user_b.school:
        return True
    if not CROSS_SCHOOL_MATCHING_ENABLED:
        return False
    a_list = set(user_a.get_cross_schools())
    b_list = set(user_b.get_cross_schools())
    return user_b.school in a_list and user_a.school in b_list


def degree_compatible(user_a, user_b):
    """双方都填了学历：同学历可配，跨学历须双方勾选。
    有一方未填：不知道学历，不拦老用户；但已填且明确不跨的一方，不与「未知」配。"""
    a = (user_a.education_level or "").strip()
    b = (user_b.education_level or "").strip()
    a_ok = a in EDUCATION_LEVELS
    b_ok = b in EDUCATION_LEVELS
    if a_ok and b_ok:
        if a == b:
            return True
        return bool(user_a.allow_cross_degree) and bool(user_b.allow_cross_degree)
    if a_ok and not user_a.allow_cross_degree:
        return False
    if b_ok and not user_b.allow_cross_degree:
        return False
    return True


def deactivate_filled_degree_violations(user=None):
    """双方都已填学历、按当前规则不可配的有效配对 → active=False。
    任一方未填学历的不拆（对方可能只是还没打开新表单，不能当成跨学历）。
    返回拆掉的条数（调用方负责 commit）。"""
    q = Match.query.filter(Match.active.is_(True))
    if user is not None:
        q = q.filter((Match.user1_id == user.id) | (Match.user2_id == user.id))
    n = 0
    for m in q.all():
        a = User.query.get(m.user1_id)
        b = User.query.get(m.user2_id)
        if not a or not b:
            continue
        ea = (a.education_level or "").strip()
        eb = (b.education_level or "").strip()
        if ea not in EDUCATION_LEVELS or eb not in EDUCATION_LEVELS:
            continue
        if degree_compatible(a, b):
            continue
        m.active = False
        n += 1
        print(
            f"[CampusMatch] deactivate match #{m.id}: "
            f"{a.id}/{ea}/cross={int(bool(a.allow_cross_degree))} "
            f"x {b.id}/{eb}/cross={int(bool(b.allow_cross_degree))}"
        )
    return n


def vectors_aligned(user_a, user_b):
    va = user_a.feature_vector
    vb = user_b.feature_vector
    return bool(va and vb and len(va) == len(vb))


def pair_key(a_id, b_id):
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


def previous_partner_ids(user_id):
    """曾与该用户配过对的对方 ID（含已失效，不含拉黑过滤）。"""
    rows = Match.query.filter(
        (Match.user1_id == user_id) | (Match.user2_id == user_id)
    ).all()
    ids = set()
    for r in rows:
        ids.add(r.user2_id if r.user1_id == user_id else r.user1_id)
    return ids


def previous_pair_keys(user_ids=None):
    """历史配对 (min_id, max_id)。传入 user_ids 时只收两端都在集合内的对。"""
    q = Match.query
    if user_ids is not None:
        ids = set(user_ids)
        if not ids:
            return set()
        q = q.filter(Match.user1_id.in_(ids), Match.user2_id.in_(ids))
    keys = set()
    for r in q.all():
        keys.add(pair_key(r.user1_id, r.user2_id))
    return keys


def eligible_candidates(user, exclude_ids=None):
    """即时匹配候选：进池 + 学校规则 + 黑名单 + 取向 + 向量 + 对方本周额度。"""
    exclude_ids = set(exclude_ids or ())
    exclude_ids.add(user.id)
    blocked = blocked_partner_ids(user.id)

    q = User.query.filter(
        User.email_verified == True,
        User.feature_vector_json.isnot(None),
        User.gender.isnot(None),
    )
    willing = user.get_cross_schools()
    # 未选跨校：只查同校，少扫库
    if not (CROSS_SCHOOL_MATCHING_ENABLED and willing):
        q = q.filter(User.school == user.school)
    # 未开跨学历：只查同学历
    if user.education_level in EDUCATION_LEVELS and not user.allow_cross_degree:
        q = q.filter(User.education_level == user.education_level)

    out = []
    for c in q.all():
        if c.id in exclude_ids or c.id in blocked:
            continue
        if not c.in_match_pool():
            continue
        if not school_compatible(user, c):
            continue
        if not degree_compatible(user, c):
            continue
        if not orientation_compatible(user, c):
            continue
        if not vectors_aligned(user, c):
            continue
        out.append(c)

    # 延迟导入，避免与 batch_job 循环依赖；排除本周已配满的人
    from batch_job import users_without_weekly_quota
    busy = users_without_weekly_quota([c.id for c in out])
    return [c for c in out if c.id not in busy]
