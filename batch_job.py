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
    BATCH_MATCH_DAY, BATCH_MATCH_HOUR, MATCH_MIN_SCORE, SCHOOL_DOMAINS,
)
from models import db, User, Match
from matcher import batch_match_school, orientation_compatible
from questionnaire import check_dealbreakers, get_compatibility_insight
from email_service import send_match_result_email


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
    """本自然周起始（周一 00:00，本地时间）。"""
    now = now or datetime.now()
    monday = now.date() - timedelta(days=now.weekday())
    return datetime.combine(monday, datetime.min.time())


def count_new_matches_this_week(user_id, now=None):
    start = week_window_start(now)
    # 用 UTC 存库，这里按「最近 7 天」更稳妥地兼容 utcnow
    since = (now or datetime.utcnow()) - timedelta(days=7)
    return Match.query.filter(
        ((Match.user1_id == user_id) | (Match.user2_id == user_id)),
        Match.created_at >= since,
    ).count()


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
        return existing, False

    m = Match(
        user1_id=user_a.id,
        user2_id=user_b.id,
        score=score,
        mode=mode,
        insight_json=payload,
    )
    db.session.add(m)
    return m, True


def persist_user_matches(user, scored_pairs, mode, mail_cfg, weekly_new_limit=None):
    """
    将 [(other, score), ...] 落库并通知。
    weekly_new_limit: 本周新建匹配上限；None 表示不限制（批量任务用）。
    返回结果摘要 dict。
    """
    saved = []
    to_notify = []
    skipped_dealbreaker = 0
    updated_existing = 0
    skipped_quota = 0

    new_this_week = count_new_matches_this_week(user.id) if weekly_new_limit is not None else 0

    for other, score in scored_pairs:
        if check_dealbreakers(user.answers, other.answers):
            skipped_dealbreaker += 1
            continue

        insight = get_compatibility_insight(
            user.feature_vector, other.feature_vector,
            user.answers, other.answers,
        )

        existing = Match.query.filter(
            ((Match.user1_id == user.id) & (Match.user2_id == other.id)) |
            ((Match.user1_id == other.id) & (Match.user2_id == user.id))
        ).first()

        if existing:
            existing.score = score
            existing.mode = mode
            existing.insight_json = json.dumps(insight, ensure_ascii=False)
            updated_existing += 1
            saved.append((other, score, insight))
            continue

        if weekly_new_limit is not None and new_this_week >= weekly_new_limit:
            skipped_quota += 1
            continue

        m = Match(
            user1_id=user.id, user2_id=other.id,
            score=score, mode=mode,
            insight_json=json.dumps(insight, ensure_ascii=False),
        )
        db.session.add(m)
        saved.append((other, score, insight))
        to_notify.append((other, score, insight))
        new_this_week += 1

    if saved:
        user.last_matched_at = datetime.utcnow()
    db.session.commit()

    mail_ok_count = 0
    mail_fail_count = 0
    for other, score, insight in to_notify:
        ok1, _ = send_match_result_email(user.email, [(other, score)], mail_cfg, insight)
        ok2, _ = send_match_result_email(other.email, [(user, score)], mail_cfg, insight)
        if ok1:
            mail_ok_count += 1
        else:
            mail_fail_count += 1
        if not ok2:
            mail_fail_count += 1
        mrec = Match.query.filter(
            ((Match.user1_id == user.id) & (Match.user2_id == other.id)) |
            ((Match.user1_id == other.id) & (Match.user2_id == user.id))
        ).first()
        if mrec:
            # 邮件失败也不影响页面结果；仅标记是否尝试通知过
            mrec.notified = True
    if to_notify:
        db.session.commit()

    return {
        "saved": saved,
        "updated_existing": updated_existing,
        "newly_notified": len(to_notify),
        "dealbreaker_skipped": skipped_dealbreaker,
        "quota_skipped": skipped_quota,
        "mail_ok_count": mail_ok_count,
        "mail_fail_count": mail_fail_count,
    }


def ready_users(school=None):
    q = User.query.filter(
        User.email_verified == True,
        User.feature_vector_json.isnot(None),
        User.gender.isnot(None),
        User.looking_for.isnot(None),
        User.wechat_id.isnot(None),
    )
    if school:
        q = q.filter(User.school == school)
    return [u for u in q.all() if u.ready_to_match()]


def run_batch_school(school, mail_cfg):
    """对单校执行一对一批量匹配。返回摘要。"""
    users = ready_users(school)
    if len(users) < 2:
        return {"school": school, "users": len(users), "pairs": 0, "created": 0, "updated": 0}

    pairs = batch_match_school(users, filter_same_gender=True)
    created = 0
    updated = 0
    notified = 0

    for a, b, score in pairs:
        if score < MATCH_MIN_SCORE:
            continue
        if not orientation_compatible(a, b):
            continue
        if check_dealbreakers(a.answers, b.answers):
            continue

        insight = get_compatibility_insight(
            a.feature_vector, b.feature_vector, a.answers, b.answers,
        )
        m, is_new = _get_or_create_pair(a, b, score, insight, mode="batch")
        if is_new:
            created += 1
        else:
            updated += 1

        a.last_matched_at = datetime.utcnow()
        b.last_matched_at = datetime.utcnow()

        if is_new or not m.notified:
            send_match_result_email(a.email, [(b, score)], mail_cfg, insight)
            send_match_result_email(b.email, [(a, score)], mail_cfg, insight)
            m.notified = True
            notified += 1

    db.session.commit()
    return {
        "school": school,
        "users": len(users),
        "pairs": len(pairs),
        "created": created,
        "updated": updated,
        "notified": notified,
    }


def run_batch_all(mail_cfg):
    schools = list(SCHOOL_DOMAINS.keys())
    results = []
    for school in schools:
        summary = run_batch_school(school, mail_cfg)
        results.append(summary)
        print(
            f"  [{school}] users={summary['users']} pairs={summary.get('pairs', 0)} "
            f"created={summary.get('created', 0)} updated={summary.get('updated', 0)}"
        )
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
