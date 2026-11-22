"""Verified-campus buddy plans. Writes require CSRF. No private messages."""
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from admin_dashboard import _admin_signed_in, _csrf_token, _valid_csrf
from config import SCHOOL_DOMAINS
from models import (db, User, CommunityEntry as Entry, CommunityMember as Member,
                    CommunityReaction as Reaction, CommunityReport as Report,
                    CommunityBan as Ban, CommunityLimit as Limit, CommunityAudit as Audit)

bp = Blueprint("community", __name__)
GUEST_PREVIEW = 3
PLAN_CATEGORIES = {
    "study": "学习",
    "sport": "运动",
    "meal": "吃饭",
    "outing": "出行",
    "show": "看演出 / 看展",
    "game": "开黑",
}
LEGACY_CATEGORIES = {
    "confession": "表白与心动",
    "friends": "认识新朋友",
    "campus": "校园日常",
}
CATEGORIES = {**PLAN_CATEGORIES, **LEGACY_CATEGORIES}
FEES = {"aa": "AA", "host": "我请", "free": "免费"}
AUDIENCES = {"any": "不限", "male": "只限男生", "female": "只限女生"}
STATES = {"published": "已发布", "pending": "待审核", "hidden": "已隐藏", "deleted": "已删除"}
ACTIONS = {"approve": "审核通过", "hide": "隐藏内容", "pin": "置顶", "unpin": "取消置顶",
           "ban": "禁言 7 天", "unban": "解除禁言", "resolve": "举报已处理"}
COLUMN_ADDS = (
    ("place", "VARCHAR(80) DEFAULT ''"),
    ("capacity", "INTEGER"),
    ("fee", "VARCHAR(16) DEFAULT ''"),
    ("starts_at", "DATETIME"),
    ("flexible", "BOOLEAN DEFAULT 0"),
    ("cancelled", "BOOLEAN DEFAULT 0"),
    ("audience", "VARCHAR(16) DEFAULT 'any'"),
)


def ensure_community_columns():
    """Add plan columns when an older community_entries table is already present."""
    try:
        cols = {column["name"] for column in inspect(db.engine).get_columns("community_entries")}
    except Exception:
        return
    for name, ddl in COLUMN_ADDS:
        if name not in cols:
            db.session.execute(text(f"ALTER TABLE community_entries ADD COLUMN {name} {ddl}"))
    db.session.commit()


@bp.before_request
def authorize():
    if request.path.startswith("/admin/community"):
        if not _admin_signed_in():
            return redirect(url_for("admin_dashboard.login"))
        if request.method == "POST" and not _valid_csrf(request.form.get("csrf")):
            abort(400, "页面已过期，请刷新后重试。")
        return
    user = db.session.get(User, session.get("user_id")) if session.get("user_id") else None
    g.community_user = user if user and user.email_verified else None
    public_read = request.method == "GET" and (
        request.endpoint == "community.detail" or
        request.endpoint == "community.feed" and request.args.get("view", "all") == "all")
    if public_read:
        if g.community_user and "community_csrf" not in session:
            session["community_csrf"] = secrets.token_urlsafe(32)
        return
    if user is None:
        if request.method == "GET":
            return redirect("/#step1-card")
        abort(401, "请先登录。")
    if not user.email_verified:
        abort(403, "请先完成学校邮箱验证。")
    g.community_user = user
    if "community_csrf" not in session:
        session["community_csrf"] = secrets.token_urlsafe(32)
    if request.method == "POST":
        actual = request.form.get("csrf", "")
        if not secrets.compare_digest(actual.encode(), session["community_csrf"].encode()):
            abort(400, "页面已过期，请刷新后重试。")


@bp.after_request
def private_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def macau_now():
    return datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)


@bp.context_processor
def shared():
    now = macau_now().replace(second=0, microsecond=0)
    return dict(categories=CATEGORIES, plan_categories=PLAN_CATEGORIES, fees=FEES, audiences=AUDIENCES,
                states=STATES, actions=ACTIONS,
                community_user=getattr(g, "community_user", None),
                community_csrf=session.get("community_csrf", ""),
                plan_active=plan_active, plan_when=plan_when,
                macau_clock=now.strftime("%m-%d %H:%M"),
                macau_min=now.strftime("%Y-%m-%dT%H:%M"))


@bp.app_template_filter("community_time")
def local_time(value):
    return (value + timedelta(hours=8)).strftime("%m-%d %H:%M") if value else "—"


@bp.errorhandler(400)
@bp.errorhandler(401)
@bp.errorhandler(403)
@bp.errorhandler(404)
@bp.errorhandler(429)
def show_error(error):
    db.session.rollback()
    if request.accept_mimetypes.best == "application/json":
        return jsonify(message=error.description), error.code
    return render_template("community_error.html", message=error.description), error.code


def text_field(name, maximum, minimum=1):
    value = request.form.get(name, "").strip()
    if not minimum <= len(value) <= maximum:
        abort(400, f"内容长度须在 {minimum}–{maximum} 字之间。")
    return value


def guard_muted():
    ban = db.session.get(Ban, g.community_user.id)
    if ban and ban.until > datetime.utcnow():
        abort(403, f"你暂时无法发言或点赞，解除时间：{local_time(ban.until)}。原因：{ban.reason}")


def rate_limit(action, seconds):
    """Persistent atomic reservation, rolled back with a rejected write."""
    uid = g.community_user.id
    try:
        with db.session.begin_nested():
            db.session.add(Limit(user_id=uid, action=action, last_at=datetime(1970, 1, 1)))
            db.session.flush()
    except IntegrityError:
        pass
    now = datetime.utcnow()
    changed = Limit.query.filter_by(user_id=uid, action=action).filter(
        Limit.last_at <= now - timedelta(seconds=seconds)).update({"last_at": now})
    if not changed:
        abort(429, f"操作太频繁，请间隔 {seconds} 秒后再试。")


def plan_active(post, now=None):
    if not post or post.cancelled or post.status != "published" or post.category not in PLAN_CATEGORIES:
        return False
    now = now or datetime.utcnow()
    if post.flexible:
        return post.created_at >= now - timedelta(days=7)
    return bool(post.starts_at and post.starts_at >= now)


def plan_when(post):
    if post.flexible:
        return "7 天内再议"
    if post.starts_at:
        return local_time(post.starts_at)
    return local_time(post.created_at)


def active_clause(now=None):
    now = now or datetime.utcnow()
    return db.or_(
        db.and_(Entry.flexible.is_(False), Entry.starts_at.isnot(None), Entry.starts_at >= now),
        db.and_(Entry.flexible.is_(True), Entry.created_at >= now - timedelta(days=7)),
    )


def upcoming(query):
    return query.order_by(Entry.pinned.desc(), Entry.flexible.asc(),
                          Entry.starts_at.asc().nulls_last(), Entry.id.asc())


def going_count_query():
    return db.session.query(db.func.count(Member.user_id)).filter(
        Member.plan_id == Entry.id, Member.state == "going").correlate(Entry).scalar_subquery()


def schools_can_meet(left, right):
    if not left or not right:
        return False
    if left.school == right.school:
        return True
    return right.school in left.get_cross_schools() and left.school in right.get_cross_schools()


def in_squad(user, post):
    """Host and people holding a spot. Waitlist has not entered the group yet."""
    if not user or not post:
        return False
    if user.id == post.author_id:
        return True
    return Member.query.filter_by(plan_id=post.id, user_id=user.id, state="going").first() is not None


def visible_post(post_id):
    post = db.session.get(Entry, post_id)
    if not post or post.parent_id or post.status == "deleted":
        abort(404, "这场局不存在或已删除。")
    if post.status != "published" and (not g.community_user or post.author_id != g.community_user.id):
        abort(404, "这场局暂不可见。")
    if post.status == "published" and not g.community_user and post.id not in guest_preview_ids():
        abort(403, "这是预览之外的局。注册并验证学校邮箱后，即可浏览全部内容。")
    return post


def published_plans():
    query = Entry.query.filter(
        Entry.parent_id.is_(None), Entry.status == "published",
        Entry.category.in_(PLAN_CATEGORIES), Entry.cancelled.is_(False), active_clause())
    return upcoming(query)


def guest_preview_ids():
    return [row.id for row in published_plans().limit(GUEST_PREVIEW).all()]


def page_number():
    return max(1, min(request.args.get("page", 1, type=int), 100000))


def card_data(posts):
    ids = [p.id for p in posts]
    if not ids:
        return dict(likes={}, comment_counts={}, reactions={}, going={}, waiting={}, membership={})
    likes = dict(db.session.query(Reaction.entry_id, db.func.count()).filter(
        Reaction.entry_id.in_(ids), Reaction.kind == "like").group_by(Reaction.entry_id).all())
    comments = dict(db.session.query(Entry.parent_id, db.func.count()).filter(
        Entry.parent_id.in_(ids), Entry.status == "published").group_by(Entry.parent_id).all())
    going = dict(db.session.query(Member.plan_id, db.func.count()).filter(
        Member.plan_id.in_(ids), Member.state == "going").group_by(Member.plan_id).all())
    waiting = dict(db.session.query(Member.plan_id, db.func.count()).filter(
        Member.plan_id.in_(ids), Member.state == "waitlist").group_by(Member.plan_id).all())
    mine = {(r.entry_id, r.kind) for r in Reaction.query.filter(
        Reaction.entry_id.in_(ids), Reaction.user_id == g.community_user.id)} if g.community_user else set()
    membership = {}
    if g.community_user:
        membership = {row.plan_id: row.state for row in Member.query.filter(
            Member.plan_id.in_(ids), Member.user_id == g.community_user.id)}
    return dict(likes=likes, comment_counts=comments, reactions=mine,
                going=going, waiting=waiting, membership=membership)


def parse_start(raw):
    text = (raw or "").strip()
    local = None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            local = datetime.strptime(text, fmt)
            break
        except ValueError:
            continue
    if local is None:
        abort(400, "请填写开始时间。")
    local = local.replace(second=0, microsecond=0)
    now = macau_now().replace(second=0, microsecond=0)
    if local < now:
        abort(400, "开始时间要晚于现在。你填的是 "
              f"{local.strftime('%m-%d %H:%M')}，现在是 {now.strftime('%m-%d %H:%M')}（澳门时间）。"
              "已经过了的话，把时间改晚，或勾选「时间再议」。")
    return local - timedelta(hours=8)


def promote(plan):
    seated = 1 + Member.query.filter_by(plan_id=plan.id, state="going").count()
    if not plan.capacity or seated >= plan.capacity:
        return
    nxt = Member.query.filter_by(plan_id=plan.id, state="waitlist").order_by(
        Member.created_at, Member.user_id).first()
    if nxt:
        nxt.state = "going"


@bp.get("/community")
def feed():
    category = request.args.get("category", "")
    view = request.args.get("view", "all")
    school = request.args.get("school", "")
    when = request.args.get("when", "")
    spots = request.args.get("spots", "")
    who = request.args.get("who", "")
    fee = request.args.get("fee", "")
    if category and category not in PLAN_CATEGORIES or view not in ("all", "mine", "saved", "joined"):
        abort(400, "无效筛选条件。")
    if when not in ("", "week") or spots not in ("", "open"):
        abort(400, "无效筛选条件。")
    if who not in ("", "any", "male", "female", "mine") or (fee and fee not in FEES):
        abort(400, "无效筛选条件。")
    query = Entry.query.filter(Entry.parent_id.is_(None), Entry.status != "deleted")
    if view == "mine":
        query = query.filter(Entry.author_id == g.community_user.id)
    elif view == "joined":
        query = query.filter(Entry.id.in_(db.select(Member.plan_id).where(
            Member.user_id == g.community_user.id)))
        query = query.filter(Entry.status == "published")
    else:
        query = query.filter(Entry.status == "published")
    if view == "saved":
        query = query.filter(Entry.id.in_(db.select(Reaction.entry_id).where(
            Reaction.user_id == g.community_user.id, Reaction.kind == "save")))
    if view == "all":
        query = query.filter(Entry.category.in_(PLAN_CATEGORIES), Entry.cancelled.is_(False), active_clause())
        if when == "week":
            soon = datetime.utcnow() + timedelta(days=7)
            query = query.filter(db.or_(Entry.flexible.is_(True), Entry.starts_at <= soon))
        if spots == "open":
            query = query.filter(Entry.capacity > 1 + going_count_query())
        if who == "mine":
            gender = g.community_user.gender if g.community_user else ""
            allowed = ("any", gender) if gender in ("male", "female") else ("any",)
            query = query.filter(Entry.audience.in_(allowed))
        elif who:
            query = query.filter(Entry.audience == who)
        if fee:
            query = query.filter(Entry.fee == fee)
    if category and view == "all":
        query = query.filter(Entry.category == category)
    guest = not g.community_user
    order = upcoming(query) if view == "all" else query.order_by(Entry.created_at.desc(), Entry.id.desc())
    if guest:
        school = ""
        page, more = 1, False
        total = query.count()
        preview_ids = guest_preview_ids()
        query = query.filter(Entry.id.in_(preview_ids)) if preview_ids else query.filter(db.false())
        rows = upcoming(query).limit(GUEST_PREVIEW).all()
        locked = max(0, total - len(rows))
        schools = []
    else:
        if school and view == "all":
            query = query.filter(Entry.school == school)
            order = upcoming(query) if view == "all" else query.order_by(Entry.created_at.desc(), Entry.id.desc())
        page = page_number()
        rows = order.offset((page - 1) * 20).limit(21).all()
        more, locked = len(rows) > 20, 0
        rows = rows[:20]
        present = {s for s, in db.session.query(Entry.school).filter(
            Entry.parent_id.is_(None), Entry.status == "published",
            Entry.category.in_(PLAN_CATEGORIES), Entry.school != "")}
        schools = list(SCHOOL_DOMAINS) + sorted(s for s in present if s not in SCHOOL_DOMAINS)
    return render_template("community_feed.html", posts=rows, more=more, page=page, locked=locked,
                           category=category, view=view, school=school, schools=schools,
                           when=when, spots=spots, who=who, fee=fee, **card_data(rows))


@bp.route("/community/new", methods=["GET", "POST"])
def create():
    if request.method == "GET":
        return render_template("community_new.html")
    guard_muted()
    category = request.form.get("category")
    if category not in PLAN_CATEGORIES:
        abort(400, "请选择活动类型。")
    title = text_field("title", 80, 2)
    body = text_field("body", 2000, 0)
    place = text_field("place", 40, 2)
    fee = request.form.get("fee", "")
    if fee not in FEES:
        abort(400, "请选择费用方式。")
    audience = request.form.get("audience", "")
    if audience not in AUDIENCES:
        abort(400, "请选择性别范围。")
    picked = request.form.get("my_gender", "").strip()
    if picked and picked not in ("male", "female"):
        abort(400, "请选择你的性别。")
    if audience in ("male", "female"):
        gender = g.community_user.gender if g.community_user.gender in ("male", "female") else ""
        if not gender and picked in ("male", "female"):
            gender = picked
        if gender != audience:
            who = "男生" if audience == "male" else "女生"
            abort(400, f"只限{who}的局，发起人自己也要是{who}。")
        if g.community_user.gender not in ("male", "female"):
            g.community_user.gender = picked
    raw_cap = request.form.get("capacity", "").strip()
    if not raw_cap.isdigit() or not 2 <= int(raw_cap) <= 12:
        abort(400, "人数上限须在 2–12 人之间（含发起人）。")
    flexible = request.form.get("flexible") == "1"
    starts_at = None if flexible else parse_start(request.form.get("starts_at", ""))
    rate_limit("post", 60)
    post = Entry(author_id=g.community_user.id, school=g.community_user.school, category=category,
                 title=title, body=body, place=place, capacity=int(raw_cap),
                 fee=fee, audience=audience, starts_at=starts_at, flexible=flexible,
                 anonymous=False, status="published")
    db.session.add(post)
    db.session.commit()
    flash("局已发布。同校同学可以直接占名额。")
    return redirect(url_for("community.detail", post_id=post.id))


@bp.get("/community/posts/<int:post_id>")
def detail(post_id):
    post = visible_post(post_id)
    squad = post.category not in PLAN_CATEGORIES or in_squad(g.community_user, post)
    if not squad:
        comments, page, more = [], 1, False
    else:
        query = Entry.query.filter_by(parent_id=post.id).filter(Entry.status != "deleted")
        if g.community_user:
            query = query.filter(db.or_(Entry.status == "published", Entry.author_id == g.community_user.id))
        else:
            query = query.filter(Entry.status == "published")
        page = page_number()
        comments = query.order_by(Entry.created_at, Entry.id).offset((page - 1) * 30).limit(31).all()
        more = len(comments) > 30
        comments = comments[:30]
    members = Member.query.filter_by(plan_id=post.id).order_by(Member.state, Member.created_at, Member.user_id).all()
    return render_template("community_detail.html", post=post, comments=comments, page=page,
                           more=more, members=members, squad=squad, **card_data([post]))


@bp.post("/community/posts/<int:post_id>/comments")
def comment(post_id):
    post = visible_post(post_id)
    if post.status != "published":
        abort(403, "这场局尚未公开，暂不能留言。")
    if post.category in PLAN_CATEGORIES and not in_squad(g.community_user, post):
        abort(403, "占到名额后才能留言。")
    guard_muted()
    body = text_field("body", 500)
    rate_limit("comment", 15)
    pending = post.category == "confession"
    db.session.add(Entry(parent_id=post.id, author_id=g.community_user.id, school=g.community_user.school,
                         category=post.category, body=body, anonymous=False,
                         status="pending" if pending else "published"))
    db.session.commit()
    flash("留言已提交审核，通过后会显示。" if pending else "留言已发布。只有占到名额的人看得到。")
    return redirect(url_for("community.detail", post_id=post.id))


@bp.post("/community/posts/<int:post_id>/join")
def join(post_id):
    post = visible_post(post_id)
    if not plan_active(post):
        abort(403, "这场局已结束或已取消，不能再加入。")
    if post.author_id == g.community_user.id:
        abort(400, "你是发起人，名额里已经算上你。")
    if not schools_can_meet(g.community_user, post.author):
        abort(403, "跨校组局需要双方都在资料里勾选了对方的学校。")
    limit = post.audience if post.audience in ("male", "female") else ""
    picked = request.form.get("my_gender", "").strip()
    gender = g.community_user.gender if g.community_user.gender in ("male", "female") else ""
    if not gender and picked in ("male", "female"):
        gender = picked
    if limit and gender != limit:
        who = "男生" if limit == "male" else "女生"
        abort(403, f"这场局只限{who}。" + ("" if g.community_user.gender in ("male", "female") else "请选择你的性别。"))
    if picked in ("male", "female") and g.community_user.gender not in ("male", "female"):
        g.community_user.gender = picked
    guard_muted()
    if Member.query.filter_by(plan_id=post.id, user_id=g.community_user.id).first():
        abort(400, "你已经在这场局里。")
    rate_limit("join", 10)
    going = Member.query.filter_by(plan_id=post.id, state="going").count()
    state = "going" if post.capacity and 1 + going < post.capacity else "waitlist"
    try:
        with db.session.begin_nested():
            db.session.add(Member(plan_id=post.id, user_id=g.community_user.id, state=state))
            db.session.flush()
    except IntegrityError:
        state = Member.query.filter_by(plan_id=post.id, user_id=g.community_user.id).one().state
    db.session.commit()
    flash("已占到名额。" if state == "going" else "名额已满，你在候补里。有人退出会按顺序补上。")
    return redirect(url_for("community.detail", post_id=post.id))


@bp.post("/community/posts/<int:post_id>/leave")
def leave(post_id):
    post = visible_post(post_id)
    row = Member.query.filter_by(plan_id=post.id, user_id=g.community_user.id).first()
    if not row:
        abort(404, "你不在这场局里。")
    was_going = row.state == "going"
    db.session.delete(row)
    db.session.flush()
    if was_going and plan_active(post):
        promote(post)
    db.session.commit()
    flash("已退出。空出的名额会补给最早的候补。" if plan_active(post) else "已退出。")
    return redirect(url_for("community.detail", post_id=post.id))


@bp.post("/community/posts/<int:post_id>/cancel")
def cancel(post_id):
    post = visible_post(post_id)
    if post.author_id != g.community_user.id:
        abort(403, "只有发起人可以取消这场局。")
    post.cancelled = True
    post.pinned = False
    db.session.commit()
    flash("这场局已取消。已加入的同学仍能打开页面看到取消说明。")
    return redirect(url_for("community.detail", post_id=post.id))


@bp.post("/community/posts/<int:post_id>/members/<int:user_id>/remove")
def remove_member(post_id, user_id):
    post = visible_post(post_id)
    if post.author_id != g.community_user.id:
        abort(403, "只有发起人可以移出同学。")
    row = Member.query.filter_by(plan_id=post.id, user_id=user_id).first()
    if not row:
        abort(404, "这位同学不在局里。")
    was_going = row.state == "going"
    db.session.delete(row)
    db.session.flush()
    if was_going and plan_active(post):
        promote(post)
    db.session.commit()
    flash("已移出。空出的名额会补给最早的候补。" if plan_active(post) else "已移出。")
    return redirect(url_for("community.detail", post_id=post.id))


@bp.post("/community/posts/<int:post_id>/reaction")
def react(post_id):
    post = visible_post(post_id)
    if post.status != "published":
        abort(403, "这场局尚未公开。")
    kind, enabled = request.form.get("kind"), request.form.get("enabled")
    if kind not in ("like", "save") or enabled not in ("0", "1"):
        abort(400, "无效操作。")
    if kind == "like":
        guard_muted()
    if enabled == "1":
        try:
            with db.session.begin_nested():
                db.session.add(Reaction(user_id=g.community_user.id, entry_id=post.id, kind=kind))
                db.session.flush()
        except IntegrityError:
            pass
    else:
        Reaction.query.filter_by(user_id=g.community_user.id, entry_id=post.id, kind=kind).delete()
    db.session.commit()
    if request.accept_mimetypes.best == "application/json":
        return jsonify(enabled=Reaction.query.filter_by(
            user_id=g.community_user.id, entry_id=post.id, kind=kind).first() is not None,
                       likes=Reaction.query.filter_by(entry_id=post.id, kind="like").count())
    return redirect(url_for("community.detail", post_id=post.id))


@bp.post("/community/entries/<int:entry_id>/delete")
def delete(entry_id):
    entry = db.session.get(Entry, entry_id)
    if not entry or entry.author_id != g.community_user.id:
        abort(404, "内容不存在。")
    parent_id = entry.parent_id
    ids = [entry.id] + [i for i, in db.session.query(Entry.id).filter_by(parent_id=entry.id)]
    retire_entries(ids)
    db.session.add(Audit(entry_id=entry.id, user_id=g.community_user.id, action="user_delete",
                         reason="用户自行删除"))
    db.session.commit()
    flash("内容已删除。")
    parent = db.session.get(Entry, parent_id) if parent_id else None
    return redirect(url_for("community.detail", post_id=parent_id) if parent and parent.status == "published"
                    else url_for("community.feed", view="mine"))


@bp.post("/community/entries/<int:entry_id>/report")
def report(entry_id):
    entry = db.session.get(Entry, entry_id)
    if not entry or entry.status != "published":
        abort(404, "内容暂不可见。")
    post = visible_post(entry.parent_id or entry.id)
    if post.status != "published":
        abort(404, "内容暂不可见。")
    reason = text_field("reason", 280, 2)
    if not Report.query.filter_by(user_id=g.community_user.id, entry_id=entry.id).first():
        rate_limit("report", 15)
        try:
            with db.session.begin_nested():
                db.session.add(Report(user_id=g.community_user.id, entry_id=entry.id, reason=reason))
                db.session.flush()
        except IntegrityError:
            pass
    db.session.commit()
    if request.accept_mimetypes.best == "application/json":
        return jsonify(message="举报已收到，管理员将查看。")
    flash("举报已收到，管理员将查看。")
    return redirect(url_for("community.detail", post_id=post.id))


@bp.get("/admin/community")
def admin():
    state = request.args.get("state", "pending")
    if state not in ("pending", "published", "hidden", "reports", "banned"):
        abort(400, "无效筛选条件。")
    query = Entry.query.filter(Entry.status != "deleted")
    if state == "reports":
        query = query.filter(Entry.id.in_(db.select(Report.entry_id).where(Report.resolved.is_(False))))
    elif state == "banned":
        query = query.filter(Entry.author_id.in_(db.select(Ban.user_id).where(Ban.until > datetime.utcnow())))
    else:
        query = query.filter(Entry.status == state)
    page = page_number()
    rows = query.order_by(Entry.created_at.desc(), Entry.id.desc()).offset((page - 1) * 20).limit(21).all()
    ids = [r.id for r in rows[:20]]
    reports = Report.query.filter(Report.entry_id.in_(ids), Report.resolved.is_(False)).order_by(Report.created_at).all()
    counts = {key: Entry.query.filter_by(status=key).count() for key in ("pending", "published", "hidden")}
    counts["reports"] = db.session.query(Report.entry_id).filter_by(resolved=False).distinct().count()
    counts["banned"] = Ban.query.filter(Ban.until > datetime.utcnow()).count()
    return render_template("admin_community.html", entries=rows[:20], reports=reports, counts=counts,
                           bans={b.user_id: b for b in Ban.query.filter(Ban.until > datetime.utcnow())},
                           audits=Audit.query.order_by(Audit.created_at.desc(), Audit.id.desc()).limit(30).all(),
                           state=state, page=page, more=len(rows) > 20, admin_csrf=_csrf_token())


@bp.post("/admin/community/entries/<int:entry_id>")
def moderate(entry_id):
    entry = db.session.get(Entry, entry_id)
    if not entry or entry.status == "deleted":
        abort(404, "内容已删除或不存在。")
    action = request.form.get("action")
    if action not in ACTIONS:
        abort(400, "无效管理操作。")
    reason = text_field("reason", 280, 2)
    if action == "approve":
        entry.status = "published"
    elif action == "hide":
        entry.status, entry.pinned = "hidden", False
    elif action in ("pin", "unpin"):
        if entry.parent_id or entry.status != "published":
            abort(400, "仅可置顶公开的局。")
        entry.pinned = action == "pin"
    elif action == "ban":
        ban = db.session.get(Ban, entry.author_id)
        if not ban:
            ban = Ban(user_id=entry.author_id)
            db.session.add(ban)
        ban.until, ban.reason = datetime.utcnow() + timedelta(days=7), reason
        Entry.query.filter(Entry.author_id == entry.author_id, Entry.status == "published").update(
            {"status": "hidden", "pinned": False}, synchronize_session=False)
    elif action == "unban":
        Ban.query.filter_by(user_id=entry.author_id).delete()
    if action in ("hide", "resolve"):
        Report.query.filter_by(entry_id=entry.id, resolved=False).update({"resolved": True})
    db.session.add(Audit(entry_id=entry.id, action=action, reason=reason))
    db.session.commit()
    flash("管理操作已保存。")
    return redirect(url_for("community.admin", state="reports" if action == "resolve" else "pending"))


@bp.post("/admin/community/users/<int:user_id>/unban")
def unban_user(user_id):
    ban = db.session.get(Ban, user_id)
    if not ban:
        abort(404, "该账号没有禁言记录。")
    reason = text_field("reason", 280, 2)
    db.session.delete(ban)
    db.session.add(Audit(user_id=user_id, action="unban", reason=reason))
    db.session.commit()
    flash("禁言已解除。")
    return redirect(url_for("community.admin", state="banned"))


def retire_entries(ids):
    """Hide deleted content but keep reports and audit rows."""
    if not ids:
        return
    Member.query.filter(Member.plan_id.in_(ids)).delete(synchronize_session=False)
    Reaction.query.filter(Reaction.entry_id.in_(ids)).delete(synchronize_session=False)
    Report.query.filter(Report.entry_id.in_(ids), Report.resolved.is_(False)).update(
        {"resolved": True}, synchronize_session=False)
    Entry.query.filter(Entry.id.in_(ids)).update(
        {"status": "deleted", "pinned": False, "title": "", "body": ""}, synchronize_session=False)


def erase_entries(ids):
    """Account purge: remove rows, but detach audit so the log can remain."""
    if not ids:
        return
    Audit.query.filter(Audit.entry_id.in_(ids)).update({"entry_id": None}, synchronize_session=False)
    Member.query.filter(Member.plan_id.in_(ids)).delete(synchronize_session=False)
    for model in (Reaction, Report):
        model.query.filter(model.entry_id.in_(ids)).delete(synchronize_session=False)
    Entry.query.filter(Entry.id.in_(ids), Entry.parent_id.isnot(None)).delete(synchronize_session=False)
    Entry.query.filter(Entry.id.in_(ids)).delete(synchronize_session=False)


def purge_community(user_id):
    own = [i for i, in db.session.query(Entry.id).filter_by(author_id=user_id)]
    children = [i for i, in db.session.query(Entry.id).filter(Entry.parent_id.in_(own))] if own else []
    Member.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    erase_entries(own + children)
    Audit.query.filter_by(user_id=user_id).update({"user_id": None}, synchronize_session=False)
    for model in (Reaction, Report, Ban, Limit):
        model.query.filter_by(user_id=user_id).delete(synchronize_session=False)
