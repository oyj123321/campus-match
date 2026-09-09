"""Send one explicit delivery smoke test using the configured provider."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import get_mail_config
from email_service import _dispatch_email


parser = argparse.ArgumentParser()
parser.add_argument("--to", required=True, help="Mailbox that should receive the test")
args = parser.parse_args()

subject = "CampusMatch 阿里云邮件通道测试"
text = "CampusMatch 邮件通道测试成功。收到此邮件说明阿里云 SMTP 已正常提交。"
html = "<p>CampusMatch 邮件通道测试成功。</p><p>收到此邮件说明阿里云 SMTP 已正常提交。</p>"
ok, info = _dispatch_email(args.to.strip().lower(), subject, html, get_mail_config(), text, kind="verification")
print("accepted" if ok else f"failed: {info}")
raise SystemExit(0 if ok else 1)
