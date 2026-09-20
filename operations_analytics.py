"""Participation events and completed-week snapshots; no inferred past history."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from models import db, Match, PoolEvent, ParticipationWeek, WeeklyParticipation, User


EVENT_LABELS = {"pause": "退出参与", "resume": "恢复参与", "feedback": "退出反馈"}


def set_pool_participation(user, enabled, reason_code=None, reason_note=None):
    """Caller commits with the account update; repeated requests add no transition."""
    previous = user.is_open_to_match()
    user.open_to_match = enabled
    if not enabled:
        user.opt_in_week = None
    if previous != enabled:
        db.session.add(PoolEvent(user_id=user.id, kind="resume" if enabled else "pause",
                                 reason_code=reason_code, reason_note=reason_note))


def record_exit_feedback(user, code, note):
    db.session.add(PoolEvent(user_id=user.id, kind="feedback", reason_code=code,
                             reason_note=note or None))


def record_match_success(match):
    """Keep existing weekly outcomes successful even if the peer later deletes their account."""
    day = match.created_at.date()
    start = day - timedelta(days=day.weekday())
    WeeklyParticipation.query.filter(
        WeeklyParticipation.week_start == start,
        WeeklyParticipation.user_id.in_([match.user1_id, match.user2_id]),
    ).update({WeeklyParticipation.matched: True}, synchronize_session="fetch")


def record_completed_week(user_ids, week_start, now=None):
    """Merge successful reruns of a week; a recorded success never becomes failure."""
    now = now or datetime.utcnow()
    start = datetime.combine(week_start, datetime.min.time())
    end = start + timedelta(days=7)
    matched_ids = set()
    for match in Match.query.filter(Match.created_at >= start, Match.created_at < end):
        matched_ids.update((match.user1_id, match.user2_id))
    # Skip accounts deleted since the batch began.
    ids = {u.id for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else set()
    for uid in ids:
        try:
            with db.session.begin_nested():
                db.session.add(WeeklyParticipation(user_id=uid, week_start=week_start,
                                                    matched=uid in matched_ids))
                db.session.flush()
        except IntegrityError:
            pass
    if matched_ids:
        WeeklyParticipation.query.filter(WeeklyParticipation.week_start == week_start,
                                         WeeklyParticipation.user_id.in_(matched_ids)).update(
                                             {WeeklyParticipation.matched: True}, synchronize_session=False)
    try:
        with db.session.begin_nested():
            db.session.add(ParticipationWeek(week_start=week_start, completed_at=now))
            db.session.flush()
    except IntegrityError:
        ParticipationWeek.query.filter_by(week_start=week_start).update({"completed_at": now})
    db.session.commit()


def operations_data(users, week_key, now):
    ids = {u.id for u in users}
    verified = [u for u in users if u.email_verified]
    ready = [u for u in verified if u.ready_to_match()]
    pool = [u for u in ready if u.is_open_to_match()]
    opted = [u for u in pool if u.opt_in_week == week_key]
    stages = []
    previous = len(users)
    for label, members in [("现存注册账号", users), ("已验证邮箱", verified),
                           ("资料完整", ready), ("开启参与", pool), ("本周报名", opted)]:
        count = len(members)
        stages.append(dict(label=label, count=count,
                           rate=round(count * 100 / previous, 1) if previous else None))
        previous = count

    cutoff = now - timedelta(days=7)
    event_query = PoolEvent.query.filter(PoolEvent.user_id.in_(ids))
    counts = Counter(dict(db.session.query(PoolEvent.kind, db.func.count(PoolEvent.id)).filter(
        PoolEvent.user_id.in_(ids), PoolEvent.created_at >= cutoff).group_by(PoolEvent.kind).all()))
    events = [{"time": (e.created_at + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M"),
               "kind": EVENT_LABELS.get(e.kind, e.kind), "reason": e.reason_code,
               "note": e.reason_note or "—"}
              for e in event_query.order_by(PoolEvent.created_at.desc(), PoolEvent.id.desc()).limit(50)]

    weeks = ParticipationWeek.query.order_by(ParticipationWeek.week_start.desc()).all()
    latest = weeks[0].week_start if weeks else None
    history = defaultdict(dict)
    for row in WeeklyParticipation.query.filter(WeeklyParticipation.user_id.in_(ids)):
        history[row.user_id][row.week_start] = row.matched
    # Successful reveals after a batch also end the wait; do not require another batch run.
    matches = Match.query.filter(Match.created_at >= datetime.combine(min(w.week_start for w in weeks), datetime.min.time())).all() if weeks else []
    recent_success = set()
    for match in matches:
        start = match.created_at.date() - timedelta(days=match.created_at.weekday())
        for uid in (match.user1_id, match.user2_id):
            if uid in ids:
                if start in history[uid]:
                    history[uid][start] = True
                if latest and start >= latest:
                    recent_success.add(uid)
    waiting = Counter()
    distribution = Counter()
    for user in pool:
        streak, cursor = 0, latest
        while cursor and history[user.id].get(cursor) is False:
            streak += 1
            cursor -= timedelta(days=7)
        if user.id in recent_success:
            streak = 0
        if streak:
            distribution[streak] += 1
            if streak >= 2:
                waiting[(user.school, user.gender)] += 1
    participants = [rows[latest] for rows in history.values() if latest in rows] if latest else []
    return dict(stages=stages, pauses=counts["pause"], resumes=counts["resume"], events=events,
                latest_week=latest.isoformat() if latest else None,
                latest_completed=(weeks[0].completed_at + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M") if weeks else None,
                participants=len(participants), matched=sum(participants),
                match_rate=round(sum(participants) * 100 / len(participants), 1) if participants else None,
                distribution=[{"weeks": n, "count": c} for n, c in sorted(distribution.items())],
                waiting_total=sum(waiting.values()),
                waiting=[{"school": s, "gender": g, "count": c} for (s, g), c in waiting.most_common()])
