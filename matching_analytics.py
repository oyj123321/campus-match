"""Batch-start diagnostics, persisted only as aggregate counts."""
import json
from collections import Counter
from datetime import datetime, timedelta
from itertools import combinations

from age_rules import age_compatible
from config import MATCH_MIN_SCORE, SCHOOL_DOMAINS, CROSS_SCHOOL_MATCHING_ENABLED
from match_pool import degree_compatible, school_compatible, vectors_aligned, pair_key
from matcher import orientation_compatible, _dealbreaker_conflict, pair_score
from models import Blocklist, Match, MatchingRound

LABELS = {
    'structure': '池内无人满足双向性别意愿',
    'age': '仅放宽年龄即可出现候选',
    'degree': '仅放宽学历即可出现候选',
    'school': '仅放宽学校即可出现候选',
    'multiple_options': '多种单项放宽均可出现候选',
    'combined': '多项限制或其他规则共同阻挡',
    'allocation': '有合适候选但本轮未分配',
}


def capture(require_opt_in):
    from batch_job import ready_users, users_without_weekly_quota
    pool = ready_users(require_opt_in=require_opt_in)
    busy = users_without_weekly_quota([u.id for u in pool])
    users = [u for u in pool if u.id not in busy and (u.school in SCHOOL_DOMAINS
             or (CROSS_SCHOOL_MATCHING_ENABLED and u.get_cross_schools()))]
    ids = [u.id for u in users]
    history = {pair_key(m.user1_id, m.user2_id) for m in Match.query.filter(
        Match.user1_id.in_(ids), Match.user2_id.in_(ids)).all()}
    blocked = {pair_key(b.user_id, b.blocked_user_id) for b in Blocklist.query.filter(
        Blocklist.user_id.in_(ids), Blocklist.blocked_user_id.in_(ids)).all()}
    state = diagnose(users, history, blocked)
    return users, state, {'version': 2, 'registered': len(pool), 'quota_excluded': len(busy),
                          'policy': [MATCH_MIN_SCORE, CROSS_SCHOOL_MATCHING_ENABLED, bool(require_opt_in)],
                          'participants': len(users), 'require_opt_in': require_opt_in}


def diagnose(users, history=(), blocked=()):
    state = {u.id: {'orientation': 0, 'eligible': 0, 'relax': set(),
                   'sole_candidate': None, 'history_candidates': 0} for u in users}
    for a, b in combinations(users, 2):
        if not orientation_compatible(a, b):
            continue
        for u in (a, b):
            state[u.id]['orientation'] += 1
        key = pair_key(a.id, b.id)
        if key in blocked or not vectors_aligned(a, b):
            continue
        if _dealbreaker_conflict(a, b) or pair_score(a, b) < MATCH_MIN_SCORE:
            continue
        failures = [name for name, passes in (
            ('age', age_compatible(a, b)), ('degree', degree_compatible(a, b)),
            ('school', school_compatible(a, b))) if not passes]
        if key in history:
            if not failures:
                for u in (a, b):
                    state[u.id]['history_candidates'] += 1
            continue
        for u in (a, b):
            if not failures:
                state[u.id]['eligible'] += 1
                state[u.id]['sole_candidate'] = b.id if u.id == a.id else a.id
            elif len(failures) == 1:
                state[u.id]['relax'].add(failures[0])
    demand = Counter(s['sole_candidate'] for s in state.values() if s['eligible'] == 1)
    for s in state.values():
        s['contested_sole'] = s['eligible'] == 1 and demand[s['sole_candidate']] > 1
    return state


def aggregate(users, state, matched_ids, report):
    matched = set(matched_ids) & set(state)
    reasons = {}
    for u in users:
        if u.id in matched:
            continue
        s = state[u.id]
        if s['eligible']:
            reason = 'allocation'
        elif not s['orientation']:
            reason = 'structure'
        elif len(s['relax']) == 1:
            reason = next(iter(s['relax']))
        elif s['relax']:
            reason = 'multiple_options'
        else:
            reason = 'combined'
        reasons[u.id] = reason

    def summarize(members):
        n = len(members)
        count = sum(u.id in matched for u in members)
        return dict(participants=n, matched=count, unmatched=n-count,
                    rate=round(100*count/n, 1) if n else 0,
                    reasons=dict(Counter(reasons[u.id] for u in members if u.id in reasons)),
                    age_missing=sum(u.age is None for u in members),
                    no_candidates=sum(state[u.id]['eligible'] == 0 for u in members),
                    one_candidate=sum(state[u.id]['eligible'] == 1 for u in members),
                    many_candidates=sum(state[u.id]['eligible'] >= 2 for u in members),
                    contested_sole=sum(state[u.id]['contested_sole'] for u in members),
                    history_exhausted=sum(state[u.id]['eligible'] == 0 and
                                          state[u.id]['history_candidates'] > 0 for u in members))
    schools = [dict(school=school, **summarize([u for u in users if u.school == school]))
               for school in sorted({u.school for u in users})]
    return dict(report, **summarize(users), schools=schools)


def dashboard_reports(days=90, school='', round_id=None):
    from admin_analysis import build_analysis
    days = days if days in (30, 90, 365) else 90
    rows = MatchingRound.query.filter(MatchingRound.started_at >= datetime.utcnow() - timedelta(days=days)).order_by(MatchingRound.id.desc()).limit(100).all()
    reports = []
    for row in rows:
        try:
            report = json.loads(row.report_json)
            if not isinstance(report, dict):
                raise ValueError('invalid report')
            if row.status == 'completed':
                if any(type(report.get(k)) is not int or report[k] < 0
                       for k in ('participants', 'matched', 'unmatched')):
                    raise ValueError('invalid totals')
                if report['matched'] + report['unmatched'] != report['participants']:
                    raise ValueError('inconsistent totals')
                if not isinstance(report.get('rate'), (int, float)) or not 0 <= report['rate'] <= 100:
                    raise ValueError('invalid rate')
        except (ValueError, TypeError):
            report = {'unavailable': True}
        reports.append(dict(report, id=row.id, status=row.status,
                            elapsed_minutes=max(0, (datetime.utcnow() - row.started_at).total_seconds() / 60),
                            time=(row.started_at + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')))
    return build_analysis(reports, LABELS, days, school, round_id)


def report_tips(latest):
    tips = []
    if latest:
        reasons = latest.get('reasons', {})
        if reasons.get('structure'):
            tips.append('存在双向性别意愿不匹配的供需缺口，优先扩大适配人群来源。')
        if any(reasons.get(k) for k in ('age', 'degree', 'school', 'multiple_options')):
            tips.append('部分未匹配用户只差一项偏好条件；可改善偏好设置提示，由用户自主决定是否放宽。')
        if reasons.get('allocation'):
            tips.append('部分用户有合适候选仍未配上，应结合一对一竞争、校内优先和分配策略检查，不能直接归因为人数不足。')
        if reasons.get('combined'):
            tips.append('存在多项条件、历史配对、屏蔽、底线或分数门槛共同影响，单独放宽年龄未必有效。')
        if latest.get('age_missing'):
            tips.append('参与者中仍有年龄未填写，提醒补全可能改善年龄条件下的候选覆盖。')
        if not latest.get('participants'):
            tips.append('本轮没有符合参与条件且尚有周额度的用户，请检查报名、资料完成和周额度。')
    return tips
