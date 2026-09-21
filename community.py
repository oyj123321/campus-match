"""Verified-campus community and private moderation. All writes require CSRF."""
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from admin_dashboard import _admin_signed_in, _csrf_token, _valid_csrf
from models import (db, User, CommunityEntry as Entry, CommunityReaction as Reaction,
                    CommunityReport as Report, CommunityBan as Ban,
                    CommunityLimit as Limit, CommunityAudit as Audit)

bp = Blueprint("community", __name__)
CATEGORIES = {"confession": "表白与心动", "friends": "认识新朋友", "campus": "校园日常"}
STATES = {"published": "已发布", "pending": "待审核", "hidden": "已隐藏", "deleted": "已删除"}
ACTIONS = {"approve": "审核通过", "hide": "隐藏内容", "pin": "置顶", "unpin": "取消置顶",
           "ban": "禁言 7 天", "unban": "解除禁言", "resolve": "举报已处理"}


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


@bp.context_processor
def shared():
    return dict(categories=CATEGORIES, states=STATES, actions=ACTIONS,
                community_user=getattr(g, "community_user", None),
                community_csrf=session.get("community_csrf", ""))


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


def visible_post(post_id):
    post = db.session.get(Entry, post_id)
    if not post or post.parent_id or post.status == "deleted":
        abort(404, "帖子不存在或已删除。")
    if post.status != "published" and (not g.community_user or post.author_id != g.community_user.id):
        abort(404, "帖子暂不可见。")
    return post


def page_number():
    return max(1, min(request.args.get("page", 1, type=int), 100000))


def card_data(posts):
    ids = [p.id for p in posts]
    likes = dict(db.session.query(Reaction.entry_id, db.func.count()).filter(
        Reaction.entry_id.in_(ids), Reaction.kind == "like").group_by(Reaction.entry_id).all())
    comments = dict(db.session.query(Entry.parent_id, db.func.count()).filter(
        Entry.parent_id.in_(ids), Entry.status == "published").group_by(Entry.parent_id).all())
    mine = {(r.entry_id, r.kind) for r in Reaction.query.filter(
        Reaction.entry_id.in_(ids), Reaction.user_id == g.community_user.id)} if g.community_user else set()
    return dict(likes=likes, comment_counts=comments, reactions=mine)


@bp.get("/community")
def feed():
    category = request.args.get("category", "")
    view = request.args.get("view", "all")
    school = request.args.get("school", "")
    if category and category not in CATEGORIES or view not in ("all", "mine", "saved"):
        abort(400, "无效筛选条件。")
    query = Entry.query.filter(Entry.parent_id.is_(None), Entry.status != "deleted")
    if view == "mine":
        query = query.filter(Entry.author_id == g.community_user.id)
    else:
        query = query.filter(Entry.status == "published")
    if view == "saved":
        query = query.filter(Entry.id.in_(db.select(Reaction.entry_id).where(
            Reaction.user_id == g.community_user.id, Reaction.kind == "save")))
    if category:
        query = query.filter(Entry.category == category)
    if school:
        query = query.filter(Entry.school == school)
    page = page_number()
    rows = query.order_by(Entry.pinned.desc(), Entry.created_at.desc(), Entry.id.desc()).offset((page-1)*20).limit(21).all()
    schools = [s for s, in db.session.query(User.school).distinct().order_by(User.school)]
    return render_template("community_feed.html", posts=rows[:20], more=len(rows)>20, page=page,
                           category=category, view=view, school=school, schools=schools,
                           **card_data(rows[:20]))


@bp.route("/community/new", methods=["GET", "POST"])
def create():
    if request.method == "GET":
        return render_template("community_new.html")
    guard_muted()
    category = request.form.get("category")
    if category not in CATEGORIES:
        abort(400, "请选择有效分类。")
    title, body = text_field("title", 80, 2), text_field("body", 2000, 5)
    rate_limit("post", 60)
    post = Entry(author_id=g.community_user.id, school=g.community_user.school, category=category,
                 title=title, body=body, anonymous=request.form.get("anonymous") == "1",
                 status="pending" if category == "confession" else "published")
    db.session.add(post)
    db.session.commit()
    flash("已提交审核，通过后会出现在广场。" if post.status == "pending" else "发布成功。")
    return redirect(url_for("community.detail", post_id=post.id))


@bp.get("/community/posts/<int:post_id>")
def detail(post_id):
    post = visible_post(post_id)
    query = Entry.query.filter_by(parent_id=post.id, status="published")
    if post.status != "published":
        query = query.filter_by(author_id=g.community_user.id)
    page = page_number()
    comments = query.order_by(Entry.created_at, Entry.id).offset((page-1)*30).limit(31).all()
    return render_template("community_detail.html", post=post, comments=comments[:30], page=page,
                           more=len(comments)>30, **card_data([post]))


@bp.post("/community/posts/<int:post_id>/comments")
def comment(post_id):
    post = visible_post(post_id)
    if post.status != "published":
        abort(403, "帖子尚未公开，暂不能评论。")
    guard_muted()
    body = text_field("body", 500)
    rate_limit("comment", 15)
    db.session.add(Entry(parent_id=post.id, author_id=g.community_user.id, school=g.community_user.school,
                         category=post.category, body=body, anonymous=request.form.get("anonymous") == "1"))
    db.session.commit()
    flash("评论已发布。")
    return redirect(url_for("community.detail", post_id=post.id))


@bp.post("/community/posts/<int:post_id>/reaction")
def react(post_id):
    post = visible_post(post_id)
    if post.status != "published":
        abort(403, "帖子尚未公开。")
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
        return jsonify(enabled=Reaction.query.filter_by(user_id=g.community_user.id, entry_id=post.id, kind=kind).first() is not None,
                       likes=Reaction.query.filter_by(entry_id=post.id, kind="like").count())
    return redirect(url_for("community.detail", post_id=post.id))


@bp.post("/community/entries/<int:entry_id>/delete")
def delete(entry_id):
    entry = db.session.get(Entry, entry_id)
    if not entry or entry.author_id != g.community_user.id:
        abort(404, "内容不存在。")
    parent_id = entry.parent_id
    erase_entries([entry.id] + [i for i, in db.session.query(Entry.id).filter_by(parent_id=entry.id)])
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
    rows = query.order_by(Entry.created_at.desc(), Entry.id.desc()).offset((page-1)*20).limit(21).all()
    ids = [r.id for r in rows[:20]]
    reports = Report.query.filter(Report.entry_id.in_(ids), Report.resolved.is_(False)).order_by(Report.created_at).all()
    counts = {key: Entry.query.filter_by(status=key).count() for key in ("pending", "published", "hidden")}
    counts["reports"] = db.session.query(Report.entry_id).filter_by(resolved=False).distinct().count()
    counts["banned"] = Ban.query.filter(Ban.until > datetime.utcnow()).count()
    return render_template("admin_community.html", entries=rows[:20], reports=reports, counts=counts,
                           bans={b.user_id:b for b in Ban.query.filter(Ban.until > datetime.utcnow())},
                           audits=Audit.query.order_by(Audit.created_at.desc(), Audit.id.desc()).limit(30).all(),
                           state=state, page=page, more=len(rows)>20, admin_csrf=_csrf_token())


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
            abort(400, "仅可置顶公开帖子。")
        entry.pinned = action == "pin"
    elif action == "ban":
        ban = db.session.get(Ban, entry.author_id)
        if not ban:
            ban = Ban(user_id=entry.author_id)
            db.session.add(ban)
        ban.until, ban.reason = datetime.utcnow() + timedelta(days=7), reason
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


def erase_entries(ids):
    """Child-first hard deletion, including reports/reactions and related audit text."""
    if not ids:
        return
    for model in (Reaction, Report, Audit):
        model.query.filter(model.entry_id.in_(ids)).delete(synchronize_session=False)
    Entry.query.filter(Entry.id.in_(ids), Entry.parent_id.isnot(None)).delete(synchronize_session=False)
    Entry.query.filter(Entry.id.in_(ids)).delete(synchronize_session=False)


def purge_community(user_id):
    own = [i for i, in db.session.query(Entry.id).filter_by(author_id=user_id)]
    children = [i for i, in db.session.query(Entry.id).filter(Entry.parent_id.in_(own))]
    erase_entries(own + children)
    for model in (Reaction, Report, Ban, Limit, Audit):
        model.query.filter_by(user_id=user_id).delete(synchronize_session=False)
