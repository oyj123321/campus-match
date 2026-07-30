"""
CampusMatch 批量匹配任务（MVP 1.2）

用法:
  python batch_job.py --now          # 立刻跑一轮全校批量匹配
  python batch_job.py --schedule     # 前台阻塞，等到每周二 21:00 再跑（可配合任务计划）

也可由 app.py 在 BATCH_SCHEDULER_ENABLED=true 时后台线程自动调度。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta

from config import (
    BATCH_MATCH_DAY, BATCH_MATCH_HOUR, MATCH_MIN_SCORE, MATCH_WEEKLY_NEW_LIMIT,
    SCHOOL_DOMAINS, CROSS_SCHOOL_MATCHING_ENABLED,
)
from models import db, User, Match
from matcher import batch_match_school, orientation_compatible
from questionnaire import check_dealbreakers, get_compatibility_insight
from email_service import send_match_result_email
from match_pool import is_blocked_pair, school_compatible, vectors_aligned


WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def next_batch_datetime(now=None):
    """下一次批量匹配的本地时间（按 BATCH_MATCH_DAY / HOUR）。"""
    now = now or datetime.now()
    target = now.replace(hour=BATCH_MATCH_HOUR, minute=0, second=0, microsecond=0)
    days_ahead = (BATCH_MATCH_DAY - now.weekday()) % 7
    if days_ahead == 0 and now >= target:
        days_ahead = 7
    return target + timedelta(days=days_ahead)


def week_window_start(now=None):
    """本自然周起始（周一 00:00，UTC，与 Match.created_at 对齐）。"""
    now = now or datetime.utcnow()
    monday = now.date() - timedelta(days=now.weekday())
    return datetime.combine(monday, datetime.min.time())


def count_new_matches_this_week(user_id, now=None):
    """本自然周内，该用户作为任一方参与的「新建」有效匹配次数。"""
    since = week_window_start(now)
    return Match.query.filter(
        ((Match.user1_id == user_id) | (Match.user2_id == user_id)),
        Match.created_at >= since,
        Match.active.is_(True),
    ).count()


def weekly_quota_remaining(user_id, limit=None, now=None):
    """剩余可参与次数；默认上限来自 MATCH_WEEKLY_NEW_LIMIT。"""
    lim = MATCH_WEEKLY_NEW_LIMIT if limit is None else limit
    used = count_new_matches_this_week(user_id, now=now)
    return max(0, lim - used)


def users_without_weekly_quota(user_ids, limit=None, now=None):
    """已用尽本周匹配额度的用户 ID 集合。"""
    out = set()
    for uid in user_ids:
        if weekly_quota_remaining(uid, limit=limit, now=now) <= 0:
            out.add(uid)
    return out


def active_partner_id(user_id):
    """当前有效配对对方 ID；无则 None。"""
    m = Match.query.filter(
        ((Match.user1_id == user_id) | (Match.user2_id == user_id)),
        Match.active.is_(True),
    ).first()
    if not m:
        return None
    return m.user2_id if m.user1_id == user_id else m.user1_id


def partner_accepts_match(user_id, partner_id, weekly_new_limit=None):
    """
    对方本周是否还能被配：有剩余额度，或本周额度已用尽但当前有效对象就是自己
    （允许刷新同一对，禁止抢走别人本周已配到的人）。
    """
    if weekly_new_limit is None:
        return True
    if weekly_quota_remaining(partner_id, limit=weekly_new_limit) > 0:
        return True
    return active_partner_id(partner_id) == user_id

def deactivate_other_matches(user_id, keep_partner_id):
    """一对一：除 keep_partner 外，该用户其余配对全部失效（不再展示微信号等）。"""
    rows = Match.query.filter(
        ((Match.user1_id == user_id) | (Match.user2_id == user_id)),
        Match.active.is_(True),
    ).all()
    for m in rows:
        other_id = m.user2_id if m.user1_id == user_id else m.user1_id
        if other_id == keep_partner_id:
            m.active = True
        else:
            m.active = False


def enforce_one_to_one_active(user_a, user_b, match_row):
    """确立 A-B 为双方唯一有效配对。"""
    match_row.active = True
    deactivate_other_matches(user_a.id, user_b.id)
    deactivate_other_matches(user_b.id, user_a.id)


def _get_or_create_pair(user_a, user_b, score, insight, mode="batch"):
    """写入或更新一对匹配。返回 (match, is_new)。"""
    existing = Match.query.filter(
        ((Match.user1_id == user_a.id) & (Match.user2_id == user_b.id)) |
        ((Match.user1_id == user_b.id) & (Match.user2_id == user_a.id))
    ).first()
    payload = json.dumps(insight, ensure_ascii=False)
    if existing:
        existing.score = score
        existing.mode = mode
        existing.insight_json = payload
        existing.active = True
        return existing, False

    m = Match(
        user1_id=user_a.id,
        user2_id=user_b.id,
        score=score,
        mode=mode,
        insight_json=payload,
        active=True,
        notified=False,
    )
    db.session.add(m)
    return m, True


def persist_user_matches(user, scored_pairs, mode, mail_cfg, weekly_new_limit=None):
    """
    将 [(other, score), ...] 落库并通知。
    weekly_new_limit: 本周新建匹配上限（发起方与被配方都计）；None 表示不限制。
    返回结果摘要 dict。
    """
    saved = []
    to_notify = []
    skipped_dealbreaker = 0
    updated_existing = 0
    skipped_quota = 0
    skipped_partner_quota = 0
    skipped_low_score = 0

    new_this_week = count_new_matches_this_week(user.id) if weekly_new_limit is not None else 0

    for other, score in scored_pairs:
        if score < MATCH_MIN_SCORE:
            skipped_low_score += 1
            continue
        if is_blocked_pair(user.id, other.id):
            continue
        if check_dealbreakers(user.answers, other.answers):
            skipped_dealbreaker += 1
            continue
        if weekly_new_limit is not None and not partner_accepts_match(
            user.id, other.id, weekly_new_limit=weekly_new_limit
        ):
            skipped_partner_quota += 1
            continue

        insight = get_compatibility_insight(
            user.feature_vector, other.feature_vector,
            user.answers, other.answers,
            score=score,
        )

        existing = Match.query.filter(
            ((Match.user1_id == user.id) & (Match.user2_id == other.id)) |
            ((Match.user1_id == other.id) & (Match.user2_id == user.id))
        ).first()

        if existing:
            existing.score = score
            existing.mode = mode
            existing.insight_json = json.dumps(insight, ensure_ascii=False)
            existing.active = True
            updated_existing += 1
            saved.append((other, score, insight, existing))
            # 用户主动点「开始匹配」时再次尝试发信（冷却限制频率）
            to_notify.append((other, score, insight, existing))
            enforce_one_to_one_active(user, other, existing)
            continue

        if weekly_new_limit is not None and new_this_week >= weekly_new_limit:
            skipped_quota += 1
            continue

        m = Match(
            user1_id=user.id, user2_id=other.id,
            score=score, mode=mode,
            insight_json=json.dumps(insight, ensure_ascii=False),
            notified=False,
            active=True,
        )
        db.session.add(m)
        db.session.flush()
        enforce_one_to_one_active(user, other, m)
        saved.append((other, score, insight, m))
        to_notify.append((other, score, insight, m))
        new_this_week += 1

    if saved:
        now = datetime.utcnow()
        user.last_matched_at = now
        for other, *_ in saved:
            other.last_matched_at = now
    db.session.commit()

    mail_ok_count = 0
    mail_fail_count = 0
    mail_details = []
    for other, score, insight, mrec in to_notify:
        ok1, info1 = send_match_result_email(user.email, [(other, score)], mail_cfg, insight)
        ok2, info2 = send_match_result_email(other.email, [(user, score)], mail_cfg, insight)
        mail_details.append({
            "to_self": user.email,
            "self_ok": bool(ok1),
            "self_info": str(info1)[:120],
            "to_partner": other.email,
            "partner_ok": bool(ok2),
            "partner_info": str(info2)[:120],
            "partner_name": other.name,
        })
        if ok1:
            mail_ok_count += 1
            # 只有「你自己」的邮箱发送成功，才算通知成功（对方种子邮箱常会 550）
            mrec.notified = True
        else:
            mail_fail_count += 1
            mrec.notified = False
        if not ok2:
            mail_fail_count += 1

    if to_notify:
        db.session.commit()

    return {
        "saved": [(o, s, insight) for o, s, insight, _ in saved],
        "updated_existing": updated_existing,
        "newly_notified": sum(1 for d in mail_details if d["self_ok"]),
        "dealbreaker_skipped": skipped_dealbreaker,
        "quota_skipped": skipped_quota,
        "partner_quota_skipped": skipped_partner_quota,
        "low_score_skipped": skipped_low_score,
        "mail_ok_count": mail_ok_count,
        "mail_fail_count": mail_fail_count,
        "mail_details": mail_details,
    }


def current_week_key(now=None):
    """ISO 周键，如 2026-W31。"""
    now = now or datetime.now()
    return now.strftime("%G-W%V")


def ready_users(school=None, require_opt_in=False):
    q = User.query.filter(
        User.email_verified == True,
        User.feature_vector_json.isnot(None),
        User.gender.isnot(None),
        User.looking_for.isnot(None),
    )
    if school:
        q = q.filter(User.school == school)
    users = [u for u in q.all() if u.ready_to_match()]
    if require_opt_in:
        week = current_week_key()
        users = [u for u in users if u.opt_in_week == week]
    return users


def run_batch_school(school, mail_cfg, require_opt_in=False, exclude_ids=None):
    """对单校执行一对一批量匹配。返回摘要（含 matched_ids）。"""
    exclude_ids = set(exclude_ids or ())
    users = [u for u in ready_users(school, require_opt_in=require_opt_in) if u.id not in exclude_ids]
    # 本周已配过的人不再进入池（双向一周一次）
    busy = users_without_weekly_quota([u.id for u in users])
    users = [u for u in users if u.id not in busy]
    if len(users) < 2:
        return {"school": school, "users": len(users), "pairs": 0, "created": 0, "updated": 0, "matched_ids": set()}

    pairs = batch_match_school(users, filter_same_gender=True)
    created = 0
    updated = 0
    notified = 0
    matched_ids = set()

    for a, b, score in pairs:
        if score < MATCH_MIN_SCORE:
            continue
        if a.id in exclude_ids or b.id in exclude_ids:
            continue
        if a.id in matched_ids or b.id in matched_ids:
            continue
        if not orientation_compatible(a, b):
            continue
        if not school_compatible(a, b):
            continue
        if is_blocked_pair(a.id, b.id):
            continue
        if not vectors_aligned(a, b):
            continue
        if check_dealbreakers(a.answers, b.answers):
            continue
        if not partner_accepts_match(a.id, b.id, weekly_new_limit=MATCH_WEEKLY_NEW_LIMIT):
            continue
        if not partner_accepts_match(b.id, a.id, weekly_new_limit=MATCH_WEEKLY_NEW_LIMIT):
            continue

        insight = get_compatibility_insight(
            a.feature_vector, b.feature_vector, a.answers, b.answers,
            score=score,
        )
        m, is_new = _get_or_create_pair(a, b, score, insight, mode="batch")
        enforce_one_to_one_active(a, b, m)
        matched_ids.add(a.id)
        matched_ids.add(b.id)
        if is_new:
            created += 1
        else:
            updated += 1

        a.last_matched_at = datetime.utcnow()
        b.last_matched_at = datetime.utcnow()

        if is_new or not m.notified:
            ok_a, _ = send_match_result_email(a.email, [(b, score)], mail_cfg, insight)
            ok_b, _ = send_match_result_email(b.email, [(a, score)], mail_cfg, insight)
            m.notified = bool(ok_a and ok_b)
            if ok_a or ok_b:
                notified += 1

    db.session.commit()
    return {
        "school": school,
        "users": len(users),
        "pairs": len(pairs),
        "created": created,
        "updated": updated,
        "notified": notified,
        "matched_ids": matched_ids,
    }


def run_batch_cross(mail_cfg, require_opt_in=False, exclude_ids=None):
    """跨校池：仅双方都开 allow_cross_school 的用户。"""
    if not CROSS_SCHOOL_MATCHING_ENABLED:
        return {"school": "跨校", "users": 0, "pairs": 0, "created": 0, "updated": 0, "matched_ids": set()}

    exclude_ids = set(exclude_ids or ())
    users = [
        u for u in ready_users(None, require_opt_in=require_opt_in)
        if u.id not in exclude_ids and getattr(u, "allow_cross_school", False)
    ]
    busy = users_without_weekly_quota([u.id for u in users])
    users = [u for u in users if u.id not in busy]
    # 至少要有 2 所学校才有意义
    schools = {u.school for u in users}
    if len(users) < 2 or len(schools) < 2:
        return {
            "school": "跨校",
            "users": len(users),
            "pairs": 0,
            "created": 0,
            "updated": 0,
            "matched_ids": set(),
            "note": "跨校池人数不足或同校",
        }

    # 复用 school 批量逻辑：临时把 school 标签忽略，靠 school_compatible 过滤
    # 直接跑匈牙利，再过滤非跨校对
    pairs = batch_match_school(users, filter_same_gender=True)
    created = updated = notified = 0
    matched_ids = set()
    kept = 0

    for a, b, score in pairs:
        if score < MATCH_MIN_SCORE:
            continue
        if a.school == b.school:
            continue  # 同校留给校内轮
        if a.id in matched_ids or b.id in matched_ids:
            continue
        if not school_compatible(a, b):
            continue
        if is_blocked_pair(a.id, b.id):
            continue
        if not orientation_compatible(a, b):
            continue
        if not vectors_aligned(a, b):
            continue
        if check_dealbreakers(a.answers, b.answers):
            continue
        if not partner_accepts_match(a.id, b.id, weekly_new_limit=MATCH_WEEKLY_NEW_LIMIT):
            continue
        if not partner_accepts_match(b.id, a.id, weekly_new_limit=MATCH_WEEKLY_NEW_LIMIT):
            continue

        insight = get_compatibility_insight(
            a.feature_vector, b.feature_vector, a.answers, b.answers,
            score=score,
        )
        m, is_new = _get_or_create_pair(a, b, score, insight, mode="batch")
        enforce_one_to_one_active(a, b, m)
        matched_ids.add(a.id)
        matched_ids.add(b.id)
        kept += 1
        if is_new:
            created += 1
        else:
            updated += 1
        a.last_matched_at = datetime.utcnow()
        b.last_matched_at = datetime.utcnow()
        if is_new or not m.notified:
            ok_a, _ = send_match_result_email(a.email, [(b, score)], mail_cfg, insight)
            ok_b, _ = send_match_result_email(b.email, [(a, score)], mail_cfg, insight)
            m.notified = bool(ok_a and ok_b)
            if ok_a or ok_b:
                notified += 1

    db.session.commit()
    return {
        "school": "跨校",
        "users": len(users),
        "pairs": kept,
        "created": created,
        "updated": updated,
        "notified": notified,
        "matched_ids": matched_ids,
    }


def run_batch_all(mail_cfg, require_opt_in=None):
    from config import REVEAL_REQUIRE_OPT_IN
    if require_opt_in is None:
        require_opt_in = REVEAL_REQUIRE_OPT_IN
    schools = list(SCHOOL_DOMAINS.keys())
    results = []
    already = set()
    for school in schools:
        summary = run_batch_school(school, mail_cfg, require_opt_in=require_opt_in, exclude_ids=already)
        already |= summary.get("matched_ids") or set()
        results.append(summary)
        print(
            f"  [{school}] users={summary['users']} pairs={summary.get('pairs', 0)} "
            f"created={summary.get('created', 0)} updated={summary.get('updated', 0)}"
        )
    cross = run_batch_cross(mail_cfg, require_opt_in=require_opt_in, exclude_ids=already)
    results.append(cross)
    already |= cross.get("matched_ids") or set()
    print(
        f"  [跨校] users={cross['users']} pairs={cross.get('pairs', 0)} "
        f"created={cross.get('created', 0)} updated={cross.get('updated', 0)}"
    )

    # 预约了本周但未配上的人：同样发「暂未配对」邮件
    no_match_sent = 0
    pool = ready_users(require_opt_in=require_opt_in) if require_opt_in else ready_users()
    for u in pool:
        if u.id in already:
            continue
        ok, _ = send_match_result_email(
            u.email,
            [],
            mail_cfg,
            reason="本周揭晓已结束，这一轮没有合适人选（池子人少、取向/底线不合，或对方本周已配过）。",
        )
        if ok:
            no_match_sent += 1
    print(f"  [未配对通知] sent={no_match_sent}")
    results.append({"no_match_notified": no_match_sent})
    return results


def schedule_loop(mail_cfg_factory, check_seconds=30):
    """阻塞循环：到点执行批量匹配。"""
    print(f"[batch] 调度中：每{WEEKDAY_NAMES[BATCH_MATCH_DAY]} {BATCH_MATCH_HOUR}:00")
    while True:
        nxt = next_batch_datetime()
        wait = (nxt - datetime.now()).total_seconds()
        print(f"[batch] 下次执行: {nxt.isoformat()} （约 {int(wait)} 秒后）")
        # 分段睡，便于 Ctrl+C
        end = time.time() + max(wait, 1)
        while time.time() < end:
            time.sleep(min(check_seconds, max(1, end - time.time())))
        print(f"[batch] 开始执行 {datetime.now().isoformat()}")
        try:
            run_batch_all(mail_cfg_factory())
        except Exception as e:
            print(f"[batch] 执行失败: {e}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="CampusMatch batch matcher")
    parser.add_argument("--now", action="store_true", help="立刻执行一轮")
    parser.add_argument("--schedule", action="store_true", help="按周调度阻塞运行")
    args = parser.parse_args(argv)

    # 延迟导入 app，避免循环依赖
    from app import app, get_mail_config, init_db

    init_db()
    with app.app_context():
        if args.now:
            print("[batch] 立即执行全校批量匹配…")
            run_batch_all(get_mail_config())
            return 0
        if args.schedule:
            schedule_loop(get_mail_config)
            return 0
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
