"""首周自动预约，以及连续三周不出现则提醒一次。"""

from datetime import datetime, timedelta

DORMANT_DAYS = 21


def current_week_key(now=None):
    now = now or datetime.now()
    return now.strftime("%G-W%V")


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
    return True


def is_dormant(user, now_utc=None, now_local=None):
    """连续三周没登录，且近三周都没有预约。已提醒过的不重复算。"""
    if not user.is_open_to_match():
        return False
    if getattr(user, "dormant_notice_at", None):
        return False
    if not user.in_match_pool():
        return False
    now_utc = now_utc or datetime.utcnow()
    seen = user.last_login_at or user.created_at
    if seen is None or seen >= now_utc - timedelta(days=DORMANT_DAYS):
        return False
    if user.opt_in_week in recent_week_keys(now_local):
        return False
    return True
