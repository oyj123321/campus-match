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
    REVEAL_REQUIRE_OPT_IN, INSTANT_MATCH_ENABLED, CROSS_SCHOOL_MATCHING_ENABLED,
    ICEBREAKER_FOLLOWUP_DAYS,
    MAIL_ENABLED, MAIL_PROVIDER, MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM,
    RESEND_API_KEY,
)
from models import db, User, UserTag, Match, Blocklist
from questionnaire import QUESTIONS, build_feature_vector, get_compatibility_insight, get_open_letter
from mbti_report import build_mbti_report
from matcher import real_time_match, batch_match_school
from email_service import send_verification_email, send_match_result_email
from batch_job import (
    persist_user_matches, count_new_matches_this_week,
    next_batch_datetime, run_batch_all, schedule_loop, current_week_key,
)
from match_pool import eligible_candidates

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
    """无论是否配对成功都应通知；无结果时发「暂未配对」邮件。"""
    ok, info = send_match_result_email(
        user.email, [], get_mail_config(), reason=reason,
    )
    return bool(ok), info


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
    """计算冷却 / 本周额度 / 预约揭晓状态。"""
    used = count_new_matches_this_week(user.id)
    remaining = max(0, MATCH_WEEKLY_NEW_LIMIT - used)
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
        "weekly_limit": MATCH_WEEKLY_NEW_LIMIT,
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
        "email": other.email if active else None,
        "wechat_id": other.wechat_id if active else None,
        "bio": other.bio if active else None,
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
        "一对一：在取向互相接受、本周仍有额度的人里算问卷相似度，"
        "只给你得分最高的 1 人；页面不展示匹配度分数，只给契合点与破冰话题"
        + (
            "；默认同校，跨校需双方互相勾选对方学校（双向白名单）。"
            if CROSS_SCHOOL_MATCHING_ENABLED else "（同校）。"
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
            "2. 余弦相似度：两串数字方向越接近，匹配分越高（仅用于内部排序，不对用户展示）。",
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

    # 内测号：免邮件，注册后直接登录（验证码随便填也能进）
    if _is_beta_account(email):
        user.verification_token = None
        user.email_verified = True
        db.session.commit()
        session["user_id"] = user.id
        return jsonify({
            "ok": True,
            "mail_sent": False,
            "beta_skip_verify": True,
            "message": f"内测账号已直接登录（{email}）。验证码可随便填，或不填直接点验证亦可。",
            "dev_token": "任意",
        })

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
        return jsonify({"ok": False, "error": "邮箱不能为空"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"ok": False, "error": "用户不存在"}), 404

    beta = _is_beta_account(email)
    # 内测号：任意验证码（可空）直接登录
    if beta:
        user.email_verified = True
        user.verification_token = None
        db.session.commit()
        session["user_id"] = user.id
        return jsonify({"ok": True, "message": "内测账号已登录"})

    if not token:
        return jsonify({"ok": False, "error": "邮箱和验证码不能为空"}), 400

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
    if user.email_verified and not _is_beta_account(email):
        return jsonify({"ok": True, "message": "已验证"})

    ok_rate, rate_err = check_register_rate(email)
    if not ok_rate:
        return jsonify({"ok": False, "error": rate_err}), 429

    if _is_beta_account(email):
        user.verification_token = None
        user.email_verified = True
        db.session.commit()
        session["user_id"] = user.id
        return jsonify({
            "ok": True,
            "beta_skip_verify": True,
            "dev_token": "任意",
            "message": "内测账号已登录，验证码可随便填",
        })

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
    if not isinstance(answers_raw, dict):
        return jsonify({"ok": False, "error": "问卷答案格式错误"}), 400
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
        return jsonify({
            "ok": False,
            "error": f"请完成全部 {required_n} 道必答题（未完成：{', '.join('Q' + str(x) for x in missing)}）",
        }), 400

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

    mbti = build_mbti_report(answers)
    user.mbti_report = mbti

    db.session.commit()

    return jsonify({
        "ok": True,
        "message": "问卷已保存",
        "vector_dim": len(vec),
        "completed": user.questionnaire_completed(),
        "mbti": mbti,
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
    """问卷推演 MBTI（娱乐向）；无缓存则按当前答案现算并落库。"""
    user = get_current_user()
    if not user.answers:
        return jsonify({"ok": False, "error": "请先完成问卷"}), 400
    report = user.mbti_report
    if not report or not report.get("type"):
        report = build_mbti_report(user.answers)
        user.mbti_report = report
        db.session.commit()
    return jsonify({"ok": True, "mbti": report})


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
            return jsonify({"ok": False, "error": "请先填写附加联系方式"}), 400
        return jsonify({"ok": False, "error": "资料不完整，请返回问卷页补全"}), 400

    if not user.is_open_to_match():
        return jsonify({
            "ok": False,
            "error": "你已关闭「参与匹配」。可在匹配中心重新打开后再试。",
            "quota": match_quota_status(user),
        }), 403

    if not INSTANT_MATCH_ENABLED:
        return jsonify({
            "ok": False,
            "error": "当前为「每周揭晓」模式，请先预约本周匹配，等待统一揭晓。",
            "quota": match_quota_status(user),
        }), 403

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
        msg = "当前暂无符合你择偶取向的可匹配用户"
        if CROSS_SCHOOL_MATCHING_ENABLED and not user.get_cross_schools():
            msg += "（可在问卷/匹配页勾选愿意跨配的学校，且对方也须勾选你的学校）"
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
            "note": "结果以本页为准；邮件仅作通知，发送失败不影响查看。",
        })

    if mode == "batch":
        all_users = candidates + [user]
        results = batch_match_school(all_users, filter_same_gender=True)
        my_matches = [
            (a if b.id == user.id else b, s)
            for a, b, s in results
            if (a.id == user.id or b.id == user.id) and s >= MATCH_MIN_SCORE
        ]
    else:
        # one_to_one：只取 1 人；top_n：可多人（调试）
        top_n = 1 if mode != "top_n" else max(1, MATCH_TOP_N)
        my_matches = real_time_match(
            user, candidates, top_n=top_n, min_score=MATCH_MIN_SCORE
        )

    if not my_matches:
        msg = (
            "池子里有人，但暂时没有足够合适的人选"
            "（或合适人选本周已配过）。宁缺毋滥，请下周再试或完善问卷。"
        )
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
            "note": "结果以本页为准；邮件仅作通知，发送失败不影响查看。",
        })

    summary = persist_user_matches(
        user, my_matches, mode, get_mail_config(),
        weekly_new_limit=MATCH_WEEKLY_NEW_LIMIT,
    )
    saved = summary["saved"]

    if not saved:
        parts = []
        if summary.get("partner_quota_skipped"):
            parts.append("对方本周已有配对")
        if summary.get("low_score_skipped"):
            parts.append("相似度未达内部门槛")
        if summary.get("dealbreaker_skipped"):
            parts.append("硬性底线冲突")
        if summary.get("quota_skipped"):
            parts.append("你的本周额度已用完")
        reason = "；".join(parts) if parts else "暂无合适人选"
        msg = f"未能完成配对：{reason}。"
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
            "note": "结果以本页为准；邮件仅作通知。",
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
        "note": "结果以本页为准；邮件仅作通知。种子/无效邮箱常会发送失败，你的真实学校邮箱应能收到。",
    })


@app.route("/api/match/opt-in", methods=["POST", "DELETE"])
@login_required
def api_match_opt_in():
    """预约 / 取消本周批量匹配。"""
    user = get_current_user()
    if not user.ready_to_match():
        return jsonify({"ok": False, "error": "请先完成问卷、性别、择偶取向与附加联系方式"}), 400
    if not user.is_open_to_match():
        return jsonify({
            "ok": False,
            "error": "请先开启「参与匹配」，再预约本周揭晓",
            "quota": match_quota_status(user),
        }), 403

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
        "message": f"已预约本周匹配，将在 {match_quota_status(user)['next_batch_label']} 揭晓",
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
        # 旧记录补全：icebreakers 为空时重新生成
        ice = insight.get("icebreakers") or []
        needs_regen = not ice
        if m.active and needs_regen:
            insight = get_compatibility_insight(
                user.feature_vector, other.feature_vector,
                user.answers, other.answers,
                score=m.score,
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
        "note": "一对一：你只能看到当前有效配对；学校邮箱已互见，可先邮件开聊。",
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
    contact = (data.get("wechat_id") or "").strip()
    if "wechat_id" in data:
        if not contact:
            return jsonify({"ok": False, "error": "请填写附加联系方式（微信或其他均可）"}), 400
        user.wechat_id = contact[:120]
    user.bio = (data.get("bio") or "").strip() or user.bio
    if "cross_schools" in data:
        raw = data.get("cross_schools")
        if raw is None:
            raw = []
        if not isinstance(raw, list):
            return jsonify({"ok": False, "error": "cross_schools 须为学校名列表"}), 400
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
    db.session.commit()
    return jsonify({"ok": True, "user": user.to_dict()})


@app.route("/api/users/search", methods=["GET"])
@login_required
def api_users_search():
    """按昵称或邮箱精确搜索可拉黑对象（不返回联系方式）。"""
    user = get_current_user()
    q = (request.args.get("q") or "").strip()
    if len(q) < 1:
        return jsonify({"ok": False, "error": "请输入昵称或邮箱"}), 400

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
        return jsonify({"ok": False, "error": "请指定要拉黑的用户（从搜索结果点选）"}), 400

    if target_id == user.id:
        return jsonify({"ok": False, "error": "不能拉黑自己"}), 400

    target = User.query.get(target_id)
    if not target or not target.email_verified:
        return jsonify({"ok": False, "error": "用户不存在"}), 404

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
        "message": f"已将 {target.name or target.email} 加入黑名单，之后不会再匹配",
        "deactivated_matches": len(active),
    })


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
    """后台线程：破冰随访（按小时）；可选每周批量匹配。"""
    # Flask debug 重载会起两个进程，只在主进程开调度
    if FLASK_DEBUG and not os_environ_is_reloader_main():
        return

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
    start_batch_scheduler()
    app.run(debug=FLASK_DEBUG, host="127.0.0.1", port=5000)
