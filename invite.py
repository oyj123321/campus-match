"""邀请码：跨校可用；填码后对方资料齐才给双方本周额度 +1。"""

from __future__ import annotations

import secrets
from datetime import datetime

from models import db, User

INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
INVITE_LEN = 6
INVITER_REWARDS_PER_WEEK = 1


def normalize_invite_code(raw: str | None) -> str:
    return (raw or "").strip().upper().replace(" ", "").replace("-", "")


def ensure_invite_code(user: User) -> bool:
    """没有码就生成。返回是否新写入。"""
    if not user or user.invite_code:
        return False
    for _ in range(24):
        cand = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_LEN))
        taken = User.query.filter_by(invite_code=cand).first()
        if not taken:
            user.invite_code = cand
            return True
    suffix = str(user.id or secrets.randbelow(10**6)).zfill(6)[-6:]
    user.invite_code = suffix
    return True


def bind_invite(user: User, raw_code: str | None) -> tuple[bool, str | None]:
    """绑定邀请人。已绑过则忽略。返回 (ok, error_key)。"""
    code = normalize_invite_code(raw_code)
    if not code:
        return True, None
    if user.invited_by_id:
        return True, None
    ensure_invite_code(user)
    if user.invite_code and code == user.invite_code:
        return False, "err.invite_self"
    inviter = User.query.filter_by(invite_code=code).first()
    if not inviter:
        return False, "err.invite_bad"
    if inviter.id == user.id:
        return False, "err.invite_self"
    from app import find_sibling_account

    sibling = find_sibling_account(user.email, user.school)
    if sibling and sibling.id == inviter.id:
        return False, "err.invite_sibling"
    user.invited_by_id = inviter.id
    user.invite_bound_at = datetime.utcnow()
    return True, None


def _inviter_rewards_this_week(inviter_id: int) -> int:
    from batch_job import week_window_start

    since = week_window_start()
    return User.query.filter(
        User.invited_by_id == inviter_id,
        User.invite_redeemed_at.isnot(None),
        User.invite_redeemed_at >= since,
    ).count()


def try_redeem_invite(user: User) -> bool:
    """资料齐后发奖：被邀请人必得本周 +1；邀请人本周最多兑现 1 次。"""
    if not user or user.invite_redeemed_at or not user.invited_by_id:
        return False
    if not user.ready_to_match():
        return False
    inviter = db.session.get(User, user.invited_by_id)
    if not inviter or inviter.id == user.id:
        return False
    from batch_job import current_week_key

    week = current_week_key()
    already = _inviter_rewards_this_week(inviter.id)
    user.invite_quota_week = week
    user.invite_redeemed_at = datetime.utcnow()
    if already < INVITER_REWARDS_PER_WEEK:
        inviter.invite_quota_week = week
    return True
