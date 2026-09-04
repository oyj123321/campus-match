"""
CampusMatch v2 — 校园恋爱匹配系统
=====================================
参考 SJTU Date / FDU Date / MatchUs 已验证模式：
  深度问卷 → 特征向量 → 余弦相似度 → 匈牙利全局匹配 → 邮件通知
"""

import os
import time, json, threading
from collections import defaultdict, deque
from datetime import datetime, timedelta, date
from functools import wraps

from flask import Flask, request, session, jsonify, render_template, redirect, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import inspect, text

from config import (
    SECRET_KEY, FLASK_DEBUG, SQLALCHEMY_DATABASE_URI, PUBLIC_URL,
    USING_DEFAULT_SECRET_KEY,
    SCHOOL_DOMAINS, MATCH_MODE, MATCH_TOP_N, MATCH_MIN_SCORE,
    MATCH_DELAY_SECONDS, VERIFICATION_EXPIRE_SECONDS,
    REGISTER_RATE_LIMIT, REGISTER_RATE_WINDOW, REGISTER_RESEND_SECONDS,
    MATCH_WEEKLY_NEW_LIMIT, MATCH_COOLDOWN_HOURS,
    BATCH_MATCH_DAY, BATCH_MATCH_HOUR, BATCH_SCHEDULER_ENABLED,
    ADMIN_SECRET, WEEKDAY_LABELS,
    REVEAL_REQUIRE_OPT_IN, INSTANT_MATCH_ENABLED, CROSS_SCHOOL_MATCHING_ENABLED,
    ICEBREAKER_FOLLOWUP_DAYS, MAIL_NO_MATCH_ENABLED, ICEBREAKER_FOLLOWUP_ENABLED,
    MAIL_INCOMPLETE_NUDGE_ENABLED, INCOMPLETE_NUDGE_COOLDOWN_DAYS,
    MAIL_ENABLED, MAIL_PROVIDER, MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM,
    CONTACT_EMAIL,
    RESEND_API_KEY,
    LOGIN_ONCE_PER_DAY, SITE_ANNOUNCEMENT,
    SESSION_REMEMBER_DAYS, DEVICE_COOKIE_NAME,
)
from models import db, User, UserTag, Match, Blocklist, EXPRESS_BIO_MIN, EDUCATION_LEVELS
from questionnaire import QUESTIONS, build_feature_vector, build_express_vector, get_compatibility_insight, get_open_letter
from personality import build_love_personality
from matcher import real_time_match, batch_match_school
from i18n_server import api_err, t_api, request_lang
from email_service import (
    send_verification_email, send_match_result_email, send_incomplete_nudges,
)
from batch_job import (
    persist_user_matches, count_new_matches_this_week, weekly_limit_for,
    next_batch_datetime, run_batch_all, schedule_loop, current_week_key,
)
from match_pool import eligible_candidates, previous_partner_ids, previous_pair_keys

# ---- App Factory ----
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=SESSION_REMEMBER_DAYS)
if PUBLIC_URL.startswith("https://"):
    app.config["SESSION_COOKIE_SECURE"] = True
db.init_app(app)
_DEVICE_SERIALIZER = URLSafeTimedSerializer(SECRET_KEY, salt="cm-device-v1")


@app.context_processor
def inject_globals():
    user = get_current_user()
    incomplete = bool(
        user and user.email_verified and not user.ready_to_match()
    )
    return {
        "contact_email": CONTACT_EMAIL,
        "site_announcement": (SITE_ANNOUNCEMENT or "").strip(),
        "login_once_per_day": LOGIN_ONCE_PER_DAY,
        "public_url": PUBLIC_URL,
        "current_user": user,
        "questionnaire_incomplete": incomplete,
    }


# 邮箱 → 近期请求时间戳（进程内限流，MVP 够用）
_register_hits = defaultdict(deque)
_verify_fails = defaultdict(deque)
_email_locks = defaultdict(threading.Lock)
VERIFY_FAIL_LIMIT = 8
VERIFY_FAIL_WINDOW = 900  # 秒


def get_mail_config():
    return {
        "enabled": MAIL_ENABLED,
        "provider": MAIL_PROVIDER,
        "server": MAIL_SERVER,
        "port": MAIL_PORT,
        "username": MAIL_USERNAME,
        "password": MAIL_PASSWORD,
        "mail_from": MAIL_FROM,
        "resend_api_key": RESEND_API_KEY,
        "public_url": PUBLIC_URL,
    }


def notify_no_match(user, reason=None):
    """无结果时发「暂未配对」邮件；额度紧张时可 MAIL_NO_MATCH_ENABLED=false 关闭。"""
    if not MAIL_NO_MATCH_ENABLED:
        return False, "no-match-mail-disabled"
    ok, info = send_match_result_email(
        user.email, [], get_mail_config(), reason=reason,
    )
    return bool(ok), info


def touch_instant_match_cooldown(user):
    """提前揭晓一旦进入匹配尝试（无论成败）都写入冷却时间戳。

    成功路径还会由 persist_user_matches 再次刷新；失败路径靠此处挡住
    12h 内反复点击刷「暂未配对」邮件。不消耗本周新建匹配额度。
    """
    user.last_matched_at = datetime.utcnow()
    db.session.commit()


# ---- Helpers ----

def get_school_from_email(email):
    email = email.strip().lower()
    domain = email.split("@")[-1] if "@" in email else ""
    for school, domains in SCHOOL_DOMAINS.items():
        if domain in domains:
            return school
    return None


def _must_new_student_needs_outlook_domain(email):
    """科大学生 Outlook 登录账号是 学号@student.must.edu.mo；纯学号@must.edu.mo 收不到网页邮箱。"""
    email = (email or "").strip().lower()
    if "@" not in email:
        return False
    local, domain = email.rsplit("@", 1)
    return domain == "must.edu.mo" and local.isdigit() and len(local) >= 6


def _must_should_migrate_to_student_domain(new_email, sibling):
    """旧号 学号@must.edu.mo 改填学生域名时，把账号迁到 Outlook 能打开的邮箱。"""
    if not sibling:
        return False
    new_email = (new_email or "").strip().lower()
    old = (sibling.email or "").strip().lower()
    if "@" not in new_email or "@" not in old:
        return False
    n_local, n_dom = new_email.rsplit("@", 1)
    o_local, o_dom = old.rsplit("@", 1)
    return (
        n_local == o_local
        and n_local.isdigit()
        and len(n_local) >= 6
        and n_dom == "student.must.edu.mo"
        and o_dom == "must.edu.mo"
    )


def _email_local_part(email: str) -> str:
    return (email or "").strip().lower().split("@", 1)[0]


def find_sibling_account(email: str, school: str | None = None):
    """同校其他域名、相同本地名的已有账号（一人多号风险）。"""
    email = (email or "").strip().lower()
    if "@" not in email:
        return None
    school = school or get_school_from_email(email)
    if not school:
        return None
    local = _email_local_part(email)
    if not local:
        return None
    domains = SCHOOL_DOMAINS.get(school) or []
    others = [f"{local}@{d}" for d in domains if f"{local}@{d}" != email]
    if not others:
        return None
    return User.query.filter(User.email.in_(others)).first()


def sibling_account_error(sibling: User):
    return (
        f"该学号/账号已在本平台使用邮箱 {sibling.email} 注册过。"
        f"请用该邮箱登录，勿用同校其他域名重复注册。"
    )


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json or request.path.startswith("/api/"):
                return api_err("err.login", 401)
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = db.session.get(User, user_id)
    if user:
        from invite import ensure_invite_code
        if ensure_invite_code(user):
            db.session.commit()
    return user


def check_verify_fail_rate(email):
    """验证码猜错次数限制。返回是否允许再试。"""
    now = time.time()
    key = (email or "").strip().lower()
    q = _verify_fails[key]
    while q and now - q[0] > VERIFY_FAIL_WINDOW:
        q.popleft()
    return len(q) < VERIFY_FAIL_LIMIT


def record_verify_fail(email):
    _verify_fails[(email or "").strip().lower()].append(time.time())


def check_register_rate(email):
    """同一邮箱在窗口内发送验证码次数限制。返回 (ok, error_msg)。"""
    now = time.time()
    key = email.strip().lower()
    q = _register_hits[key]
    while q and now - q[0] > REGISTER_RATE_WINDOW:
        q.popleft()
    if len(q) >= REGISTER_RATE_LIMIT:
        return False, None
    q.append(now)
    return True, None


def _token_unexpired(user):
    if not user or not user.verification_token or not user.verification_sent_at:
        return False
    elapsed = (datetime.utcnow() - user.verification_sent_at).total_seconds()
    return 0 <= elapsed <= VERIFICATION_EXPIRE_SECONDS


def _seconds_since_code(user):
    if not user or not user.verification_sent_at:
        return None
    return (datetime.utcnow() - user.verification_sent_at).total_seconds()


def _code_json(user, email, *, mail_ok=False, already=False, rate_limited=False, wait=False, info=None):
    """发码接口统一成功体：始终让前端打开验证码输入框。"""
    if rate_limited:
        msg = t_api("err.rate_enter", mins=REGISTER_RATE_WINDOW // 60)
    elif wait:
        msg = t_api("ok.code_wait", secs=REGISTER_RESEND_SECONDS)
    elif already:
        msg = t_api("ok.code_already")
    elif mail_ok:
        msg = t_api("ok.code_sent", email=email)
    else:
        msg = t_api("ok.code_fail", info=info or "")
    show_dev = (not MAIL_ENABLED) or (not mail_ok and not already and not wait and not rate_limited)
    return jsonify({
        "ok": True,
        "mail_sent": bool(mail_ok),
        "code_already_sent": bool(already or wait or rate_limited),
        "message": msg,
        "dev_token": user.verification_token if show_dev and user.verification_token else None,
    })


def _send_or_reuse_verification(user, email):
    """发验证码：未过期则复用，连点不换码；限额打满仍允许输入已发的码。"""
    if _token_unexpired(user):
        elapsed = _seconds_since_code(user) or 0
        if elapsed < REGISTER_RESEND_SECONDS:
            return _code_json(user, email, already=True, wait=True)
        ok_rate, _ = check_register_rate(email)
        if not ok_rate:
            return _code_json(user, email, already=True, rate_limited=True)
        token = user.verification_token
        user.verification_sent_at = datetime.utcnow()
        db.session.commit()
        mail_ok, info = send_verification_email(email, token, get_mail_config())
        return _code_json(user, email, mail_ok=mail_ok, info=info)

    ok_rate, _ = check_register_rate(email)
    if not ok_rate:
        if user.verification_token:
            return _code_json(user, email, already=True, rate_limited=True)
        return api_err("err.rate", 429, mins=REGISTER_RATE_WINDOW // 60)

    token = user.generate_token()
    db.session.commit()
    mail_ok, info = send_verification_email(email, token, get_mail_config())
    return _code_json(user, email, mail_ok=mail_ok, info=info)


def _macau_date(dt_utc_naive: datetime | None = None) -> date:
    """UTC naive → 澳门/香港日历日（UTC+8）。"""
    utc = dt_utc_naive or datetime.utcnow()
    return (utc + timedelta(hours=8)).date()


def _logged_in_today(user: User) -> bool:
    if not user or not getattr(user, "last_login_at", None):
        return False
    return _macau_date(user.last_login_at) == _macau_date()


def _email_sent_today(user: User) -> bool:
    if not user or not user.verification_sent_at:
        return False
    return _macau_date(user.verification_sent_at) == _macau_date()


def _mark_login(user: User) -> None:
    user.last_login_at = datetime.utcnow()


def _cookie_secure() -> bool:
    return bool(app.config.get("SESSION_COOKIE_SECURE")) or (PUBLIC_URL or "").startswith("https://")


def _device_cookie_max_age() -> int:
    return max(1, SESSION_REMEMBER_DAYS) * 86400


def _read_device_user():
    """读本设备 7 天信任 cookie；签名无效或过期则忽略。"""
    raw = request.cookies.get(DEVICE_COOKIE_NAME)
    if not raw:
        return None
    try:
        data = _DEVICE_SERIALIZER.loads(raw, max_age=_device_cookie_max_age())
    except (BadSignature, SignatureExpired, TypeError, ValueError):
        return None
    uid = data.get("uid")
    em = (data.get("em") or "").strip().lower()
    if not uid or not em:
        return None
    user = db.session.get(User, uid)
    if not user or (user.email or "").strip().lower() != em:
        return None
    return user


def _device_trusted(user: User) -> bool:
    remembered = _read_device_user()
    return bool(
        user and remembered
        and remembered.id == user.id
        and (remembered.email or "").strip().lower() == (user.email or "").strip().lower()
    )


def _attach_remember(resp, user: User):
    """写入 7 天会话 + 设备信任 cookie（HttpOnly）。"""
    session.permanent = True
    session["user_id"] = user.id
    token = _DEVICE_SERIALIZER.dumps({"uid": user.id, "em": (user.email or "").strip().lower()})
    resp.set_cookie(
        DEVICE_COOKIE_NAME,
        token,
        max_age=_device_cookie_max_age(),
        httponly=True,
        samesite="Lax",
        secure=_cookie_secure(),
        path="/",
    )
    return resp


def _login_json(user: User, payload: dict, status: int = 200):
    _mark_login(user)
    db.session.commit()
    resp = jsonify(payload)
    resp.status_code = status
    return _attach_remember(resp, user)


LOGIN_ONCE_MSG = (
    "今日已登录过（紧急限流：每人每天仅可登录一次，以澳门时区计日）。"
    "若你仍保持登录可继续使用；退出后请明天再试。给大家带来不便，敬请谅解。"
)
EMAIL_ONCE_MSG = (
    "今日验证码已发送过，请查收学校邮箱（含垃圾箱），勿重复申请。"
    "紧急限流期间每人每天仅发一封登录验证码。"
)


def _deny_login_once_today(user: User):
    """若触发每日登录限制，返回 Flask 响应；否则 None。内测号豁免。"""
    if not LOGIN_ONCE_PER_DAY or not user:
        return None
    if _is_beta_account(user.email):
        return None
    if _logged_in_today(user):
        return api_err("err.login_once", 429)
    return None


LOOKING_FOR_VALUES = {"male", "female", "both"}


def apply_education_fields(user, data, required=False):
    """写入学历 / 跨学历。required 时必须带合法 education_level。失败返回 api_err，成功返回 None。"""
    if required or "education_level" in data:
        level = (data.get("education_level") or "").strip()
        if level not in EDUCATION_LEVELS:
            return api_err("err.education")
        user.education_level = level
    if "allow_cross_degree" in data:
        user.allow_cross_degree = bool(data.get("allow_cross_degree"))
    return None


def match_quota_status(user):
    """计算冷却 / 本周额度 / 预约揭晓状态。"""
    used = count_new_matches_this_week(user.id)
    limit = weekly_limit_for(user)
    remaining = max(0, limit - used)
    cooldown_left = 0
    if user.last_matched_at and MATCH_COOLDOWN_HOURS > 0:
        elapsed = (datetime.utcnow() - user.last_matched_at).total_seconds()
        need = MATCH_COOLDOWN_HOURS * 3600
        if elapsed < need:
            cooldown_left = int(need - elapsed)
    nxt = next_batch_datetime()
    mode = MATCH_MODE if MATCH_MODE != "realtime" else "one_to_one"
    week = current_week_key()
    opted_in = (user.opt_in_week == week)
    now = datetime.now()
    # 本周是否已过揭晓时刻（周二 BATCH_MATCH_HOUR 之后）
    reveal_happened_this_week = now.weekday() > BATCH_MATCH_DAY or (
        now.weekday() == BATCH_MATCH_DAY and now.hour >= BATCH_MATCH_HOUR
    )

    active_match = Match.query.filter(
        ((Match.user1_id == user.id) | (Match.user2_id == user.id)),
        Match.active.is_(True),
    ).first()

    return {
        "weekly_limit": limit,
        "weekly_used": used,
        "weekly_remaining": remaining,
        "cooldown_hours": MATCH_COOLDOWN_HOURS,
        "cooldown_seconds_left": cooldown_left,
        "can_match_now": remaining > 0 and cooldown_left <= 0 and INSTANT_MATCH_ENABLED,
        "instant_match_enabled": INSTANT_MATCH_ENABLED,
        "next_batch_at": nxt.isoformat(timespec="minutes"),
        "next_batch_label": f"每{WEEKDAY_LABELS[BATCH_MATCH_DAY]} {BATCH_MATCH_HOUR}:00",
        "match_mode": mode,
        "week_key": week,
        "opted_in": opted_in,
        "reveal_require_opt_in": REVEAL_REQUIRE_OPT_IN,
        "reveal_happened_this_week": reveal_happened_this_week,
        "has_active_match": bool(active_match),
        "seconds_to_reveal": max(0, int((nxt - now).total_seconds())) if not reveal_happened_this_week else 0,
        "cross_school_enabled": CROSS_SCHOOL_MATCHING_ENABLED,
        "allow_cross_school": bool(user.get_cross_schools()),
        "cross_schools": user.get_cross_schools(),
        "all_schools": list(SCHOOL_DOMAINS.keys()),
        "education_level": user.education_level if (user.education_level or "") in EDUCATION_LEVELS else None,
        "allow_cross_degree": bool(user.allow_cross_degree),
        "open_to_match": user.is_open_to_match(),
        "explain": _match_explain_text(mode),
    }


def serialize_match_payload(other, score, insight, active=True):
    """统一匹配结果 JSON。不对用户返回匹配度分数；有效配对才互见学校邮箱与附加联系方式。"""
    insight = insight or {}
    letter = get_open_letter(other.answers) if active else None
    return {
        "id": other.id if active else None,
        "name": other.name if active else "（已失效的配对）",
        "gender": other.gender if active else None,
        "school": getattr(other, "school", None) if active else None,
        "education_level": (
            other.education_level
            if active and (getattr(other, "education_level", None) or "") in EDUCATION_LEVELS
            else None
        ),
        "email": other.email if active else None,
        "wechat_id": other.wechat_id if active else None,
        "bio": other.bio if active else None,
        "privacy_user": bool(active and getattr(other, "is_express", lambda: False)()),
        "open_letter": letter,
        "summary": insight.get("summary") if active else None,
        "strengths": insight.get("strengths", [])[:6] if active else [],
        "differences": insight.get("differences", [])[:4] if active else [],
        "icebreakers": insight.get("icebreakers", [])[:3] if active else [],
        "shared_tags": insight.get("shared_tags", [])[:6] if active else [],
        "differences_count": insight.get("total_differences", 0) if active else 0,
    }


def _match_explain_text(mode):
    """给开发者/用户看的通俗说明（不讲公式也能懂）。"""
    school_line = (
        "一对一：在取向互相接受、本周仍有额度的人里排序，"
        "问卷用户优先于隐私用户，曾经配过的人再往后排，同档再看问卷相似度，"
        "只给你优先级最高的 1 人；页面不展示匹配度分数，只给契合点与破冰话题"
        + (
            "；默认同校，跨校需双方互相勾选对方学校（双向白名单）。"
            "学历须填写；不同学历需双方都勾选愿意跨学历。"
            if CROSS_SCHOOL_MATCHING_ENABLED else "（同校）。学历须填写；不同学历需双方都勾选愿意跨学历。"
        )
    )
    return {
        "mode": mode,
        "summary": (
            school_line
            if mode in ("one_to_one", "realtime") else
            "Top-N：按相似度返回多人（调试用）。"
            if mode == "top_n" else
            "批量匈牙利：先按校配对，再跑跨校池；每人每周最多配到 1 人；结果只展示契合点，不展示分数。"
        ),
        "steps": [
            "1. 问卷答案变成双向平衡的特征向量，选左端或右端都不会天然占优势；「对我很重要」的题权重更大。",
            "2. 排序：双方填问卷 > 一方填问卷 > 双方隐私；曾经配过的人降一档；同档再用余弦相似度（仅内部排序，不展示分数）。",
            "3. 一票否决：婚姻、孩子出现明确相反意愿，或出轨观、吸烟接受度差异过大时直接跳过。",
            "4. 择偶取向：双方都愿意匹配对方的性别才进入候选。",
            "5. 黑名单双向生效；跨校需双方都勾选且总闸开启。",
            "6. 每人每周最多参与 1 次新匹配（发起或被配都算），不会反复抢走同一人。",
            "7. 揭晓时互见学校邮箱与附加联系方式；破冰话题帮你开口（避开出轨/婚姻等开场雷区）。",
        ],
        "why_not_many": "以前默认 Top-5 会一次出很多人，现已改为默认一对一，且每周双向各限一次。",
        "email_note": "匹配成功会尝试给你和对方发邮件；对方若是演示账号（假学校邮箱）常会失败，你的真实学校邮箱应能收到。",
    }


# ============================================================
# 页面路由
# ============================================================

@app.route("/privacy")
def privacy_page():
    """隐私政策（注册前可阅读）。"""
    return render_template("privacy.html", contact_email=CONTACT_EMAIL)


@app.route("/")
def index():
    user = get_current_user()
    if user:
        if not user.email_verified:
            return redirect(url_for("verify_page"))
        if user.ready_to_match():
            return redirect(url_for("matches_page"))
        return redirect(url_for("questionnaire_page"))
    from sqlalchemy import func
    stats = dict(
        db.session.query(User.school, func.count(User.id))
        .filter(User.email_verified == True)
        .group_by(User.school)
        .all()
    )
    return render_template(
        "index.html",
        schools=SCHOOL_DOMAINS,
        school_stats=stats,
        total_users=sum(stats.values()),
        batch_label=f"每{WEEKDAY_LABELS[BATCH_MATCH_DAY]} {BATCH_MATCH_HOUR}:00",
    )


@app.route("/verify")
def verify_page():
    user = get_current_user()
    if not user:
        return redirect(url_for("index"))
    if user.email_verified:
        if user.ready_to_match():
            return redirect(url_for("matches_page"))
        return redirect(url_for("questionnaire_page"))
    return render_template("verify.html", email=user.email)


@app.route("/questionnaire")
@login_required
def questionnaire_page():
    user = get_current_user()
    if not user.email_verified:
        return redirect(url_for("verify_page"))
    return render_template(
        "questionnaire.html",
        user=user,
        questions=QUESTIONS,
        schools=list(SCHOOL_DOMAINS.keys()),
        cross_school_enabled=CROSS_SCHOOL_MATCHING_ENABLED,
    )


@app.route("/matches")
@login_required
def matches_page():
    user = get_current_user()
    if not user.email_verified:
        return redirect(url_for("verify_page"))
    # 未完成问卷也可进入：顶部/导航会醒目催填；匹配操作仍由 API 的 ready_to_match 拦截
    return render_template(
        "matches.html",
        user=user,
        quota=match_quota_status(user),
        questionnaire_incomplete=not user.ready_to_match(),
    )


@app.route("/dev/personality-themes")
def personality_themes_gallery():
    """本地预览 16 型卡片主题（仅 Debug）。"""
    if not FLASK_DEBUG:
        return "Not found", 404
    from personality import PERSONALITIES
    return render_template("personality_themes.html", personalities=PERSONALITIES)


@app.route("/dev/personality-copy-compare")
def personality_copy_compare():
    """16 型文案：吸收前（git HEAD）vs 吸收后（工作区）并排对照，仅 Debug。"""
    if not FLASK_DEBUG:
        return "Not found", 404
    import subprocess
    from pathlib import Path
    from personality import PERSONALITIES

    before = {}
    err = None
    try:
        raw = subprocess.check_output(
            ["git", "show", "HEAD:personality.py"],
            cwd=str(Path(__file__).resolve().parent),
            text=True,
            encoding="utf-8",
        )
        ns = {}
        exec(compile(raw, "personality_git_HEAD.py", "exec"), ns)  # noqa: S102
        before = ns.get("PERSONALITIES") or {}
    except Exception as exc:  # noqa: BLE001
        before = {}
        err = str(exc)

    return render_template(
        "personality_copy_compare.html",
        after=PERSONALITIES,
        before=before,
        load_error=err,
    )


@app.route("/dev/personality-compare")
def personality_style_compare():
    """花园隐士型：极简科技 vs 插画 并排对比（仅 Debug）。"""
    if not FLASK_DEBUG:
        return "Not found", 404
    from personality import PERSONALITIES
    return render_template(
        "personality_compare.html",
        p=PERSONALITIES["IFOP"],
    )


@app.route("/dev/personality-spacing")
def personality_spacing_compare():
    """花园隐士型：间距改前 vs 改后（仅 Debug）。"""
    if not FLASK_DEBUG:
        return "Not found", 404
    from personality import PERSONALITIES
    return render_template(
        "personality_spacing_compare.html",
        p=PERSONALITIES["IFOP"],
    )


@app.route("/dev/personality-export")
def personality_export_page():
    """16 型分享卡导出页（宣发截图用，仅 Debug）。?lang=tw 出繁体。"""
    if not FLASK_DEBUG:
        return "Not found", 404
    from copy import deepcopy
    from personality import PERSONALITIES, DIM_META

    lang = (request.args.get("lang") or "zh").lower()
    if lang not in ("zh", "tw"):
        lang = "zh"

    def _t(s: str) -> str:
        if lang != "tw" or not s:
            return s
        try:
            from opencc import OpenCC
            return OpenCC("s2t").convert(s)
        except Exception:
            return s

    personalities = {}
    for code, meta in PERSONALITIES.items():
        personalities[code] = {
            "name": _t(meta["name"]),
            "subtitle": _t(meta["subtitle"]),
            "traits": [_t(x) for x in meta["traits"]],
            "strength": _t(meta["strength"]),
            "match_tip": _t(meta["match_tip"]),
        }

    dim = deepcopy(DIM_META)
    if lang == "tw":
        for key in dim:
            dim[key]["label"] = _t(dim[key]["label"])
            dim[key]["high"] = (dim[key]["high"][0], _t(dim[key]["high"][1]))
            dim[key]["low"] = (dim[key]["low"][0], _t(dim[key]["low"][1]))

    def demo_bars(code: str):
        e, s, c, r = code[0], code[1], code[2], code[3]
        return [
            {
                "label": dim["expression"]["label"],
                "pct": 78 if e == "E" else 32,
                "pole": dim["expression"]["high"][1] if e == "E" else dim["expression"]["low"][1],
            },
            {
                "label": dim["rhythm"]["label"],
                "pct": 72 if s == "S" else 38,
                "pole": dim["rhythm"]["high"][1] if s == "S" else dim["rhythm"]["low"][1],
            },
            {
                "label": dim["boundary"]["label"],
                "pct": 70 if c == "C" else 35,
                "pole": dim["boundary"]["high"][1] if c == "C" else dim["boundary"]["low"][1],
            },
            {
                "label": dim["risk"]["label"],
                "pct": 74 if r == "P" else 36,
                "pole": dim["risk"]["high"][1] if r == "P" else dim["risk"]["low"][1],
            },
        ]

    ui = {
        "zh": {
            "title": "你的恋爱人格",
            "sub": "根据问卷生成，可截图分享 · 仅供娱乐",
            "traits": "核心特质",
            "strength": "关系优势：",
            "match": "你可能适合：",
            "disc": "本结果由恋爱问卷规则生成，仅供娱乐与破冰，不构成心理诊断。",
        },
        "tw": {
            "title": "你的戀愛人格",
            "sub": "根據問卷生成，可截圖分享 · 僅供娛樂",
            "traits": "核心特質",
            "strength": "關係優勢：",
            "match": "你可能適合：",
            "disc": "本結果由戀愛問卷規則生成，僅供娛樂與破冰，不構成心理診斷。",
        },
    }[lang]

    demo = {code: demo_bars(code) for code in personalities}
    return render_template(
        "personality_export.html",
        personalities=personalities,
        demo_bars=demo,
        ui=ui,
        export_lang=lang,
    )


@app.route("/dev/letter-portrait")
def letter_portrait_page():
    """歌词随笔文字侧写分享卡（私人预览，仅 Debug）。"""
    if not FLASK_DEBUG:
        return "Not found", 404
    from personality import DIM_META

    # IFOA 底色：内敛 / 随性 / 独立 / 开放；文案掺花园隐士式守候
    bars = [
        {
            "label": DIM_META["expression"]["label"],
            "pct": 28,
            "pole": DIM_META["expression"]["low"][1],
        },
        {
            "label": DIM_META["rhythm"]["label"],
            "pct": 34,
            "pole": DIM_META["rhythm"]["low"][1],
        },
        {
            "label": DIM_META["boundary"]["label"],
            "pct": 30,
            "pole": DIM_META["boundary"]["low"][1],
        },
        {
            "label": DIM_META["risk"]["label"],
            "pct": 42,
            "pole": DIM_META["risk"]["low"][1],
        },
    ]
    return render_template(
        "letter_portrait.html",
        bars=bars,
        traits=[
            "以沟通为爱的功课——要正视、要触碰，不轻轻带过",
            "羊群外仍渴望并肩：独山上山很自由，翻山后也想有人同享",
            "苦中带甜的余韵：不写非黑即白，记苦是为了来日回甘",
            "敬纯粹，也怕爱的重量——会风险评估，仍向往不计较得失的靠近",
        ],
        strength="能把感受写成可被触碰的文字；独立完整，不靠关系填空；一旦靠近会认真谈。",
        match_tip="愿意互相触碰、接得住深情又不急着入账的人——轻声靠近，不侵入她的氧。",
    )


# ============================================================
# Auth API
# ============================================================

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    if not email or "@" not in email:
        return api_err("err.email_invalid")

    if not data.get("privacy_accepted"):
        return api_err("err.privacy")

    school = get_school_from_email(email)
    if not school:
        sep = ", " if request_lang() in ("en", "pt") else "、"
        return api_err("err.school", schools=sep.join(SCHOOL_DOMAINS.keys()))

    # 同校同本地名只允许一个账号（兼容多域名时防一人多号）
    sibling = find_sibling_account(email, school)
    if sibling:
        if _must_should_migrate_to_student_domain(email, sibling):
            taken = User.query.filter_by(email=email).first()
            if taken:
                return api_err("err.sibling", 409, email=taken.email)
            sibling.email = email
            db.session.commit()
        else:
            return api_err("err.sibling", 409, email=sibling.email)

    # 科大新号：学号必须用 student.must.edu.mo（Outlook 网页邮箱）；已有 @must.edu.mo 账号仍可登录
    if _must_new_student_needs_outlook_domain(email):
        existing = User.query.filter_by(email=email).first()
        if not existing:
            return api_err("err.must_student_mail")

    with _email_locks[email]:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, school=school)
            db.session.add(user)
            db.session.flush()

        from invite import bind_invite, ensure_invite_code
        ensure_invite_code(user)
        bind_invite(user, data.get("invite_code"))

        # 同设备 7 天内已验证过：免验证码、不吃发码限流、也不吃「每天只能登一次」
        if user.email_verified and _device_trusted(user):
            return _login_json(user, {
                "ok": True,
                "mail_sent": False,
                "direct_login": True,
                "remembered": True,
                "message": t_api("ok.device_login"),
            })

        denied = _deny_login_once_today(user)
        if denied:
            return denied

        # 内测号：免邮件，注册后直接登录（验证码随便填也能进）
        if _is_beta_account(email):
            user.verification_token = None
            user.email_verified = True
            return _login_json(user, {
                "ok": True,
                "mail_sent": False,
                "beta_skip_verify": True,
                "message": t_api("ok.beta_login", email=email),
                "dev_token": "任意",
            })

        # 未验证或换设备：当天已发过验证码则不再发信，但仍放行进验证步骤
        if LOGIN_ONCE_PER_DAY and _email_sent_today(user):
            return _code_json(user, email, already=True)

        return _send_or_reuse_verification(user, email)


def _is_beta_account(email: str) -> bool:
    """内测号：本地部分为 beta/cmtest/test + 数字，如 cmtest01@um.edu.mo。免真邮件。"""
    local = (email or "").split("@", 1)[0].lower()
    for prefix in ("cmtest", "beta", "test"):
        if local.startswith(prefix) and local[len(prefix):].isdigit():
            return True
    return False


@app.route("/api/verify", methods=["POST"])
def api_verify():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    token = (data.get("token") or "").strip().upper()

    if not email:
        return api_err("err.email_empty")

    user = User.query.filter_by(email=email).first()
    if not user:
        return api_err("err.user_missing", 404)

    if user.email_verified and _device_trusted(user):
        return _login_json(user, {
            "ok": True,
            "direct_login": True,
            "remembered": True,
            "message": t_api("ok.device_login"),
        })

    denied = _deny_login_once_today(user)
    if denied:
        return denied

    beta = _is_beta_account(email)
    # 内测号：任意验证码（可空）直接登录
    if beta:
        sibling = find_sibling_account(email, user.school)
        if sibling and sibling.email_verified and sibling.id != user.id:
            return api_err("err.sibling", 409, email=sibling.email)
        user.email_verified = True
        user.verification_token = None
        return _login_json(user, {"ok": True, "message": t_api("ok.beta_in")})

    if not token:
        return api_err("err.email_token_empty")

    if not check_verify_fail_rate(email):
        return api_err("err.rate_verify", 429, mins=VERIFY_FAIL_WINDOW // 60)

    if not user.verification_token or user.verification_token != token:
        record_verify_fail(email)
        return api_err("err.token_bad")

    if user.verification_sent_at:
        elapsed = (datetime.utcnow() - user.verification_sent_at).total_seconds()
        if elapsed > VERIFICATION_EXPIRE_SECONDS:
            return api_err("err.token_expired")

    # 验证落库前再拦一次，防止并发双号同时过验证
    sibling = find_sibling_account(email, user.school)
    if sibling and sibling.email_verified and sibling.id != user.id:
        return api_err("err.sibling", 409, email=sibling.email)

    user.email_verified = True
    user.verification_token = None
    from invite import try_redeem_invite
    try_redeem_invite(user)
    return _login_json(user, {"ok": True, "message": t_api("ok.verified")})


@app.route("/api/resend-verification", methods=["POST"])
def api_resend_verification():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return api_err("err.email_empty")

    with _email_locks[email]:
        user = User.query.filter_by(email=email).first()
        if not user:
            return api_err("err.user_missing", 404)

        if user.email_verified and _device_trusted(user):
            return _login_json(user, {
                "ok": True,
                "direct_login": True,
                "remembered": True,
                "message": t_api("ok.device_login"),
            })

        denied = _deny_login_once_today(user)
        if denied:
            return denied

        if user.email_verified and not _is_beta_account(email):
            return jsonify({"ok": True, "message": t_api("ok.already_verified")})

        if _is_beta_account(email):
            user.verification_token = None
            user.email_verified = True
            return _login_json(user, {
                "ok": True,
                "beta_skip_verify": True,
                "dev_token": "任意",
                "message": t_api("ok.beta_any_code"),
            })

        if LOGIN_ONCE_PER_DAY and _email_sent_today(user):
            return _code_json(user, email, already=True)

        return _send_or_reuse_verification(user, email)


# ============================================================
# 问卷 API
# ============================================================


@app.route("/api/express-profile", methods=["POST"])
@login_required
def api_express_profile():
    """隐私模式：昵称 + 性别/取向 + 一段话进池；微信可选。"""
    user = get_current_user()
    if not user.email_verified:
        return api_err("err.need_verify")
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    gender = (data.get("gender") or "").strip()
    looking_for = (data.get("looking_for") or "").strip()
    bio = (data.get("bio") or "").strip()
    if not name:
        return api_err("err.express_name")
    if gender not in ("male", "female") or looking_for not in LOOKING_FOR_VALUES:
        return api_err("err.need_gender")
    if len(bio) < EXPRESS_BIO_MIN:
        return api_err("err.express_bio", n=EXPRESS_BIO_MIN)
    edu_err = apply_education_fields(user, data, required=True)
    if edu_err:
        return edu_err
    user.name = name[:32]
    user.gender = gender
    user.looking_for = looking_for
    user.bio = bio[:800]
    contact = (data.get("wechat_id") or "").strip()
    user.wechat_id = contact[:120] if contact else user.wechat_id
    if "cross_schools" in data:
        raw = data.get("cross_schools") or []
        if not isinstance(raw, list):
            return api_err("err.cross_list")
        if CROSS_SCHOOL_MATCHING_ENABLED:
            user.set_cross_schools(raw)
        else:
            user.set_cross_schools([])
    if "open_to_match" in data:
        user.open_to_match = bool(data.get("open_to_match"))
        if not user.open_to_match:
            user.opt_in_week = None
    vec, _ = build_express_vector(user.bio)
    user.feature_vector = vec
    user.profile_mode = "privacy"
    from invite import try_redeem_invite
    try_redeem_invite(user)
    db.session.commit()
    return jsonify({"ok": True, "message": t_api("ok.express_saved"), "user": user.to_dict()})


@app.route("/api/questionnaire", methods=["GET", "POST"])
@login_required
def api_questionnaire():
    """获取问卷题目 / 提交答案"""
    user = get_current_user()

    if request.method == "GET":
        return jsonify({
            "ok": True,
            "questions": QUESTIONS,
            "answers": user.answers,
            "important_qids": list(user.important_qids),
            "completed": user.questionnaire_completed(),
            "profile_mode": "privacy" if user.is_express() else "full",
        })

    # POST: 提交答案 + 生成特征向量
    data = request.get_json() or {}
    answers_raw = data.get("answers", {})
    if not isinstance(answers_raw, dict):
        return api_err("err.answers_format")
    valid_qids = {q["id"] for q in QUESTIONS}
    important_qids = set()
    for raw_qid in data.get("important_qids", []):
        try:
            qid = int(raw_qid)
        except (TypeError, ValueError):
            continue
        if qid in valid_qids:
            # 自由留言题不参与「很重要」加权
            qmeta = next((x for x in QUESTIONS if x["id"] == qid), None)
            if qmeta and qmeta.get("type") == "text":
                continue
            important_qids.add(qid)

    # 转换：前端传来的都是字符串键，统一成 int 键
    answers = {}
    for q in QUESTIONS:
        qid_str = str(q["id"])
        val = answers_raw.get(qid_str, answers_raw.get(q["id"]))
        if val is None:
            continue
        if q["type"] == "scale":
            try:
                answers[q["id"]] = max(1, min(5, int(val)))
            except (ValueError, TypeError):
                pass
        elif q["type"] == "multi":
            if isinstance(val, list):
                # 只保留合法选项，避免脏数据进入特征向量
                allowed = set(q.get("options") or [])
                clean = list(dict.fromkeys(x for x in val if x in allowed))
            elif isinstance(val, str):
                allowed = set(q.get("options") or [])
                parts = [x.strip() for x in val.replace("，", ",").split(",") if x.strip()]
                clean = list(dict.fromkeys(x for x in parts if x in allowed))
            else:
                clean = []

            # “不玩/不运动/暂不确定”等选项与其它选项互斥。
            exclusive = set(q.get("exclusive_options") or [])
            chosen_exclusive = next((x for x in clean if x in exclusive), None)
            answers[q["id"]] = [chosen_exclusive] if chosen_exclusive else clean
        elif q["type"] == "text":
            text = val if isinstance(val, str) else ("" if val is None else str(val))
            text = text.strip()
            max_len = int(q.get("max_length") or 2000)
            if text:
                answers[q["id"]] = text[:max_len]

    missing = []
    for q in QUESTIONS:
        if q.get("optional") or q["type"] == "text":
            continue
        val = answers.get(q["id"])
        if q["type"] == "scale" and val is None:
            missing.append(q["id"])
        elif q["type"] == "multi" and not val:
            missing.append(q["id"])
    if missing:
        required_n = sum(1 for q in QUESTIONS if not q.get("optional") and q["type"] != "text")
        return api_err(
            "err.answers_missing",
            n=required_n,
            ids=", ".join("Q" + str(x) for x in missing),
        )

    # 构建特征向量
    vec, dim_names = build_feature_vector(answers, important_qids)

    # 保存
    user.answers = answers
    user.feature_vector = vec
    user.important_qids = important_qids

    # 同时更新兴趣标签（从 multi 题中提取，去重）
    UserTag.query.filter_by(user_id=user.id).delete()
    seen_tags = set()
    for q in QUESTIONS:
        if q["type"] == "multi" and q["id"] in answers:
            for opt in answers[q["id"]]:
                if opt not in seen_tags:
                    seen_tags.add(opt)
                    db.session.add(UserTag(user_id=user.id, tag=opt))

    personality = build_love_personality(answers)
    user.mbti_report = personality
    user.profile_mode = "full"

    from invite import try_redeem_invite
    try_redeem_invite(user)
    db.session.commit()

    return jsonify({
        "ok": True,
        "message": t_api("ok.survey_saved"),
        "vector_dim": len(vec),
        "completed": user.questionnaire_completed(),
        "personality": personality,
        "mbti": personality,  # 兼容旧前端字段名
    })


# ============================================================
# 匹配 API
# ============================================================

@app.route("/api/match/status", methods=["GET"])
@login_required
def api_match_status():
    user = get_current_user()
    return jsonify({"ok": True, "quota": match_quota_status(user)})


@app.route("/api/me/mbti", methods=["GET"])
@login_required
def api_me_mbti():
    """恋爱人格报告（存 mbti_json）；旧 MBTI 缓存会按答案重算覆盖。"""
    user = get_current_user()
    if not user.answers:
        return api_err("err.need_questionnaire")
    report = user.mbti_report
    if not report or report.get("kind") != "love_personality":
        report = build_love_personality(user.answers)
        user.mbti_report = report
        db.session.commit()
    return jsonify({"ok": True, "mbti": report, "personality": report})


@app.route("/api/match", methods=["POST"])
@login_required
def api_match():
    """触发匹配（实时模式或批量模式）"""
    user = get_current_user()

    if not user.ready_to_match():
        if not user.email_verified:
            return api_err("err.need_verify")
        if not user.gender or user.looking_for not in LOOKING_FOR_VALUES:
            return api_err("err.need_gender")
        if (user.education_level or "") not in EDUCATION_LEVELS:
            return api_err("err.education")
        if user.is_express():
            return api_err("err.profile_incomplete")
        if not user.questionnaire_completed() or not user.feature_vector:
            return api_err("err.need_survey_submit")
        if not user.wechat_id:
            return api_err("err.need_wechat")
        return api_err("err.profile_incomplete")

    if not user.is_open_to_match():
        body, status = api_err("err.match_closed", 403)
        payload = body.get_json()
        payload["quota"] = match_quota_status(user)
        return jsonify(payload), status

    if not INSTANT_MATCH_ENABLED:
        body, status = api_err("err.weekly_only", 403)
        payload = body.get_json()
        payload["quota"] = match_quota_status(user)
        return jsonify(payload), status

    quota = match_quota_status(user)
    if quota["cooldown_seconds_left"] > 0:
        mins = max(1, quota["cooldown_seconds_left"] // 60)
        body, status = api_err("err.cooldown", 429, mins=mins, hours=MATCH_COOLDOWN_HOURS)
        payload = body.get_json()
        payload["quota"] = quota
        return jsonify(payload), status
    if quota["weekly_remaining"] <= 0:
        body, status = api_err(
            "err.weekly_cap", 429,
            n=quota["weekly_limit"], when=quota["next_batch_label"],
        )
        payload = body.get_json()
        payload["quota"] = quota
        return jsonify(payload), status

    # 通过冷却/周额度检查后立即落库冷却：失败也算一次尝试，防刷「暂未配对」邮件
    touch_instant_match_cooldown(user)

    if MATCH_DELAY_SECONDS > 0:
        time.sleep(MATCH_DELAY_SECONDS)

    mode = MATCH_MODE
    # 兼容旧配置名 realtime → one_to_one
    if mode == "realtime":
        mode = "one_to_one"

    pool_q_size_hint = User.query.filter(
        User.email_verified == True,
        User.feature_vector_json.isnot(None),
        User.gender.isnot(None),
    )
    if not (CROSS_SCHOOL_MATCHING_ENABLED and user.get_cross_schools()):
        pool_q_size_hint = pool_q_size_hint.filter(User.school == user.school)
    pool_size = pool_q_size_hint.count()
    candidates = eligible_candidates(user)

    if not candidates:
        msg = t_api("match.none_orient")
        if CROSS_SCHOOL_MATCHING_ENABLED and not user.get_cross_schools():
            msg += t_api("match.none_orient_cross")
        mail_ok, mail_info = notify_no_match(user, reason=msg)
        return jsonify({
            "ok": True,
            "matches": [],
            "message": msg,
            "total_candidates": 0,
            "pool_size": pool_size,
            "mail_sent": mail_ok,
            "mail_info": str(mail_info)[:120] if mail_info else None,
            "quota": match_quota_status(user),
            "explain": _match_explain_text(mode),
            "note": t_api("match.note"),
        })

    if mode == "batch":
        all_users = candidates + [user]
        results = batch_match_school(
            all_users,
            filter_same_gender=True,
            previous_pairs=previous_pair_keys([u.id for u in all_users]),
        )
        my_matches = [
            (a if b.id == user.id else b, s)
            for a, b, s in results
            if (a.id == user.id or b.id == user.id) and s >= MATCH_MIN_SCORE
        ]
        max_save = 1
    else:
        # 过门槛的候选按优先级交给 persist；硬性底线冲突时跳过并试下一个。
        # one_to_one：最终只落库 1 人；top_n：可多人（调试）。
        if mode == "top_n":
            top_n = max(1, MATCH_TOP_N)
            max_save = top_n
        else:
            top_n = max(len(candidates), 1)
            max_save = 1
        my_matches = real_time_match(
            user, candidates, top_n=top_n, min_score=MATCH_MIN_SCORE,
            previous_partner_ids=previous_partner_ids(user.id),
        )

    if not my_matches:
        msg = t_api("match.none_fit")
        mail_ok, mail_info = notify_no_match(user, reason=msg)
        return jsonify({
            "ok": True,
            "matches": [],
            "message": msg,
            "total_candidates": len(candidates),
            "pool_size": pool_size,
            "mail_sent": mail_ok,
            "mail_info": str(mail_info)[:120] if mail_info else None,
            "quota": match_quota_status(user),
            "explain": _match_explain_text(mode),
            "note": t_api("match.note"),
        })

    summary = persist_user_matches(
        user, my_matches, mode, get_mail_config(),
        weekly_new_limit=MATCH_WEEKLY_NEW_LIMIT,
        max_save=max_save,
    )
    saved = summary["saved"]

    if not saved:
        db_only = (
            summary.get("dealbreaker_skipped")
            and not summary.get("partner_quota_skipped")
            and not summary.get("low_score_skipped")
            and not summary.get("quota_skipped")
        )
        if db_only:
            msg = t_api("match.fail_db")
        else:
            parts = []
            if summary.get("partner_quota_skipped"):
                parts.append(t_api("match.rs.partner"))
            if summary.get("low_score_skipped"):
                parts.append(t_api("match.rs.score"))
            if summary.get("dealbreaker_skipped"):
                parts.append(t_api("match.rs.db"))
            if summary.get("quota_skipped"):
                parts.append(t_api("match.rs.quota"))
            reason = "；".join(parts) if parts else t_api("match.rs.none")
            if request_lang() in ("en", "pt"):
                reason = "; ".join(parts) if parts else t_api("match.rs.none")
            msg = t_api("match.fail", reason=reason)
        mail_ok, mail_info = notify_no_match(user, reason=msg)
        return jsonify({
            "ok": True,
            "matches": [],
            "message": msg,
            "total_candidates": len(candidates),
            "dealbreaker_skipped": summary["dealbreaker_skipped"],
            "quota_skipped": summary["quota_skipped"],
            "partner_quota_skipped": summary.get("partner_quota_skipped", 0),
            "low_score_skipped": summary.get("low_score_skipped", 0),
            "mail_sent": mail_ok,
            "mail_info": str(mail_info)[:120] if mail_info else None,
            "quota": match_quota_status(user),
            "explain": _match_explain_text(mode),
            "note": t_api("match.note"),
        })

    return jsonify({
        "ok": True,
        "mode": mode,
        "matches": [
            serialize_match_payload(u, s, insight, active=True)
            for u, s, insight in saved
        ],
        "total_candidates": len(candidates),
        "dealbreaker_skipped": summary["dealbreaker_skipped"],
        "updated_existing": summary["updated_existing"],
        "newly_notified": summary["newly_notified"],
        "quota_skipped": summary["quota_skipped"],
        "partner_quota_skipped": summary.get("partner_quota_skipped", 0),
        "low_score_skipped": summary.get("low_score_skipped", 0),
        "mail_ok_count": summary["mail_ok_count"],
        "mail_fail_count": summary["mail_fail_count"],
        "mail_details": summary.get("mail_details", []),
        "quota": match_quota_status(user),
        "explain": _match_explain_text(mode),
        "note": t_api("match.note"),
    })


@app.route("/api/match/opt-in", methods=["POST", "DELETE"])
@login_required
def api_match_opt_in():
    """预约 / 取消本周批量匹配。"""
    user = get_current_user()
    if not user.ready_to_match():
        return api_err("err.need_ready_optin")
    if not user.is_open_to_match():
        body, status = api_err("err.need_open_optin", 403)
        payload = body.get_json()
        payload["quota"] = match_quota_status(user)
        return jsonify(payload), status

    week = current_week_key()
    if request.method == "DELETE":
        if user.opt_in_week == week:
            user.opt_in_week = None
            db.session.commit()
        return jsonify({"ok": True, "opted_in": False, "quota": match_quota_status(user)})

    user.opt_in_week = week
    db.session.commit()
    return jsonify({
        "ok": True,
        "opted_in": True,
        "week_key": week,
        "message": t_api("ok.optin", when=match_quota_status(user)["next_batch_label"]),
        "quota": match_quota_status(user),
    })


@app.route("/api/matches", methods=["GET"])
@login_required
def api_get_matches():
    """默认只返回当前有效配对（一对一）；?all=1 可看已失效历史（不含微信号）。"""
    user = get_current_user()
    show_all = request.args.get("all") in ("1", "true", "yes")

    q = Match.query.filter(
        (Match.user1_id == user.id) | (Match.user2_id == user.id)
    )
    if not show_all:
        q = q.filter(Match.active.is_(True))
    records = q.order_by(Match.created_at.desc(), Match.score.desc()).all()

    results = []
    for m in records:
        other = m.user2 if m.user1_id == user.id else m.user1
        insight = json.loads(m.insight_json) if m.insight_json else {}
        # 空破冰或旧人机模板：重算一次并回写（仅 stale 时写，避免每请求都写）
        from icebreakers import is_stale_icebreaker_list
        ice = insight.get("icebreakers") or []
        needs_regen = is_stale_icebreaker_list(ice)
        if m.active and needs_regen:
            insight = get_compatibility_insight(
                user.feature_vector, other.feature_vector,
                user.answers, other.answers,
                score=m.score,
                seed=(m.user1_id, m.user2_id),
                my_school=user.school, their_school=other.school,
            )
            m.insight_json = json.dumps(insight, ensure_ascii=False)
            db.session.commit()
        item = serialize_match_payload(other, m.score, insight, active=bool(m.active))
        item["matched_at"] = m.created_at.isoformat() if m.created_at else None
        item["mode"] = m.mode
        item["notified"] = bool(m.notified)
        item["active"] = bool(m.active)
        results.append(item)

    return jsonify({
        "ok": True,
        "matches": results,
        "quota": match_quota_status(user),
        "note": t_api("match.list_note"),
    })


# ============================================================
# 用户信息 API
# ============================================================

@app.route("/api/me", methods=["GET", "PUT"])
@login_required
def api_me():
    user = get_current_user()

    if request.method == "GET":
        return jsonify({"ok": True, "user": user.to_dict()})

    # PUT: 更新基本信息（不含问卷）
    data = request.get_json() or {}
    user.name = (data.get("name") or "").strip() or user.name
    gender = (data.get("gender") or "").strip()
    if gender in ("male", "female"):
        user.gender = gender
    looking_for = (data.get("looking_for") or "").strip()
    if looking_for in LOOKING_FOR_VALUES:
        user.looking_for = looking_for
    edu_err = apply_education_fields(user, data, required=False)
    if edu_err:
        return edu_err
    contact = (data.get("wechat_id") or "").strip()
    if "wechat_id" in data:
        if not contact and not user.is_express():
            return api_err("err.wechat_required")
        user.wechat_id = contact[:120] if contact else None
    if "bio" in data:
        bio = (data.get("bio") or "").strip()
        if user.is_express() and len(bio) < EXPRESS_BIO_MIN:
            return api_err("err.express_bio", n=EXPRESS_BIO_MIN)
        if bio:
            user.bio = bio[:800]
    if "cross_schools" in data:
        raw = data.get("cross_schools")
        if raw is None:
            raw = []
        if not isinstance(raw, list):
            return api_err("err.cross_list")
        if not CROSS_SCHOOL_MATCHING_ENABLED:
            user.set_cross_schools([])
        else:
            user.set_cross_schools(raw)
    elif "allow_cross_school" in data:
        # 兼容旧前端：true = 勾选除本校外全部学校
        if data.get("allow_cross_school") and CROSS_SCHOOL_MATCHING_ENABLED:
            user.set_cross_schools([s for s in SCHOOL_DOMAINS.keys() if s != user.school])
        else:
            user.set_cross_schools([])
    if "open_to_match" in data:
        user.open_to_match = bool(data.get("open_to_match"))
        if not user.open_to_match:
            user.opt_in_week = None
    from invite import try_redeem_invite
    try_redeem_invite(user)
    db.session.commit()
    return jsonify({"ok": True, "user": user.to_dict()})


@app.route("/api/users/search", methods=["GET"])
@login_required
def api_users_search():
    """按昵称或邮箱精确搜索可拉黑对象（不返回联系方式）。"""
    user = get_current_user()
    if not user.ready_to_match():
        return api_err("err.need_ready_optin")
    q = (request.args.get("q") or "").strip()
    if "@" in q:
        if len(q) < 5:
            return api_err("err.search_q")
    elif len(q) < 2:
        return api_err("err.search_q")

    query = User.query.filter(
        User.id != user.id,
        User.email_verified == True,
        User.name.isnot(None),
    )
    if "@" in q:
        query = query.filter(User.email == q.lower())
    else:
        query = query.filter(User.name.ilike(f"%{q}%"))
        # 默认同校；开了跨校总闸则全库可搜（仍需点选确认）
        if not CROSS_SCHOOL_MATCHING_ENABLED:
            query = query.filter(User.school == user.school)

    rows = query.order_by(User.school, User.name).limit(20).all()
    blocked = {r.blocked_user_id for r in Blocklist.query.filter_by(user_id=user.id).all()}
    return jsonify({
        "ok": True,
        "results": [
            {
                "id": u.id,
                "name": u.name,
                "school": u.school,
                "gender": u.gender,
                "already_blocked": u.id in blocked,
            }
            for u in rows
        ],
    })


@app.route("/api/blocklist", methods=["GET", "POST", "DELETE"])
@login_required
def api_blocklist():
    """黑名单：GET 列表；POST 添加；DELETE 移除。"""
    user = get_current_user()

    if request.method == "GET":
        rows = Blocklist.query.filter_by(user_id=user.id).order_by(Blocklist.created_at.desc()).all()
        items = []
        for r in rows:
            other = r.blocked
            items.append({
                "id": other.id if other else r.blocked_user_id,
                "name": other.name if other else "（已注销）",
                "school": other.school if other else None,
                "gender": other.gender if other else None,
                "blocked_at": r.created_at.isoformat() if r.created_at else None,
            })
        return jsonify({"ok": True, "blocklist": items})

    data = request.get_json(silent=True) or {}
    target_id = data.get("user_id") or request.args.get("user_id")
    try:
        target_id = int(target_id)
    except (TypeError, ValueError):
        return api_err("err.block_pick")

    if target_id == user.id:
        return api_err("err.block_self")

    target = User.query.get(target_id)
    if not target or not target.email_verified:
        return api_err("err.user_missing", 404)

    if request.method == "DELETE":
        Blocklist.query.filter_by(user_id=user.id, blocked_user_id=target_id).delete()
        db.session.commit()
        return jsonify({"ok": True, "blocked": False})

    existing = Blocklist.query.filter_by(user_id=user.id, blocked_user_id=target_id).first()
    if not existing:
        db.session.add(Blocklist(user_id=user.id, blocked_user_id=target_id))

    # 若有有效配对，降为 inactive（不再展示对方微信）
    active = Match.query.filter(
        ((Match.user1_id == user.id) & (Match.user2_id == target_id)) |
        ((Match.user1_id == target_id) & (Match.user2_id == user.id)),
        Match.active.is_(True),
    ).all()
    for m in active:
        m.active = False

    db.session.commit()
    return jsonify({
        "ok": True,
        "blocked": True,
        "message": t_api("ok.blocked", name=target.name or target.email),
        "deactivated_matches": len(active),
    })


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """退出当前会话。设备信任 cookie 保留 7 天，再输入同一邮箱可免验证码。"""
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/health", methods=["GET"])
def api_health():
    """运维探活"""
    try:
        db.session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return jsonify({
        "ok": db_ok,
        "service": "campus-match",
        "mail_enabled": MAIL_ENABLED,
        "match_mode": MATCH_MODE,
        "debug": FLASK_DEBUG,
        "next_batch_at": next_batch_datetime().isoformat(timespec="minutes"),
        "batch_scheduler": BATCH_SCHEDULER_ENABLED,
    }), (200 if db_ok else 503)


@app.route("/api/admin/batch-run", methods=["POST"])
def api_admin_batch_run():
    """手动触发全校批量匹配。需要 Header: X-Admin-Secret"""
    if not ADMIN_SECRET:
        return api_err("err.admin_secret_missing", 403)
    secret = request.headers.get("X-Admin-Secret") or (request.get_json(silent=True) or {}).get("secret")
    if secret != ADMIN_SECRET:
        return api_err("err.admin_secret_bad", 403)
    results = run_batch_all(get_mail_config())
    return jsonify({"ok": True, "results": results})


@app.route("/api/admin/nudge-incomplete", methods=["POST"])
def api_admin_nudge_incomplete():
    """催填未完成问卷。需要 Header: X-Admin-Secret；默认 dry_run，send=true 才发信。"""
    if not ADMIN_SECRET:
        return api_err("err.admin_secret_missing", 403)
    body = request.get_json(silent=True) or {}
    secret = request.headers.get("X-Admin-Secret") or body.get("secret")
    if secret != ADMIN_SECRET:
        return api_err("err.admin_secret_bad", 403)
    if not MAIL_INCOMPLETE_NUDGE_ENABLED:
        return jsonify({
            "ok": False,
            "error": "MAIL_INCOMPLETE_NUDGE_ENABLED=false",
        }), 403
    dry_run = not bool(body.get("send"))
    try:
        days = int(body.get("days") or INCOMPLETE_NUDGE_COOLDOWN_DAYS)
    except (TypeError, ValueError):
        days = INCOMPLETE_NUDGE_COOLDOWN_DAYS
    try:
        limit = int(body.get("limit") or 200)
    except (TypeError, ValueError):
        limit = 200
    result = send_incomplete_nudges(
        get_mail_config(),
        cooldown_days=days,
        limit=limit,
        dry_run=dry_run,
    )
    return jsonify({"ok": True, "result": result})


# ============================================================
# 学校信息 API
# ============================================================

@app.route("/api/school/stats", methods=["GET"])
def api_school_stats():
    """获取各学校注册人数统计"""
    from sqlalchemy import func
    stats = db.session.query(
        User.school, func.count(User.id)
    ).filter(User.email_verified == True).group_by(User.school).all()

    return jsonify({
        "ok": True,
        "schools": {school: count for school, count in stats},
        "total": sum(count for _, count in stats),
    })


@app.route("/api/school/tags/<school_name>", methods=["GET"])
def api_school_tags(school_name):
    """获取某学校的流行标签（冷启动推荐）"""
    from crawler import get_school_tags
    tags = get_school_tags(school_name)
    return jsonify({"ok": True, "school": school_name, "tags": tags})


# ============================================================
# 初始化
# ============================================================

def ensure_schema():
    """create_all + 轻量迁移（looking_for / active）并清理旧 Top-N 多配对。"""
    db.create_all()
    try:
        user_cols = {c["name"] for c in inspect(db.engine).get_columns("users")}
        match_cols = {c["name"] for c in inspect(db.engine).get_columns("matches")}
    except Exception:
        return

    if "looking_for" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN looking_for VARCHAR(16)"))
        db.session.commit()
        print("[CampusMatch] migrated: users.looking_for")

    if "opt_in_week" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN opt_in_week VARCHAR(16)"))
        db.session.commit()
        print("[CampusMatch] migrated: users.opt_in_week")

    if "quota_bonus" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN quota_bonus INTEGER DEFAULT 0"))
        db.session.commit()
        print("[CampusMatch] migrated: users.quota_bonus")

    if "quota_bonus_week" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN quota_bonus_week VARCHAR(16)"))
        db.session.commit()
        print("[CampusMatch] migrated: users.quota_bonus_week")

    if "invite_code" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN invite_code VARCHAR(16)"))
        db.session.commit()
        print("[CampusMatch] migrated: users.invite_code")
    try:
        db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_invite_code ON users (invite_code)"))
        db.session.commit()
    except Exception:
        db.session.rollback()
    if "invited_by_id" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN invited_by_id INTEGER"))
        db.session.commit()
        print("[CampusMatch] migrated: users.invited_by_id")
    if "invite_bound_at" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN invite_bound_at DATETIME"))
        db.session.commit()
        print("[CampusMatch] migrated: users.invite_bound_at")
    if "invite_redeemed_at" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN invite_redeemed_at DATETIME"))
        db.session.commit()
        print("[CampusMatch] migrated: users.invite_redeemed_at")
    if "invite_quota_week" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN invite_quota_week VARCHAR(16)"))
        db.session.commit()
        print("[CampusMatch] migrated: users.invite_quota_week")

    if "allow_cross_school" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN allow_cross_school BOOLEAN DEFAULT 0"))
        db.session.commit()
        print("[CampusMatch] migrated: users.allow_cross_school")

    if "cross_schools_json" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN cross_schools_json TEXT"))
        db.session.commit()
        print("[CampusMatch] migrated: users.cross_schools_json")

    if "open_to_match" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN open_to_match BOOLEAN DEFAULT 1"))
        db.session.execute(text("UPDATE users SET open_to_match = 1 WHERE open_to_match IS NULL"))
        db.session.commit()
        print("[CampusMatch] migrated: users.open_to_match")

    if "mbti_json" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN mbti_json TEXT"))
        db.session.commit()
        print("[CampusMatch] migrated: users.mbti_json")

    if "last_login_at" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))
        db.session.commit()
        print("[CampusMatch] migrated: users.last_login_at")

    if "incomplete_nudge_at" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN incomplete_nudge_at DATETIME"))
        db.session.commit()
        print("[CampusMatch] migrated: users.incomplete_nudge_at")

    if "profile_mode" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN profile_mode VARCHAR(16) DEFAULT 'full'"))
        db.session.execute(text("UPDATE users SET profile_mode = 'full' WHERE profile_mode IS NULL"))
        db.session.commit()
        print("[CampusMatch] migrated: users.profile_mode")

    if "education_level" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN education_level VARCHAR(16)"))
        db.session.commit()
        print("[CampusMatch] migrated: users.education_level")

    if "allow_cross_degree" not in user_cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN allow_cross_degree BOOLEAN DEFAULT 0"))
        db.session.commit()
        print("[CampusMatch] migrated: users.allow_cross_degree")

    if "icebreaker_followup_sent" not in match_cols:
        db.session.execute(text("ALTER TABLE matches ADD COLUMN icebreaker_followup_sent BOOLEAN DEFAULT 0"))
        db.session.execute(text(
            "UPDATE matches SET icebreaker_followup_sent = 0 WHERE icebreaker_followup_sent IS NULL"
        ))
        db.session.commit()
        print("[CampusMatch] migrated: matches.icebreaker_followup_sent")

    if "active" not in match_cols:
        db.session.execute(text("ALTER TABLE matches ADD COLUMN active BOOLEAN DEFAULT 1"))
        db.session.execute(text("UPDATE matches SET active = 1 WHERE active IS NULL"))
        db.session.commit()
        print("[CampusMatch] migrated: matches.active")

    _cleanup_one_to_one_matches()


def _cleanup_one_to_one_matches():
    """每个用户只保留 1 条有效配对（优先最近、分数高），其余 active=False。"""
    from sqlalchemy import or_

    user_ids = [r[0] for r in db.session.query(User.id).all()]
    changed = 0
    for uid in user_ids:
        rows = (
            Match.query.filter(
                or_(Match.user1_id == uid, Match.user2_id == uid),
                Match.active.is_(True),
            )
            .order_by(Match.created_at.desc(), Match.score.desc())
            .all()
        )
        if len(rows) <= 1:
            continue
        keep = rows[0]
        keep.active = True
        for m in rows[1:]:
            if m.active:
                m.active = False
                changed += 1
    if changed:
        db.session.commit()
        print(f"[CampusMatch] one-to-one cleanup: deactivated {changed} old matches")


def init_db():
    with app.app_context():
        ensure_schema()
        print("[CampusMatch v2] DB initialized")


def start_batch_scheduler():
    """后台线程：破冰随访（按小时，可关）；可选每周批量匹配。"""
    # Flask debug 重载会起两个进程，只在主进程开调度
    if FLASK_DEBUG and not os_environ_is_reloader_main():
        return

    if ICEBREAKER_FOLLOWUP_ENABLED:
        from email_service import send_due_icebreaker_followups

        def _followup_loop():
            while True:
                try:
                    with app.app_context():
                        n = send_due_icebreaker_followups(get_mail_config())
                        if n:
                            print(f"[followup] 破冰随访已处理 {n} 对")
                except Exception as e:
                    print(f"[followup] 失败: {e}")
                time.sleep(3600)

        ft = threading.Thread(target=_followup_loop, name="icebreaker-followup", daemon=True)
        ft.start()
        print(f"  破冰随访线程已启动（配对后第 {ICEBREAKER_FOLLOWUP_DAYS} 天）")
    else:
        print("  破冰随访已关闭（ICEBREAKER_FOLLOWUP_ENABLED=false）")

    if not BATCH_SCHEDULER_ENABLED:
        return

    def _run():
        with app.app_context():
            schedule_loop(get_mail_config)

    t = threading.Thread(target=_run, name="batch-scheduler", daemon=True)
    t.start()
    print(f"  批量调度线程已启动 → {WEEKDAY_LABELS[BATCH_MATCH_DAY]} {BATCH_MATCH_HOUR}:00")


def os_environ_is_reloader_main():
    import os
    return os.environ.get("WERKZEUG_RUN_MAIN") == "true"


if __name__ == "__main__":
    init_db()
    print("  CampusMatch v2 启动!")
    print(f"  模式: {MATCH_MODE} · {WEEKDAY_LABELS[BATCH_MATCH_DAY]} {BATCH_MATCH_HOUR}:00 批量")
    print(f"  额度: 每周双向 ≤{MATCH_WEEKLY_NEW_LIMIT} · 门槛 {int(round(MATCH_MIN_SCORE*100))}% · 冷却 {MATCH_COOLDOWN_HOURS}h")
    print(f"  Debug: {FLASK_DEBUG}")
    print(f"  支持学校: {', '.join(SCHOOL_DOMAINS.keys())}")
    print(f"  邮件: {'真实发送' if MAIL_ENABLED else '开发模式'}")
    if USING_DEFAULT_SECRET_KEY:
        print("  警告: 正在使用仓库默认 SECRET_KEY，会话 cookie 可被伪造。请在 .env 设置随机 SECRET_KEY。")
        if not FLASK_DEBUG:
            raise SystemExit("Refusing to start: SECRET_KEY is the repository default")
    start_batch_scheduler()
    app.run(debug=FLASK_DEBUG, host=os.environ.get("FLASK_HOST", "0.0.0.0"), port=int(os.environ.get("FLASK_PORT", "5000")))
