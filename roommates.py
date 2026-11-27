"""Roommate cards. Each school uses its own dorms. One confirmed pair per academic year."""
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from models import (
    db, User, RoommateProfile as Profile, RoommateWish as Wish,
    RoommatePair as Pair, RoommateSeat as Seat,
)

bp = Blueprint("roommates", __name__)

UM = "澳门大学"
MUST = "澳门科技大学"
MPU = "澳门理工大学"
UTM = "澳门旅游大学"
CITYU = "澳门城市大学"
COLLEGES = (
    "蔡继有书院",
    "郑裕彤书院",
    "何鸿燊东亚书院",
    "霍英东珍禧书院",
    "曹光彪书院",
    "张昆仑书院",
    "吕志和书院",
    "马万祺罗柏心书院",
    "满珍纪念书院",
    "绍邦书院",
)
DEGREES = {"bachelor": "本科", "master": "硕士", "doctorate": "博士"}
GRAD_DORM = "研究生宿舍"
OFF_CAMPUS = "校外合租"
MPU_DORMS = (
    "明德楼", "南岸", "南方", "利新", "成和阁", "南成",
    "帝景苑", "中山新邨", "公园大道", "晋海", "荷兰花园", "氹仔校区",
)
UTM_HALLS = ("东亚楼", "望厦迎宾馆")
# 2026–2027 学生事务处宿舍导览。伟兴、银业同时写了国际生和研究生。
CITYU_PLACES = {
    "female": {
        "bachelor": ("新华邨", "伟兴"),
        "master": ("伟兴", "丽晶"),
        "doctorate": ("伟兴", "丽晶"),
    },
    "male": {
        "bachelor": ("南园", "怀情楼", "广成", "银业"),
        "master": ("新街坊", "中大金融中心", "银业"),
        "doctorate": ("新街坊", "中大金融中心", "银业"),
    },
}
LEADS = {
    "um": "本科生按自己的书院。硕士和博士住研究生宿舍，不选书院。不住宿舍就选校外合租，写下区域。同性别、同一区域互相看见，本科和研究生可以一起。确认一位后，本学年不能再选，解除后才可以。",
    "must": "科大没有书院。本科生住校园宿舍，由学校分配。硕士和博士多住校外的研究生宿舍。不住宿舍就选校外合租，写下区域。同性别、同一区域互相看见，本科和研究生可以一起。确认一位后，本学年不能再选，解除后才可以。",
    "mpu": "理工没有书院。本科和研究生从同一批宿舍里选。不住宿舍就选校外合租，写下区域。只和同一住处、同性别的人互相看见，校外合租时本科和研究生可以一起。确认一位后，本学年不能再选，解除后才可以。",
    "utm": "旅游大学没有书院。宿舍主要是东亚楼，另有望厦迎宾馆。学校写明房间和室友随机分配，这里只帮你先找到人。不住宿舍就选校外合租，写下区域。确认一位后，本学年不能再选，解除后才可以。",
    "cityu": "城大没有书院。本科生和研究生住不同的宿舍，有的楼只住男生或女生。不住宿舍就选校外合租，写下区域，本科和研究生可以一起。确认一位后，本学年不能再选，解除后才可以。",
    "other": "按你填写的宿舍名称，或选校外合租并写下区域。只和同一住处、同性别的人互相看见。确认一位后，本学年不能再选，解除后才可以。",
}
SLEEP_LABELS = {"early": "23 点前睡", "flex": "不固定", "late": "24 点后睡"}
TIDIES = {"high": "喜欢整齐", "mid": "普通", "low": "不太收拾"}
SOCIALS = {"quiet": "希望安静", "either": "都可以", "chatty": "喜欢聊天"}
SMOKES = {"no": "不抽烟，也不想室友抽", "ok": "不介意"}
GUESTS = {"rare": "很少带人回来", "sometimes": "偶尔", "often": "经常"}
CHOICES = {"tidy": TIDIES, "social": SOCIALS, "smoke": SMOKES, "guests": GUESTS}


def sleep_text(value):
    """Old cards stored a fixed key. New cards store the time the student wrote."""
    return SLEEP_LABELS.get(value or "", value or "")


def lead_key(school):
    return {UM: "um", MUST: "must", MPU: "mpu", UTM: "utm", CITYU: "cityu"}.get(school, "other")


def official_places(school, degree, gender):
    """Dorms the school actually assigns. Empty means a free-text dorm name."""
    if degree not in DEGREES:
        return ()
    if school == UM:
        return COLLEGES if degree == "bachelor" else (GRAD_DORM,)
    if school == MUST:
        return ("校园宿舍",) if degree == "bachelor" else (GRAD_DORM,)
    if school == MPU:
        return MPU_DORMS
    if school == UTM:
        return UTM_HALLS
    if school == CITYU and gender in CITYU_PLACES:
        return CITYU_PLACES[gender].get(degree, ())
    return ()


def place_options(school, degree, gender):
    """Official dorms, plus off-campus sharing for people who do not live in one."""
    official = official_places(school, degree, gender)
    if not official:
        return ()
    return official + (OFF_CAMPUS,)


def ensure_roommate_columns():
    try:
        cols = {column["name"] for column in inspect(db.engine).get_columns("roommate_profiles")}
    except Exception:
        return
    if "area" not in cols:
        db.session.execute(text("ALTER TABLE roommate_profiles ADD COLUMN area VARCHAR(32) DEFAULT ''"))
        db.session.commit()


def housing_catalog(school):
    return {gender: {degree: list(place_options(school, degree, gender)) for degree in DEGREES}
            for gender in ("female", "male")}


def current_season(now=None):
    """Academic year in Macau. August opens the next year. November 2026 is 2026-2027."""
    local = now or datetime.now(timezone(timedelta(hours=8)))
    year = local.year
    start = year if local.month >= 8 else year - 1
    return f"{start}-{start + 1}"


def pair_for(user_id, season):
    return Pair.query.filter(
        Pair.season == season, db.or_(Pair.low_id == user_id, Pair.high_id == user_id)).first()


def same_pool(me, mine, other, theirs):
    return bool(
        me and other and mine and theirs
        and other.school == me.school and other.gender == me.gender
        and other.gender in ("male", "female")
        and housing(theirs) == housing(mine)
    )


def purge_roommates(user_id):
    pair_ids = [row.id for row in Pair.query.filter(db.or_(Pair.low_id == user_id, Pair.high_id == user_id))]
    if pair_ids:
        Seat.query.filter(Seat.pair_id.in_(pair_ids)).delete(synchronize_session=False)
    Profile.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    Wish.query.filter(db.or_(Wish.from_id == user_id, Wish.to_id == user_id)).delete(synchronize_session=False)
    Pair.query.filter(db.or_(Pair.low_id == user_id, Pair.high_id == user_id)).delete(synchronize_session=False)


def drop_stale_wishes(user, profile):
    """A wish only stays while both people still share a dorm and gender."""
    season = profile.season
    wishes = Wish.query.filter(
        Wish.season == season, db.or_(Wish.from_id == user.id, Wish.to_id == user.id)).all()
    for wish in wishes:
        other_id = wish.to_id if wish.from_id == user.id else wish.from_id
        other = db.session.get(User, other_id)
        theirs = db.session.get(Profile, (other_id, season))
        if not same_pool(user, profile, other, theirs):
            db.session.delete(wish)


def confirm_mutual(season, user_id):
    """If both people already chose each other, confirm the one pair for this year."""
    if pair_for(user_id, season):
        return False
    mine = db.session.get(Profile, (user_id, season))
    if not mine:
        return False
    for wish in Wish.query.filter_by(season=season, from_id=user_id):
        other_id = wish.to_id
        if pair_for(other_id, season) or not db.session.get(Wish, (season, other_id, user_id)):
            continue
        theirs = db.session.get(Profile, (other_id, season))
        other = theirs.user if theirs else None
        if mine.user.is_suspended() or (other and other.is_suspended()):
            continue
        if not same_pool(mine.user, mine, other, theirs):
            continue
        low, high = sorted((user_id, other_id))
        pair = Pair(season=season, low_id=low, high_id=high)
        db.session.add(pair)
        try:
            db.session.flush()
            db.session.add(Seat(season=season, user_id=low, pair_id=pair.id))
            db.session.add(Seat(season=season, user_id=high, pair_id=pair.id))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return pair_for(user_id, season) is not None
    return False


@bp.before_request
def authorize():
    user = db.session.get(User, session.get("user_id")) if session.get("user_id") else None
    if not user:
        if request.method == "GET":
            return redirect("/#step1-card")
        abort(401, "请先登录。")
    if not user.email_verified:
        abort(403, "请先完成学校邮箱验证。")
    g.roommate_user = user
    if "roommate_csrf" not in session:
        session["roommate_csrf"] = secrets.token_urlsafe(32)
    if request.method == "POST":
        actual = request.form.get("csrf", "")
        if not secrets.compare_digest(actual.encode(), session["roommate_csrf"].encode()):
            abort(400, "页面已过期，请刷新后重试。")


@bp.context_processor
def shared():
    user = getattr(g, "roommate_user", None)
    return dict(
        roommate_user=user, roommate_csrf=session.get("roommate_csrf", ""),
        colleges=COLLEGES, degrees=DEGREES, sleep_text=sleep_text, tidies=TIDIES,
        socials=SOCIALS, smokes=SMOKES, guests=GUESTS, um_school=UM, must_school=MUST,
        grad_dorm=GRAD_DORM, off_campus=OFF_CAMPUS, housing=housing, leads=LEADS,
    )


@bp.get("/roommates")
def board():
    user = g.roommate_user
    season = current_season()
    mine = db.session.get(Profile, (user.id, season))
    if mine and confirm_mutual(season, user.id):
        flash("双方都想住一起，本学年的舍友已确认。学校邮箱只在这里互见。")
    pair = pair_for(user.id, season)
    partner = None
    if pair:
        partner = db.session.get(User, pair.high_id if pair.low_id == user.id else pair.low_id)
    degree = request.args.get("degree", "all" if mine and mine.college == OFF_CAMPUS else "same")
    if degree not in ("same", "all"):
        abort(400, "无效筛选条件。")
    cards = []
    wished = set()
    incoming = set()
    if mine and not pair:
        query = Profile.query.filter(Profile.season == season, Profile.user_id != user.id)
        rows = [row for row in query.all()
                if row.user.school == user.school and row.user.gender == user.gender
                and housing(row) == housing(mine) and not pair_for(row.user_id, season)
                and not row.user.is_suspended()]
        undergrad_only = mine.college != OFF_CAMPUS and user.school in (UM, MUST) and mine.degree == "bachelor"
        if undergrad_only or degree == "same":
            rows = [row for row in rows if row.degree == mine.degree]
        wished = {row.to_id for row in Wish.query.filter_by(season=season, from_id=user.id)}
        incoming = {row.from_id for row in Wish.query.filter_by(season=season, to_id=user.id)}
        cards = sorted(rows, key=lambda row: (-habit_score(mine, row), row.user_id))
    return render_template(
        "roommates.html", season=season, mine=mine, pair=pair, partner=partner,
        cards=cards, wished=wished, incoming=incoming, degree=degree,
        lead_key=lead_key(user.school), housing_catalog=housing_catalog(user.school))


def housing(profile):
    """Use the one official place when the school does not let students pick among several."""
    if not profile:
        return ""
    if profile.college == OFF_CAMPUS:
        area = (profile.area or "").strip()
        return f"{OFF_CAMPUS}·{area}" if area else ""
    user = profile.user
    gender = user.gender if user and user.gender in ("male", "female") else ""
    school = user.school if user else ""
    official = official_places(school, profile.degree, gender)
    if len(official) == 1:
        return official[0]
    return profile.college


def habit_score(mine, other):
    score = 0
    if mine.sleep and mine.sleep == other.sleep:
        score += 2
    for field in CHOICES:
        if getattr(mine, field) == getattr(other, field):
            score += 1 if field == "guests" else 2
        elif field == "smoke":
            score -= 2
    return score


def clean_sleep():
    value = request.form.get("sleep", "").strip()
    if not 2 <= len(value) <= 24:
        abort(400, "睡觉时间请自己填写，2 到 24 个字。")
    return value


def clean_choice(name):
    value = request.form.get(name, "")
    if value not in CHOICES[name]:
        abort(400, "请把作息选完整。")
    return value


@bp.post("/roommates")
def save():
    user = g.roommate_user
    season = current_season()
    degree = request.form.get("degree", "")
    if degree not in DEGREES:
        abort(400, "请选择学历。")
    picked = request.form.get("my_gender", "").strip()
    if picked and picked not in ("male", "female"):
        abort(400, "请选择你的性别。")
    if user.gender not in ("male", "female"):
        if picked not in ("male", "female"):
            abort(400, "宿舍按性别分，请先选择你的性别。")
        user.gender = picked
    options = place_options(user.school, degree, user.gender)
    official = tuple(name for name in options if name != OFF_CAMPUS)
    posted = request.form.get("college", "").strip()
    if posted == OFF_CAMPUS:
        college = OFF_CAMPUS
    elif len(official) == 1:
        college = official[0]
    elif official:
        college = posted
        if college not in official:
            abort(400, "请选择宿舍。")
    else:
        college = posted
        if not 2 <= len(college) <= 32:
            abort(400, "请填写宿舍名称。")
    area = request.form.get("area", "").strip()
    if college == OFF_CAMPUS:
        if not 2 <= len(area) <= 24:
            abort(400, "校外合租请写下大概区域，例如氹仔、横琴或澳门半岛。")
    else:
        area = ""
    account_degree = user.education_level if user.education_level in DEGREES else ""
    if account_degree and degree != account_degree:
        abort(400, "学历和账号里的不一致。要改学历，先到个人资料里改。")
    if not account_degree:
        user.education_level = degree
    note = request.form.get("note", "").strip()
    if len(note) > 200:
        abort(400, "补充请控制在 200 字以内。")
    profile = db.session.get(Profile, (user.id, season)) or Profile(user_id=user.id, season=season)
    paired = pair_for(user.id, season)
    if paired and profile.degree and (
        profile.degree != degree or profile.college != college or (profile.area or "") != area
    ):
        abort(400, "本学年已确认舍友。要换住处，先解除。")
    profile.college = college
    profile.area = area
    profile.degree = degree
    profile.sleep = clean_sleep()
    for field in CHOICES:
        setattr(profile, field, clean_choice(field))
    profile.note = note
    profile.updated_at = datetime.utcnow()
    db.session.add(profile)
    if not paired:
        drop_stale_wishes(user, profile)
    db.session.commit()
    if paired:
        flash("作息已更新。本学年的舍友确认还在。")
    else:
        where = housing(profile) or college
        flash(f"作息已保存。同性别、同在{where}的同学能看到这张卡片。")
    return redirect(url_for("roommates.board"))


@bp.post("/roommates/wishes/<int:user_id>")
def wish(user_id):
    user = g.roommate_user
    season = current_season()
    mine = db.session.get(Profile, (user.id, season))
    theirs = db.session.get(Profile, (user_id, season))
    if not mine or not theirs or user_id == user.id:
        abort(404, "找不到这位同学的舍友卡片。")
    if theirs.user.school != user.school or theirs.user.gender != user.gender or housing(theirs) != housing(mine):
        abort(403, "只能在同一处宿舍、同性别里选舍友。")
    if theirs.user.is_suspended():
        abort(403, "这位同学这周暂停使用，暂时不能选择。")
    if confirm_mutual(season, user.id):
        flash("双方都想住一起，本学年的舍友已确认。学校邮箱只在这里互见。")
        return redirect(url_for("roommates.board"))
    if pair_for(user.id, season) or pair_for(user_id, season):
        abort(400, "本学年已经确认过舍友。解除后才能再选。")
    existing = db.session.get(Wish, (season, user.id, user_id))
    back = db.session.get(Wish, (season, user_id, user.id))
    if existing and not back:
        db.session.delete(existing)
        db.session.commit()
        flash("已收回。")
        return redirect(url_for("roommates.board"))
    if not existing:
        db.session.add(Wish(season=season, from_id=user.id, to_id=user_id))
    try:
        if back:
            db.session.flush()
            if confirm_mutual(season, user.id):
                flash("双方都想住一起，本学年的舍友已确认。学校邮箱只在这里互见。")
            else:
                db.session.commit()
                flash("对方本学年已经确认过舍友。解除后才能再选。")
        else:
            db.session.commit()
            flash("已记下。对方也选择你之后，才会确认。")
    except IntegrityError:
        db.session.rollback()
        flash("刚刚已经处理过了，请刷新后再看。")
    return redirect(url_for("roommates.board"))


@bp.post("/roommates/pair/cancel")
def cancel():
    user = g.roommate_user
    season = current_season()
    pair = pair_for(user.id, season)
    if not pair:
        abort(404, "本学年还没有确认舍友。")
    other = pair.high_id if pair.low_id == user.id else pair.low_id
    Seat.query.filter(Seat.season == season, Seat.user_id.in_((user.id, other))).delete(synchronize_session=False)
    Wish.query.filter(
        Wish.season == season,
        db.or_(
            db.and_(Wish.from_id == user.id, Wish.to_id == other),
            db.and_(Wish.from_id == other, Wish.to_id == user.id),
        )).delete(synchronize_session=False)
    db.session.delete(pair)
    db.session.commit()
    flash("已解除。本学年可以再选一位。")
    return redirect(url_for("roommates.board"))
