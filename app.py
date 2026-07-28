"""
CampusMatch v2 — 校园恋爱匹配系统
=====================================
参考 SJTU Date / FDU Date / MatchUs 已验证模式：
  深度问卷 → 特征向量 → 余弦相似度 → 匈牙利全局匹配 → 邮件通知
"""

import time, json, threading
from collections import defaultdict, deque
from datetime import datetime
from functools import wraps

from flask import Flask, request, session, jsonify, render_template, redirect, url_for
from sqlalchemy import inspect, text

from config import (
    SECRET_KEY, FLASK_DEBUG, SQLALCHEMY_DATABASE_URI, PUBLIC_URL,
    SCHOOL_DOMAINS, MATCH_MODE, MATCH_TOP_N, MATCH_MIN_SCORE,
    MATCH_DELAY_SECONDS, VERIFICATION_EXPIRE_SECONDS,
    REGISTER_RATE_LIMIT, REGISTER_RATE_WINDOW,
    MATCH_WEEKLY_NEW_LIMIT, MATCH_COOLDOWN_HOURS,
    BATCH_MATCH_DAY, BATCH_MATCH_HOUR, BATCH_SCHEDULER_ENABLED,
    ADMIN_SECRET, WEEKDAY_LABELS,
    MAIL_ENABLED, MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM,
)
from models import db, User, UserTag, Match
from questionnaire import QUESTIONS, build_feature_vector
from matcher import real_time_match, batch_match_school, orientation_compatible
from email_service import send_verification_email, send_match_result_email
from batch_job import (
    persist_user_matches, count_new_matches_this_week,
    next_batch_datetime, run_batch_all, schedule_loop,
)

# ---- App Factory ----
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if PUBLIC_URL.startswith("https://"):
    app.config["SESSION_COOKIE_SECURE"] = True
db.init_app(app)

# 邮箱 → 近期请求时间戳（进程内限流，MVP 够用）
_register_hits = defaultdict(deque)


def get_mail_config():
    return {
        "enabled": MAIL_ENABLED, "server": MAIL_SERVER, "port": MAIL_PORT,
        "username": MAIL_USERNAME, "password": MAIL_PASSWORD, "mail_from": MAIL_FROM,
        "public_url": PUBLIC_URL,
    }


# ---- Helpers ----

def get_school_from_email(email):
    email = email.strip().lower()
    domain = email.split("@")[-1] if "@" in email else ""
    for school, domains in SCHOOL_DOMAINS.items():
        if domain in domains:
            return school
    return None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "请先登录"}), 401
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    user_id = session.get("user_id")
    if user_id:
        return db.session.get(User, user_id)
    return None


def check_register_rate(email):
    """同一邮箱在窗口内发送验证码次数限制。返回 (ok, error_msg)。"""
    now = time.time()
    key = email.strip().lower()
    q = _register_hits[key]
    while q and now - q[0] > REGISTER_RATE_WINDOW:
        q.popleft()
    if len(q) >= REGISTER_RATE_LIMIT:
        return False, f"发送过于频繁，请 {REGISTER_RATE_WINDOW // 60} 分钟后再试"
    q.append(now)
    return True, None


LOOKING_FOR_VALUES = {"male", "female", "both"}


def match_quota_status(user):
    """计算冷却 / 本周额度，供页面与 API 使用。"""
    used = count_new_matches_this_week(user.id)
    remaining = max(0, MATCH_WEEKLY_NEW_LIMIT - used)
    cooldown_left = 0
    if user.last_matched_at and MATCH_COOLDOWN_HOURS > 0:
        elapsed = (datetime.utcnow() - user.last_matched_at).total_seconds()
        need = MATCH_COOLDOWN_HOURS * 3600
        if elapsed < need:
            cooldown_left = int(need - elapsed)
    nxt = next_batch_datetime()
    return {
        "weekly_limit": MATCH_WEEKLY_NEW_LIMIT,
        "weekly_used": used,
        "weekly_remaining": remaining,
        "cooldown_hours": MATCH_COOLDOWN_HOURS,
        "cooldown_seconds_left": cooldown_left,
        "can_match_now": remaining > 0 and cooldown_left <= 0,
        "next_batch_at": nxt.isoformat(timespec="minutes"),
        "next_batch_label": f"每{WEEKDAY_LABELS[BATCH_MATCH_DAY]} {BATCH_MATCH_HOUR}:00",
        "match_mode": MATCH_MODE,
    }


# ============================================================
# 页面路由
# ============================================================

@app.route("/")
def index():
    user = get_current_user()
    if user:
        if not user.email_verified:
            return redirect(url_for("verify_page"))
        if not user.questionnaire_completed():
            return redirect(url_for("questionnaire_page"))
        return redirect(url_for("matches_page"))
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
        return redirect(url_for("questionnaire_page"))
    return render_template("verify.html", email=user.email)


@app.route("/questionnaire")
@login_required
def questionnaire_page():
    user = get_current_user()
    if not user.email_verified:
        return redirect(url_for("verify_page"))
    return render_template("questionnaire.html", user=user, questions=QUESTIONS)


@app.route("/matches")
@login_required
def matches_page():
    user = get_current_user()
    if not user.questionnaire_completed():
        return redirect(url_for("questionnaire_page"))
    return render_template(
        "matches.html",
        user=user,
        quota=match_quota_status(user),
    )


# ============================================================
# Auth API
# ============================================================

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    if not email or "@" not in email:
        return jsonify({"ok": False, "error": "请输入有效的邮箱地址"}), 400

    school = get_school_from_email(email)
    if not school:
        return jsonify({
            "ok": False,
            "error": "暂不支持该学校邮箱。目前支持: " + "、".join(SCHOOL_DOMAINS.keys()),
        }), 400

    ok_rate, rate_err = check_register_rate(email)
    if not ok_rate:
        return jsonify({"ok": False, "error": rate_err}), 429

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, school=school)
        db.session.add(user)
        db.session.flush()

    token = user.generate_token()
    db.session.commit()

    mail_ok, info = send_verification_email(email, token, get_mail_config())
    # 邮件失败仍允许进入验证步骤（开发/收件箱拒信时用页面展示验证码）
    return jsonify({
        "ok": True,
        "mail_sent": mail_ok,
        "message": f"验证码已发送至 {email}" if mail_ok else f"邮件发送失败，请使用页面验证码。详情: {info}",
        "dev_token": None if (mail_ok and MAIL_ENABLED) else token,
    })


@app.route("/api/verify", methods=["POST"])
def api_verify():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip()
    token = (data.get("token") or "").strip().upper()

    if not email or not token:
        return jsonify({"ok": False, "error": "邮箱和验证码不能为空"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"ok": False, "error": "用户不存在"}), 404

    # 已验证用户直接登录
    if user.email_verified:
        session["user_id"] = user.id
        return jsonify({"ok": True, "message": "已登录"})

    if user.verification_token != token:
        return jsonify({"ok": False, "error": "验证码错误"}), 400

    if user.verification_sent_at:
        elapsed = (datetime.utcnow() - user.verification_sent_at).total_seconds()
        if elapsed > VERIFICATION_EXPIRE_SECONDS:
            return jsonify({"ok": False, "error": "验证码已过期"}), 400

    user.email_verified = True
    user.verification_token = None
    db.session.commit()

    session["user_id"] = user.id
    return jsonify({"ok": True, "message": "验证成功！"})


@app.route("/api/resend-verification", methods=["POST"])
def api_resend_verification():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"ok": False, "error": "用户不存在"}), 404
    if user.email_verified:
        return jsonify({"ok": True, "message": "已验证"})

    ok_rate, rate_err = check_register_rate(email)
    if not ok_rate:
        return jsonify({"ok": False, "error": rate_err}), 429

    token = user.generate_token()
    db.session.commit()
    ok, _ = send_verification_email(email, token, get_mail_config())
    return jsonify({
        "ok": ok,
        "dev_token": token if not (ok and MAIL_ENABLED) else None,
    })


# ============================================================
# 问卷 API
# ============================================================

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
        })

    # POST: 提交答案 + 生成特征向量
    data = request.get_json() or {}
    answers_raw = data.get("answers", {})
    important_qids = set(data.get("important_qids", []))

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
                answers[q["id"]] = [x for x in val if x in allowed]
            elif isinstance(val, str):
                allowed = set(q.get("options") or [])
                parts = [x.strip() for x in val.replace(",", "，").split(",") if x.strip()]
                answers[q["id"]] = [x for x in parts if x in allowed]

    if len(answers) < 20:
        return jsonify({"ok": False, "error": f"请至少完成 20 题（当前 {len(answers)} 题）"}), 400

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

    db.session.commit()

    return jsonify({
        "ok": True,
        "message": "问卷已保存",
        "vector_dim": len(vec),
        "completed": user.questionnaire_completed(),
    })


# ============================================================
# 匹配 API
# ============================================================

@app.route("/api/match/status", methods=["GET"])
@login_required
def api_match_status():
    user = get_current_user()
    return jsonify({"ok": True, "quota": match_quota_status(user)})


@app.route("/api/match", methods=["POST"])
@login_required
def api_match():
    """触发匹配（实时模式或批量模式）"""
    user = get_current_user()

    if not user.ready_to_match():
        if not user.email_verified:
            return jsonify({"ok": False, "error": "请先验证邮箱"}), 400
        if not user.questionnaire_completed() or not user.feature_vector:
            return jsonify({"ok": False, "error": "请先完成问卷并提交"}), 400
        if not user.gender or user.looking_for not in LOOKING_FOR_VALUES:
            return jsonify({"ok": False, "error": "请先在问卷页设置性别与择偶取向"}), 400
        if not user.wechat_id:
            return jsonify({"ok": False, "error": "请先填写微信号"}), 400
        return jsonify({"ok": False, "error": "资料不完整，请返回问卷页补全"}), 400

    quota = match_quota_status(user)
    if quota["cooldown_seconds_left"] > 0:
        mins = max(1, quota["cooldown_seconds_left"] // 60)
        return jsonify({
            "ok": False,
            "error": f"匹配冷却中，请约 {mins} 分钟后再试（冷却 {MATCH_COOLDOWN_HOURS} 小时）",
            "quota": quota,
        }), 429
    if quota["weekly_remaining"] <= 0:
        return jsonify({
            "ok": False,
            "error": f"本周新建匹配已达上限（{MATCH_WEEKLY_NEW_LIMIT} 个）。可查看历史结果，或等下周 / {quota['next_batch_label']} 批量匹配。",
            "quota": quota,
        }), 429

    if MATCH_DELAY_SECONDS > 0:
        time.sleep(MATCH_DELAY_SECONDS)

    mode = MATCH_MODE
    if request.is_json:
        body = request.get_json(silent=True) or {}
        mode = body.get("mode", MATCH_MODE)

    pool = User.query.filter(
        User.school == user.school,
        User.id != user.id,
        User.email_verified == True,
        User.feature_vector_json.isnot(None),
        User.gender.isnot(None),
    ).all()
    candidates = [c for c in pool if orientation_compatible(user, c)]

    if not candidates:
        return jsonify({
            "ok": True,
            "matches": [],
            "message": "当前学校暂无符合你择偶取向的可匹配用户",
            "total_candidates": 0,
            "pool_size": len(pool),
            "quota": match_quota_status(user),
            "note": "结果以本页为准；邮件仅作通知，发送失败不影响查看。",
        })

    if mode == "batch":
        all_users = candidates + [user]
        results = batch_match_school(all_users, filter_same_gender=True)
        my_matches = [
            (a if b.id == user.id else b, s)
            for a, b, s in results
            if a.id == user.id or b.id == user.id
        ]
    else:
        my_matches = real_time_match(
            user, candidates, top_n=MATCH_TOP_N, min_score=MATCH_MIN_SCORE
        )

    summary = persist_user_matches(
        user, my_matches, mode, get_mail_config(),
        weekly_new_limit=MATCH_WEEKLY_NEW_LIMIT,
    )
    saved = summary["saved"]

    return jsonify({
        "ok": True,
        "mode": mode,
        "matches": [
            {
                "name": u.name,
                "gender": u.gender,
                "wechat_id": u.wechat_id,
                "score": s,
                "strengths": insight.get("strengths", [])[:3],
                "differences": insight.get("differences", [])[:3],
                "differences_count": insight.get("total_differences", 0),
            }
            for u, s, insight in saved
        ],
        "total_candidates": len(candidates),
        "dealbreaker_skipped": summary["dealbreaker_skipped"],
        "updated_existing": summary["updated_existing"],
        "newly_notified": summary["newly_notified"],
        "quota_skipped": summary["quota_skipped"],
        "mail_ok_count": summary["mail_ok_count"],
        "mail_fail_count": summary["mail_fail_count"],
        "quota": match_quota_status(user),
        "note": "结果以本页为准；邮件仅作通知，发送失败不影响查看。",
    })


@app.route("/api/matches", methods=["GET"])
@login_required
def api_get_matches():
    user = get_current_user()
    records = Match.query.filter(
        (Match.user1_id == user.id) | (Match.user2_id == user.id)
    ).order_by(Match.score.desc()).all()

    results = []
    for m in records:
        other = m.user2 if m.user1_id == user.id else m.user1
        insight = json.loads(m.insight_json) if m.insight_json else {}
        results.append({
            "name": other.name,
            "gender": other.gender,
            "school": other.school,
            "wechat_id": other.wechat_id,
            "score": m.score,
            "strengths": insight.get("strengths", [])[:3],
            "differences": insight.get("differences", [])[:3],
            "differences_count": insight.get("total_differences", 0),
            "matched_at": m.created_at.isoformat() if m.created_at else None,
            "mode": m.mode,
            "notified": bool(m.notified),
        })

    return jsonify({
        "ok": True,
        "matches": results,
        "quota": match_quota_status(user),
        "note": "结果以本页为准；邮件仅作通知。",
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
    user.wechat_id = (data.get("wechat_id") or "").strip() or user.wechat_id
    user.bio = (data.get("bio") or "").strip() or user.bio
    db.session.commit()
    return jsonify({"ok": True, "user": user.to_dict()})


@app.route("/api/logout", methods=["POST"])
def api_logout():
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
        return jsonify({"ok": False, "error": "未配置 ADMIN_SECRET，拒绝执行"}), 403
    secret = request.headers.get("X-Admin-Secret") or (request.get_json(silent=True) or {}).get("secret")
    if secret != ADMIN_SECRET:
        return jsonify({"ok": False, "error": "密钥错误"}), 403
    results = run_batch_all(get_mail_config())
    return jsonify({"ok": True, "results": results})


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
    """create_all + 轻量迁移（SQLite 补 looking_for 列）"""
    db.create_all()
    try:
        cols = {c["name"] for c in inspect(db.engine).get_columns("users")}
    except Exception:
        return
    if "looking_for" not in cols:
        db.session.execute(text("ALTER TABLE users ADD COLUMN looking_for VARCHAR(16)"))
        db.session.commit()
        print("[CampusMatch] migrated: users.looking_for")


def init_db():
    with app.app_context():
        ensure_schema()
        print("[CampusMatch v2] DB initialized")


def start_batch_scheduler():
    """可选：进程内后台线程等待每周批量匹配时刻。"""
    if not BATCH_SCHEDULER_ENABLED:
        return
    # Flask debug 重载会起两个进程，只在主进程开调度
    if FLASK_DEBUG and not os_environ_is_reloader_main():
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
    print(f"  模式: {'批量匹配' if MATCH_MODE == 'batch' else '实时匹配'} · {WEEKDAY_LABELS[BATCH_MATCH_DAY]} {BATCH_MATCH_HOUR}:00 批量")
    print(f"  额度: 每周新建 ≤{MATCH_WEEKLY_NEW_LIMIT} · 冷却 {MATCH_COOLDOWN_HOURS}h")
    print(f"  Debug: {FLASK_DEBUG}")
    print(f"  支持学校: {', '.join(SCHOOL_DOMAINS.keys())}")
    print(f"  邮件: {'真实发送' if MAIL_ENABLED else '开发模式'}")
    start_batch_scheduler()
    app.run(debug=FLASK_DEBUG, host="127.0.0.1", port=5000)
