"""举报累计后的短暂停用。只数不同举报人，驳回的不计入。拉黑不触发停用。"""
from datetime import datetime, timedelta

from models import Match, UserReport, db

REPORT_SUSPEND_LIMIT = 3
REPORT_SUSPEND_DAYS = 7
SUSPEND_WRITE_ALLOW = frozenset({
    ("POST", "/api/logout"),
    ("DELETE", "/api/me"),
})


class ReportError(Exception):
    def __init__(self, key):
        self.key = key


def macau_stamp(moment):
    if not moment:
        return ""
    return (moment + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")


def counted_report_count(user_id):
    """未驳回的不同举报人数。同一人只算一次。"""
    return UserReport.query.filter(
        UserReport.target_id == user_id,
        UserReport.status != "dismissed",
    ).count()


def suspend_if_widely_reported(user):
    """超过 3 位不同同学的未驳回举报，且当前没有停用时，停用 7 天并关掉进行中的恋爱配对。"""
    if counted_report_count(user.id) <= REPORT_SUSPEND_LIMIT:
        return False
    now = datetime.utcnow()
    if user.is_suspended(now):
        return False
    user.suspended_until = now + timedelta(days=REPORT_SUSPEND_DAYS)
    Match.query.filter(
        ((Match.user1_id == user.id) | (Match.user2_id == user.id)),
        Match.active.is_(True),
    ).update({"active": False}, synchronize_session=False)
    return True


def file_report(reporter, target, reason):
    text = (reason or "").strip()
    if reporter.id == target.id:
        raise ReportError("err.report_self")
    if not target.email_verified:
        raise ReportError("err.user_missing")
    if not 2 <= len(text) <= 280:
        raise ReportError("err.report_reason")
    existing = UserReport.query.filter_by(reporter_id=reporter.id, target_id=target.id).first()
    if existing and existing.status != "dismissed":
        raise ReportError("err.report_dup")
    if existing:
        existing.reason = text
        existing.status = "open"
        existing.created_at = datetime.utcnow()
        existing.reviewed_at = None
        existing.review_note = None
        row = existing
    else:
        row = UserReport(reporter_id=reporter.id, target_id=target.id, reason=text, status="open")
        db.session.add(row)
    db.session.flush()
    suspend_if_widely_reported(target)
    return row


def review_report(report, status, note):
    if status not in ("upheld", "dismissed"):
        raise ReportError("err.report_review")
    report.status = status
    report.review_note = (note or "").strip()[:280] or None
    report.reviewed_at = datetime.utcnow()


def lift_suspension(user):
    user.suspended_until = None


def write_is_frozen(method, path, suspended):
    if method in ("GET", "HEAD", "OPTIONS") or not suspended:
        return False
    return (method, path) not in SUSPEND_WRITE_ALLOW
