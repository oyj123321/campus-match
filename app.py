"""
CampusMatch v2 — 校园恋爱匹配系统
=====================================
参考 SJTU Date / FDU Date / MatchUs 已验证模式：
  深度问卷 → 特征向量 → 余弦相似度 → 匈牙利全局匹配 → 邮件通知
"""

import time, json
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, session, jsonify, render_template, redirect, url_for
from sqlalchemy import inspect, text

from config import (
    SECRET_KEY, FLASK_DEBUG, SQLALCHEMY_DATABASE_URI, PUBLIC_URL,
    SCHOOL_DOMAINS, MATCH_MODE, MATCH_TOP_N, MATCH_MIN_SCORE,
    MATCH_DELAY_SECONDS, VERIFICATION_EXPIRE_SECONDS,
    REGISTER_RATE_LIMIT, REGISTER_RATE_WINDOW,
    MAIL_ENABLED, MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM,
)
from models import db, User, UserTag, Match
from questionnaire import (
    QUESTIONS, build_feature_vector, check_dealbreakers,
    get_compatibility_insight,
)
from matcher import real_time_match, batch_match_school, orientation_compatible
from email_service import send_verification_email, send_match_result_email

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
    return render_template("index.html", schools=SCHOOL_DOMAINS)


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
    return render_template("matches.html", user=user)


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
        if not user.gender or user.effective_looking_for() not in LOOKING_FOR_VALUES:
            return jsonify({"ok": False, "error": "请先在问卷页设置性别与择偶取向"}), 400
        if not user.wechat_id:
            return jsonify({"ok": False, "error": "请先填写微信号"}), 400
        return jsonify({"ok": False, "error": "资料不完整，请返回问卷页补全"}), 400

    if MATCH_DELAY_SECONDS > 0:
        time.sleep(MATCH_DELAY_SECONDS)

    mode = MATCH_MODE
    if request.is_json:
        body = request.get_json(silent=True) or {}
        mode = body.get("mode", MATCH_MODE)

    # 同校已验证候选人，再按双向择偶取向过滤
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
        })

    if mode == "batch":
        all_users = candidates + [user]
        results = batch_match_school(all_users, filter_same_gender=True)
        my_matches = [(a if b.id == user.id else b, s) for a, b, s in results if a.id == user.id or b.id == user.id]
    else:
        my_matches = real_time_match(user, candidates, top_n=MATCH_TOP_N, min_score=MATCH_MIN_SCORE)

    # 保存匹配记录 + 发送邮件
    mail_cfg = get_mail_config()
    saved = []
    to_notify = []  # 仅新建立的匹配发邮件
    skipped_dealbreaker = 0
    updated_existing = 0

    for matched_user, score in my_matches:
        dealbreakers = check_dealbreakers(user.answers, matched_user.answers)
        if dealbreakers:
            skipped_dealbreaker += 1
            continue

        insight = get_compatibility_insight(
            user.feature_vector, matched_user.feature_vector,
            user.answers, matched_user.answers,
        )

        existing = Match.query.filter(
            ((Match.user1_id == user.id) & (Match.user2_id == matched_user.id)) |
            ((Match.user1_id == matched_user.id) & (Match.user2_id == user.id))
        ).first()

        if existing:
            existing.score = score
            existing.mode = mode
            existing.insight_json = json.dumps(insight, ensure_ascii=False)
            updated_existing += 1
            saved.append((matched_user, score, insight))
            continue

        m = Match(
            user1_id=user.id, user2_id=matched_user.id,
            score=score, mode=mode,
            insight_json=json.dumps(insight, ensure_ascii=False),
        )
        db.session.add(m)
        saved.append((matched_user, score, insight))
        to_notify.append((matched_user, score, insight))

    if saved:
        user.last_matched_at = datetime.utcnow()
    db.session.commit()

    for matched_user, score, insight in to_notify:
        send_match_result_email(user.email, [(matched_user, score)], mail_cfg, insight)
        send_match_result_email(matched_user.email, [(user, score)], mail_cfg, insight)
        mrec = Match.query.filter(
            ((Match.user1_id == user.id) & (Match.user2_id == matched_user.id)) |
            ((Match.user1_id == matched_user.id) & (Match.user2_id == user.id))
        ).first()
        if mrec:
            mrec.notified = True
    if to_notify:
        db.session.commit()

    return jsonify({
        "ok": True,
        "mode": mode,
        "matches": [
            {
                "name": u.name,
                "gender": u.gender,
                "wechat_id": u.wechat_id,
                "score": s,
                "strengths": insight["strengths"][:3] if "strengths" in insight else [],
                "differences_count": insight.get("total_differences", 0),
            }
            for u, s, insight in saved
        ],
        "total_candidates": len(candidates),
        "dealbreaker_skipped": skipped_dealbreaker,
        "updated_existing": updated_existing,
        "newly_notified": len(to_notify),
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
            "school": other.school,
            "wechat_id": other.wechat_id,
            "score": m.score,
            "strengths": insight.get("strengths", [])[:3],
            "matched_at": m.created_at.isoformat() if m.created_at else None,
            "mode": m.mode,
        })

    return jsonify({"ok": True, "matches": results})


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
    }), (200 if db_ok else 503)


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


if __name__ == "__main__":
    init_db()
    print("  CampusMatch v2 启动!")
    print(f"  模式: {'批量匹配(每周二晚9点)' if MATCH_MODE == 'batch' else '实时匹配'}")
    print(f"  Debug: {FLASK_DEBUG}")
    print(f"  支持学校: {', '.join(SCHOOL_DOMAINS.keys())}")
    print(f"  邮件: {'真实发送' if MAIL_ENABLED else '开发模式'}")
    app.run(debug=FLASK_DEBUG, host="127.0.0.1", port=5000)
