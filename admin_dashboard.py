"""Private, read-only operations dashboard and anonymous traffic counters."""

import hashlib
import hmac
import json
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict, deque
from datetime import date, datetime, time as dt_time, timedelta
from functools import wraps

from flask import Blueprint, g, redirect, render_template, request, session, url_for
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from batch_job import current_week_key, next_batch_datetime, week_window_start
from config import (
    ADMIN_SECRET,
    BATCH_SCHEDULER_ENABLED,
    MAIL_ENABLED,
    MAIL_PROVIDER,
    PUBLIC_URL,
    RESEND_API_KEY,
    RESEND_DAILY_LIMIT,
    SECRET_KEY,
)
from models import Match, TrafficDay, TrafficVisitor, User, db


bp = Blueprint("admin_dashboard", __name__)
_login_attempts = defaultdict(deque)
_TRACKED_ENDPOINTS = {
    "index", "privacy", "support", "verify_page", "questionnaire_page", "matches_page",
}
_BOT_MARKERS = ("bot", "spider", "crawler", "preview", "uptime", "monitor")
_MAIL_STATUS_LABELS = {
    "delivered": "已送达",
    "sent": "发送中",
    "queued": "排队中",
    "scheduled": "已安排",
    "delivery_delayed": "延迟",
    "bounced": "退信",
    "suppressed": "已拦截",
    "failed": "失败",
    "complained": "垃圾邮件投诉",
    "canceled": "已取消",
}


def _macau_today():
    return (datetime.utcnow() + timedelta(hours=8)).date()


def _admin_fingerprint():
    return hmac.new(SECRET_KEY.encode("utf-8"), (ADMIN_SECRET or "").encode("utf-8"), hashlib.sha256).hexdigest()


def _admin_signed_in():
    saved = session.get("admin_fingerprint")
    signed_at = session.get("admin_signed_at", 0)
    if not ADMIN_SECRET or not saved:
        return False
    try:
        age = time.time() - float(signed_at or 0)
    except (TypeError, ValueError):
        return False
    if not 0 <= age <= 8 * 3600 or not isinstance(saved, str) or not saved.isascii():
        return False
    return secrets.compare_digest(saved, _admin_fingerprint())


def _csrf_token():
    token = session.get("admin_csrf")
    if not token:
        token = secrets.token_urlsafe(24)
        session["admin_csrf"] = token
    return token


def _valid_csrf(value):
    expected = session.get("admin_csrf") or ""
    return bool(expected and value and secrets.compare_digest(expected.encode("utf-8"), value.encode("utf-8")))


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not _admin_signed_in():
            return redirect(url_for("admin_dashboard.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@bp.before_app_request
def record_public_traffic():
    if request.method != "GET" or request.endpoint not in _TRACKED_ENDPOINTS:
        return
    agent = (request.headers.get("User-Agent") or "").lower()
    if any(marker in agent for marker in _BOT_MARKERS):
        return

    visitor_id = request.cookies.get("cm_visitor")
    if not visitor_id or not re.fullmatch(r"[A-Za-z0-9_-]{20,80}", visitor_id):
        visitor_id = secrets.token_urlsafe(24)
        g.cm_new_visitor = visitor_id
    today = _macau_today()
    digest = hashlib.sha256(f"{SECRET_KEY}|{today.isoformat()}|{visitor_id}".encode("utf-8")).hexdigest()
    try:
        # Savepoints tolerate simultaneous inserts; SQL increments avoid lost updates.
        try:
            with db.session.begin_nested():
                db.session.add(TrafficDay(day=today, page_views=0, unique_visitors=0))
                db.session.flush()
        except IntegrityError:
            pass
        new_visitor = 0
        try:
            with db.session.begin_nested():
                db.session.add(TrafficVisitor(day=today, visitor_hash=digest))
                db.session.flush()
            new_visitor = 1
        except IntegrityError:
            pass
        db.session.execute(update(TrafficDay).where(TrafficDay.day == today).values(
            page_views=TrafficDay.page_views + 1,
            unique_visitors=TrafficDay.unique_visitors + new_visitor,
        ))
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f"[analytics] traffic counter skipped: {exc}")


@bp.after_app_request
def admin_response_headers(response):
    if getattr(g, "cm_new_visitor", None):
        response.set_cookie(
            "cm_visitor",
            g.cm_new_visitor,
            max_age=365 * 24 * 3600,
            secure=PUBLIC_URL.startswith("https://"),
            httponly=True,
            samesite="Lax",
        )
    if request.path.startswith("/admin"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def _login_allowed():
    key = request.remote_addr or "unknown"
    now = time.time()
    attempts = _login_attempts[key]
    while attempts and now - attempts[0] > 900:
        attempts.popleft()
    if len(attempts) >= 6:
        return False
    attempts.append(now)
    return True


@bp.route("/admin/login", methods=["GET", "POST"])
def login():
    if _admin_signed_in():
        return redirect(url_for("admin_dashboard.dashboard"))
    error = None
    status = 200
    if not ADMIN_SECRET:
        error = "服务器尚未配置 ADMIN_SECRET，管理员后台已锁定。"
        status = 503
    elif request.method == "POST":
        if not _valid_csrf(request.form.get("csrf")):
            error, status = "页面已过期，请刷新后重试。", 400
        elif not _login_allowed():
            error, status = "尝试次数过多，请 15 分钟后再试。", 429
        elif not secrets.compare_digest((request.form.get("password") or "").encode("utf-8"), ADMIN_SECRET.encode("utf-8")):
            error, status = "管理员密码不正确。", 401
        else:
            session["admin_fingerprint"] = _admin_fingerprint()
            session["admin_signed_at"] = time.time()
            session.permanent = True
            return redirect(url_for("admin_dashboard.dashboard"))
    return render_template("admin_login.html", error=error, admin_csrf=_csrf_token()), status


@bp.route("/admin/logout", methods=["POST"])
def logout():
    if _valid_csrf(request.form.get("csrf")):
        session.pop("admin_fingerprint", None)
        session.pop("admin_signed_at", None)
        session["admin_csrf"] = secrets.token_urlsafe(24)
    return redirect(url_for("admin_dashboard.login"))


def _resend_summary():
    result = {
        "available": False,
        "error": None,
        "used_today": 0,
        "daily_limit": RESEND_DAILY_LIMIT,
        "remaining": RESEND_DAILY_LIMIT,
        "statuses": {},
        "recent": [],
    }
    if not MAIL_ENABLED or MAIL_PROVIDER != "resend" or not RESEND_API_KEY:
        result["error"] = "Resend 未启用或未配置 API Key"
        return result
    req = urllib.request.Request(
        "https://api.resend.com/emails?" + urllib.parse.urlencode({"limit": 100}),
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "User-Agent": "CampusMatch-Admin/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as exc:
        result["error"] = f"暂时无法读取 Resend：{str(exc)[:120]}"
        return result

    today = _macau_today()
    statuses = Counter()
    recent = []
    used_today = 0
    for item in payload.get("data") or []:
        created_raw = item.get("created_at") or ""
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
            macau_day = (created.replace(tzinfo=None) + timedelta(hours=8)).date()
            time_label = (created.replace(tzinfo=None) + timedelta(hours=8)).strftime("%m-%d %H:%M")
        except (TypeError, ValueError):
            macau_day, time_label = None, "-"
        if macau_day == today:
            used_today += 1
        raw_status = (item.get("last_event") or "sent").lower()
        grouped = "delivered" if raw_status in ("opened", "clicked") else raw_status
        statuses[grouped] += 1
        recipients = item.get("to") or []
        address = recipients[0] if recipients else ""
        domain = address.rsplit("@", 1)[-1] if "@" in address else "-"
        subject = item.get("subject") or ""
        if "验证码" in subject or "verification" in subject.lower() or "code" in subject.lower():
            category = "验证码"
        elif "暂未配对" in subject or "本轮匹配" in subject:
            category = "未匹配通知"
        elif "匹配" in subject or "match" in subject.lower():
            category = "匹配通知"
        elif "问卷" in subject:
            category = "问卷提醒"
        elif "招呼" in subject or "交流" in subject:
            category = "配对回访"
        else:
            category = "其他邮件"
        if len(recent) < 12:
            recent.append({
                "time": time_label,
                "domain": domain,
                "category": category,
                "status": grouped,
                "status_label": _MAIL_STATUS_LABELS.get(grouped, grouped),
            })

    result.update({
        "available": True,
        "used_today": used_today,
        "remaining": max(0, RESEND_DAILY_LIMIT - used_today),
        "statuses": dict(statuses),
        "recent": recent,
    })
    return result


def _dashboard_data():
    from mail_operations import summary
    try:
        mail_budget = summary()
        mail_budget['enabled'] = MAIL_ENABLED and MAIL_PROVIDER == 'resend'
    except Exception:
        mail_budget = None
    now = datetime.utcnow()
    today = _macau_today()
    today_start = datetime.combine(today, dt_time.min) - timedelta(hours=8)
    week_start = week_window_start(now)
    week_key = current_week_key(now)
    users = User.query.order_by(User.id).all()
    verified = [user for user in users if user.email_verified]
    ready = [user for user in verified if user.ready_to_match()]
    pool = [user for user in ready if user.is_open_to_match()]

    school_rows = []
    grouped = defaultdict(list)
    for user in verified:
        grouped[user.school].append(user)
    for school, members in sorted(grouped.items(), key=lambda row: (-len(row[1]), row[0])):
        school_rows.append({
            "school": school,
            "verified": len(members),
            "ready": sum(1 for user in members if user in ready),
            "opted": sum(1 for user in members if user.opt_in_week == week_key),
        })

    traffic_rows = []
    traffic_by_day = {
        row.day: row for row in TrafficDay.query.filter(TrafficDay.day >= today - timedelta(days=6)).all()
    }
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        row = traffic_by_day.get(day)
        traffic_rows.append({
            "day": day.strftime("%m-%d"),
            "page_views": int(row.page_views or 0) if row else 0,
            "visitors": int(row.unique_visitors or 0) if row else 0,
        })

    return {
        "generated_at": (now + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M"),
        "metrics": {
            "verified_total": len(verified),
            "verified_today": sum(1 for user in verified if user.created_at and user.created_at >= today_start),
            "questionnaire_ready": len(ready),
            "open_pool": len(pool),
            "opted_week": sum(1 for user in pool if user.opt_in_week == week_key),
            "matches_week": Match.query.filter(Match.created_at >= week_start).count(),
            "active_matches": Match.query.filter(Match.active.is_(True)).count(),
            "notified_week": Match.query.filter(Match.created_at >= week_start, Match.notified.is_(True)).count(),
        },
        "traffic": traffic_rows,
        "traffic_max": max([row["page_views"] for row in traffic_rows] + [1]),
        "schools": school_rows,
        "email": _resend_summary(),
        "mail_budget": mail_budget,
        "system": {
            "database": "正常",
            "mail": "已启用" if MAIL_ENABLED else "未启用",
            "mail_provider": MAIL_PROVIDER,
            "scheduler": "已启用" if BATCH_SCHEDULER_ENABLED else "未启用",
            "next_batch": next_batch_datetime().strftime("%Y-%m-%d %H:%M"),
        },
    }


@bp.route("/admin")
@admin_required
def dashboard():
    return render_template("admin_dashboard.html", data=_dashboard_data(), admin_csrf=_csrf_token())
