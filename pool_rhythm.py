"""首周自动预约，以及连续三周不出现则提醒一次。"""

from datetime import datetime, timedelta

DORMANT_DAYS = 21


def current_week_key(now=None):
    now = now or datetime.now()
    return now.strftime("%G-W%V")


def next_week_key(now=None):
    now = now or datetime.now()
    return current_week_key(now + timedelta(days=7))


def set_next_availability(user, choice, now=None):
    """有 = 预先预约下周；无 = 下周不进；再说 = 下周仍要自己点。"""
    if choice not in ("yes", "no", "later"):
        raise ValueError(choice)
    user.next_availability = choice
    user.next_availability_week = next_week_key(now)


def apply_ahead_opt_in(user, now=None):
    """「有」指向的那一周到了，就写成当周预约。写下后清掉，取消预约不会被写回去。"""
    now = now or datetime.now()
    week = current_week_key(now)
    if getattr(user, "next_availability", None) != "yes":
        return False
    if getattr(user, "next_availability_week", None) != week:
        return False
    if not user.is_open_to_match() or not user.ready_to_match():
        return False
    user.next_availability = None
    user.next_availability_week = None
    if user.opt_in_week != week:
        user.opt_in_week = week
    return True


def recent_week_keys(now=None, weeks=3):
    now = now or datetime.now()
    return {current_week_key(now - timedelta(days=7 * i)) for i in range(weeks)}


def grant_debut_week(user, now=None):
    """第一次进池且愿意匹配：自动预约当周。之后不再自动续。"""
    if getattr(user, "debut_opted_at", None):
        return False
    if not user.is_open_to_match() or not user.ready_to_match():
        return False
    user.opt_in_week = current_week_key(now)
    user.debut_opted_at = datetime.utcnow()
    # 新用户问卷里已写明规则，不发老用户变更信。
    if getattr(user, "weekly_rule_notice_at", None) is None:
        user.weekly_rule_notice_at = datetime.utcnow()
    return True


def grant_transition_week(user, week=None, has_active_match=False):
    """老用户过渡：还在池里、当前没有有效配对的，自动预约当周一次。已有配对的不推进新一轮。"""
    week = week or current_week_key()
    if getattr(user, "rhythm_grace_week", None):
        return False
    if not user.is_open_to_match() or not user.ready_to_match():
        return False
    user.rhythm_grace_week = week
    if has_active_match:
        return False
    if user.opt_in_week != week:
        user.opt_in_week = week
        return True
    return False


def is_dormant(user, now_utc=None, now_local=None):
    """规则说明发出满三周后，仍三周没登录、近三周也没预约。已提醒过的不重复算。"""
    if not user.is_open_to_match():
        return False
    if getattr(user, "dormant_notice_at", None):
        return False
    if not user.in_match_pool():
        return False
    now_utc = now_utc or datetime.utcnow()
    # 规则说明发出后满三周仍不来，才提醒。没收到说明、或说明还不满三周，不算。
    told = getattr(user, "weekly_rule_notice_at", None)
    if told is None or told > now_utc - timedelta(days=DORMANT_DAYS):
        return False
    seen = user.last_login_at or user.created_at
    if seen is None or seen >= now_utc - timedelta(days=DORMANT_DAYS):
        return False
    if user.opt_in_week in recent_week_keys(now_local):
        return False
    return True
