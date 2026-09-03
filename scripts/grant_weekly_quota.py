#!/usr/bin/env python3
"""给指定用户本周匹配补偿额度（仅当前 ISO 周有效）。

默认 dry-run。生产示例（补偿麦辣鸡翅本周 2 次，并关掉误配）：

  cd /opt/campus-match && source .venv/bin/activate
  python scripts/grant_weekly_quota.py --name 麦辣鸡翅 --bonus 2
  python scripts/grant_weekly_quota.py --name 麦辣鸡翅 --bonus 2 --clear-active --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    p = argparse.ArgumentParser(description="本周匹配额度补偿")
    p.add_argument("--name", help="昵称精确匹配")
    p.add_argument("--email", help="学校邮箱精确匹配")
    p.add_argument("--id", type=int, dest="user_id", help="用户数字 id")
    p.add_argument("--bonus", type=int, default=2, help="加在每周上限上的次数，默认 2")
    p.add_argument(
        "--clear-active",
        action="store_true",
        help="把该用户当前有效配对设为失效（误配补偿时用）",
    )
    p.add_argument("--apply", action="store_true", help="真正写入；默认只预览")
    args = p.parse_args()

    if args.bonus < 0:
        print("bonus 不能为负", file=sys.stderr)
        sys.exit(2)
    if not (args.name or args.email or args.user_id):
        print("请提供 --name / --email / --id 之一", file=sys.stderr)
        sys.exit(2)

    from app import app
    from batch_job import (
        count_new_matches_this_week, current_week_key, weekly_limit_for,
        weekly_quota_remaining,
    )
    from models import db, Match, User

    with app.app_context():
        q = User.query
        if args.user_id:
            q = q.filter(User.id == args.user_id)
        if args.email:
            q = q.filter(User.email == args.email.strip().lower())
        if args.name:
            q = q.filter(User.name == args.name)
        rows = q.all()
        if not rows:
            print("找不到用户")
            sys.exit(1)
        if len(rows) > 1:
            print("昵称不唯一，请改用 --id：")
            for u in rows:
                print(f"  id={u.id} email={u.email} name={u.name} school={u.school}")
            sys.exit(1)

        user = rows[0]
        week = current_week_key()
        matches = (
            Match.query.filter(
                (Match.user1_id == user.id) | (Match.user2_id == user.id)
            )
            .order_by(Match.created_at.desc())
            .all()
        )
        print(f"user id={user.id} name={user.name} school={user.school}")
        print(f"week={week} used={count_new_matches_this_week(user.id)}")
        print(
            f"before limit={weekly_limit_for(user)} "
            f"remaining={weekly_quota_remaining(user.id)} "
            f"last_matched_at={user.last_matched_at}"
        )
        for m in matches:
            oid = m.user2_id if m.user1_id == user.id else m.user1_id
            other = db.session.get(User, oid)
            oname = other.name if other else "?"
            print(
                f"  match#{m.id} active={m.active} {m.created_at} "
                f"partner id={oid} name={oname}"
            )

        user.quota_bonus = args.bonus
        user.quota_bonus_week = week
        user.last_matched_at = None
        if args.clear_active:
            for m in matches:
                if m.active:
                    m.active = False
                    print(f"  deactivate match#{m.id}")

        print(
            f"after limit={weekly_limit_for(user)} "
            f"remaining={weekly_quota_remaining(user.id)}"
        )
        if not args.apply:
            db.session.rollback()
            print("dry-run（未写入）。确认后加 --apply")
            return
        db.session.commit()
        print("已写入")


if __name__ == "__main__":
    main()
