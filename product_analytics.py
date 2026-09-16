"""First-milestone cohort funnel, collected only for newly registered accounts."""
from datetime import datetime, timedelta
from flask import current_app, request, session
from sqlalchemy import func, select, union_all
from models import db, User, Match, ProductJourney

ENDPOINTS = {'api_register', 'api_verify', 'api_resend_verification', 'api_express_profile',
             'api_questionnaire', 'api_me', 'api_match_opt_in', 'api_match', 'api_get_matches'}


def enroll_new_user(user):
    """Called only when registration creates an account, in the same transaction."""
    try:
        with db.session.begin_nested():
            db.session.add(ProductJourney(user_id=user.id, school=user.school,
                                          registered_at=user.created_at))
            db.session.flush()
    except Exception:
        current_app.logger.exception('New-user milestone enrollment skipped')


def observe_response(response):
    if request.endpoint not in ENDPOINTS or response.status_code != 200 or request.method == 'DELETE':
        return response
    payload = response.get_json(silent=True)
    if not isinstance(payload, dict) or payload.get('ok') is not True:
        return response
    try:
        user = None
        if request.endpoint == 'api_register':
            data = request.get_json(silent=True) or {}
            user = User.query.filter_by(email=str(data.get('email', '')).strip().lower()).first()
        elif session.get('user_id'):
            user = db.session.get(User, session['user_id'])
        if user is None:
            return response
        row = db.session.get(ProductJourney, user.id)
        if row is None:
            return response  # do not manufacture historical timestamps for old users
        now = datetime.utcnow()
        if user.email_verified and row.verified_at is None:
            row.verified_at = now
        if row.verified_at and user.ready_to_match() and row.profile_at is None:
            row.profile_at = now
        participating = (request.endpoint == 'api_match' and request.method == 'POST') or (
            request.endpoint == 'api_match_opt_in' and request.method == 'POST' and payload.get('opted_in'))
        if participating and row.profile_at and row.participated_at is None:
            row.participated_at = now
        if request.endpoint == 'api_get_matches' and any(m.get('active') for m in payload.get('matches', [])):
            if row.viewed_at is None:
                row.viewed_at = now
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Product milestone recording skipped')
    return response


def record_batch_participation(user_ids):
    # Same analytics transaction as the round snapshot; failure rolls it back.
    ProductJourney.query.filter(ProductJourney.user_id.in_(user_ids),
                                ProductJourney.participated_at.is_(None),
                                ProductJourney.profile_at.isnot(None)).update(
        {ProductJourney.participated_at: datetime.utcnow()}, synchronize_session=False)


def cohort_summary(days=90, school=''):
    """Same registration cohort at every stage; reached-to-date, not period event totals."""
    days = days if days in (30, 90, 365) else 90
    matches = union_all(select(Match.user1_id.label('uid'), Match.created_at.label('at')),
                        select(Match.user2_id.label('uid'), Match.created_at.label('at'))).subquery()
    first_match = select(matches.c.uid, func.min(matches.c.at).label('at')).group_by(matches.c.uid).subquery()
    query = db.session.query(ProductJourney, first_match.c.at).outerjoin(
        first_match, first_match.c.uid == ProductJourney.user_id).filter(
        ProductJourney.registered_at >= datetime.utcnow() - timedelta(days=days))
    if school:
        query = query.filter(ProductJourney.school == school)
    counts = [0] * 6
    for journey, matched_at in query.all():
        participation = min(t for t in (journey.participated_at, matched_at) if t is not None) if (journey.participated_at or matched_at) else None
        stages = [journey.registered_at, journey.verified_at, journey.profile_at,
                  participation, matched_at, journey.viewed_at]
        previous = None
        for index, timestamp in enumerate(stages):
            if timestamp is None or (previous and timestamp < previous):
                break
            counts[index] += 1
            previous = timestamp
    labels = ['注册成功', '邮箱验证', '资料完整', '报名 / 参与匹配', '获得配对', '获取有效配对结果']
    rows = []
    for index, (label, count) in enumerate(zip(labels, counts)):
        rows.append({'label': label, 'count': count,
                     'percent': round(100*count/counts[0], 1) if counts[0] else 0,
                     'drop': counts[index-1]-count if index else 0})
    return {'rows': rows, 'total': counts[0], 'days': days, 'school': school}
