#!/usr/bin/env python3
"""
催填：已验证邮箱但问卷未完成的用户。

用法（项目根目录，建议 venv）：
  python scripts/nudge_incomplete.py              # dry-run，只列出候选人
  python scripts/nudge_incomplete.py --send       # 真正发信（需 MAIL_ENABLED + 通道可用）
  python scripts/nudge_incomplete.py --send --days 3 --limit 50
  python scripts/nudge_incomplete.py --email someone@um.edu.mo --send

限频：同一用户 incomplete_nudge_at 在 N 天内不重复（默认 INCOMPLETE_NUDGE_COOLDOWN_DAYS=3）。
总开关：MAIL_INCOMPLETE_NUDGE_ENABLED（默认 true）；关闭时脚本也会拒绝 --send。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    p = argparse.ArgumentParser(description="催填未完成问卷邮件")
    p.add_argument(
        "--send",
        action="store_true",
        help="真正发信（默认只 dry-run 列出）",
    )
    p.add_argument(
        "--days",
        type=int,
        default=None,
        help="冷却天数（默认读配置 INCOMPLETE_NUDGE_COOLDOWN_DAYS）",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=200,
        help="最多处理人数（默认 200）",
    )
    p.add_argument(
        "--email",
        type=str,
        default="",
        help="只针对单个邮箱（仍受冷却与开关约束）",
    )
    args = p.parse_args()

    from app import app, get_mail_config
    from config import (
        MAIL_INCOMPLETE_NUDGE_ENABLED,
        INCOMPLETE_NUDGE_COOLDOWN_DAYS,
        PUBLIC_URL,
        MAIL_ENABLED,
    )
    from email_service import send_incomplete_nudge_email, send_incomplete_nudges
    from models import db, User
    from datetime import datetime, timedelta

    with app.app_context():
        days = args.days if args.days is not None else INCOMPLETE_NUDGE_COOLDOWN_DAYS
        print(f"PUBLIC_URL={PUBLIC_URL}")
        print(f"MAIL_ENABLED={MAIL_ENABLED} MAIL_INCOMPLETE_NUDGE_ENABLED={MAIL_INCOMPLETE_NUDGE_ENABLED}")
        print(f"cooldown_days={days} dry_run={not args.send}")

        if not MAIL_INCOMPLETE_NUDGE_ENABLED:
            print("已关闭：MAIL_INCOMPLETE_NUDGE_ENABLED=false，退出。", file=sys.stderr)
            sys.exit(1)

        mail_cfg = get_mail_config()
        target_email = (args.email or "").strip().lower()

        if target_email:
            user = User.query.filter(User.email == target_email).first()
            if not user:
                print(f"用户不存在: {target_email}", file=sys.stderr)
                sys.exit(1)
            if not user.email_verified:
                print(f"未验证邮箱，跳过: {target_email}", file=sys.stderr)
                sys.exit(1)
            if user.questionnaire_completed():
                print(f"问卷已完成，跳过: {target_email}")
                sys.exit(0)
            cutoff = datetime.utcnow() - timedelta(days=max(1, days))
            if user.incomplete_nudge_at and user.incomplete_nudge_at > cutoff:
                print(
                    f"冷却中（上次 {user.incomplete_nudge_at.isoformat()}），跳过: {target_email}"
                )
                sys.exit(0)
            print(f"候选: #{user.id} {user.email} name={user.name or '-'}")
            if not args.send:
                print("dry-run：未发信。加 --send 才会发送。")
                return
            ok, info = send_incomplete_nudge_email(user.email, mail_cfg, name=user.name)
            if ok:
                user.incomplete_nudge_at = datetime.utcnow()
                db.session.commit()
                print(f"已发送 → {user.email} ({info})")
            else:
                print(f"发送失败 → {user.email}: {info}", file=sys.stderr)
                sys.exit(1)
            return

        result = send_incomplete_nudges(
            mail_cfg,
            cooldown_days=days,
            limit=args.limit,
            dry_run=not args.send,
        )
        print(
            f"candidates={result['candidates']} "
            f"skipped_cooldown={result['skipped_cooldown']} "
            f"sent={result['sent']} failed={result['failed']}"
        )
        for e in result.get("emails") or []:
            print(f"  - {e}")
        if not args.send:
            print("dry-run：未发信。确认名单后加 --send。")
        else:
            print("完成。")


if __name__ == "__main__":
    main()
