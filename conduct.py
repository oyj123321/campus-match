"""被多位同学拉黑后的短暂停用。只数当前黑名单里不同的人，不把同一个人重复计算。"""
from datetime import datetime, timedelta

from models import Blocklist, Match

BLOCK_SUSPEND_LIMIT = 3
BLOCK_SUSPEND_DAYS = 7
SUSPEND_WRITE_ALLOW = frozenset({
    ("POST", "/api/logout"),
    ("DELETE", "/api/me"),
})


def macau_stamp(moment):
    if not moment:
        return ""
    return (moment + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")


def distinct_block_count(user_id):
    return Blocklist.query.filter_by(blocked_user_id=user_id).count()


def suspend_if_widely_blocked(user):
    """超过 3 位不同同学正在拉黑时，若当前没有停用，则停用 7 天，并关掉进行中的恋爱配对。"""
    if distinct_block_count(user.id) <= BLOCK_SUSPEND_LIMIT:
        return False
    now = datetime.utcnow()
    if user.is_suspended(now):
        return False
    user.suspended_until = now + timedelta(days=BLOCK_SUSPEND_DAYS)
    Match.query.filter(
        ((Match.user1_id == user.id) | (Match.user2_id == user.id)),
        Match.active.is_(True),
    ).update({"active": False}, synchronize_session=False)
    return True


def write_is_frozen(method, path, suspended):
    if method in ("GET", "HEAD", "OPTIONS") or not suspended:
        return False
    return (method, path) not in SUSPEND_WRITE_ALLOW
