import unittest
import json
from pathlib import Path
from unittest.mock import patch

from flask import Flask

import admin_dashboard
from models import TrafficDay, User, db


ROOT = Path(__file__).resolve().parents[1]


def datetime_for_macau_today():
    from datetime import datetime, timedelta, timezone

    macau_now = datetime.now(timezone.utc) + timedelta(hours=8)
    utc_now = macau_now - timedelta(hours=8)
    return utc_now.isoformat().replace("+00:00", "Z")


class AdminDashboardTests(unittest.TestCase):
    def setUp(self):
        admin_dashboard._login_attempts.clear()
        self.app = Flask(
            __name__,
            template_folder=str(ROOT / "templates"),
            static_folder=str(ROOT / "static"),
        )
        self.app.config.update(
            TESTING=True,
            SECRET_KEY="test-session-secret",
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(self.app)
        self.app.register_blueprint(admin_dashboard.bp)

        @self.app.route("/")
        def index():
            return "ok"

        self.secret_patch = patch.object(admin_dashboard, "ADMIN_SECRET", "strong-admin-password")
        self.secret_patch.start()
        with self.app.app_context():
            db.create_all()
            db.session.add(User(school="澳门大学", email="student@um.edu.mo", email_verified=True))
            db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        self.secret_patch.stop()
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _login(self, password="strong-admin-password"):
        self.client.get("/admin/login")
        with self.client.session_transaction() as saved:
            csrf = saved["admin_csrf"]
        return self.client.post(
            "/admin/login",
            data={"password": password, "csrf": csrf},
            follow_redirects=False,
        )

    def test_admin_requires_login_and_accepts_configured_secret(self):
        self.assertEqual(self.client.get("/admin").status_code, 302)
        response = self._login()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/admin"))
        with patch.object(admin_dashboard, "_resend_summary", return_value={
            "available": False, "error": "测试模式", "used_today": 0,
            "daily_limit": 100, "remaining": 100, "statuses": {}, "recent": [],
        }):
            dashboard = self.client.get("/admin")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("运营总览", dashboard.get_data(as_text=True))
        self.assertNotIn("strong-admin-password", dashboard.get_data(as_text=True))
        self.assertEqual(dashboard.headers["Cache-Control"], "no-store")

    def test_wrong_password_is_rejected(self):
        response = self._login("wrong-password")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("strong-admin-password", response.get_data(as_text=True))

    def test_unicode_password_is_rejected_without_server_error(self):
        self.assertEqual(self._login("\u5bc6\u7801").status_code, 401)

    def test_expired_or_rotated_admin_session_is_rejected(self):
        self._login()
        with self.client.session_transaction() as saved:
            saved["admin_signed_at"] = admin_dashboard.time.time() - 8 * 3600 - 1
        self.assertEqual(self.client.get("/admin").status_code, 302)
        self._login()
        with patch.object(admin_dashboard, "ADMIN_SECRET", "changed-password"):
            self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_login_requires_csrf_and_limits_attempts(self):
        self.assertEqual(self.client.post("/admin/login", data={"password": "strong-admin-password"}).status_code, 400)
        for _ in range(6):
            self.assertEqual(self._login("wrong").status_code, 401)
        self.assertEqual(self._login().status_code, 429)

    def test_logout_revokes_admin_session(self):
        self._login()
        with self.client.session_transaction() as saved:
            csrf = saved["admin_csrf"]
        self.client.post("/admin/logout", data={"csrf": csrf})
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_unavailable_email_does_not_claim_unused_quota(self):
        self._login()
        with patch.object(admin_dashboard, "MAIL_ENABLED", False):
            response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)
        self.assertIn("暂未取得邮件数据", response.get_data(as_text=True))
        self.assertNotIn("剩余约 100", response.get_data(as_text=True))

    def test_traffic_counts_page_views_and_daily_unique_browser(self):
        self.client.get("/", headers={"User-Agent": "Mozilla/5.0"})
        self.client.get("/", headers={"User-Agent": "Mozilla/5.0"})
        with self.app.app_context():
            row = db.session.get(TrafficDay, admin_dashboard._macau_today())
            self.assertEqual(row.page_views, 2)
            self.assertEqual(row.unique_visitors, 1)

    def test_resend_summary_hides_address_and_verification_code(self):
        payload = {
            "data": [{
                "id": "mail-1",
                "to": ["2260025370@student.must.edu.mo"],
                "created_at": datetime_for_macau_today(),
                "subject": "482731 是你的 CampusMatch 验证码",
                "last_event": "delivered",
            }]
        }
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode("utf-8")
        with patch.multiple(
            admin_dashboard,
            MAIL_ENABLED=True,
            MAIL_PROVIDER="resend",
            RESEND_API_KEY="test-key",
        ), patch.object(admin_dashboard.urllib.request, "urlopen", return_value=response):
            result = admin_dashboard._resend_summary()

        serialized = json.dumps(result, ensure_ascii=False)
        self.assertEqual(result["used_today"], 1)
        self.assertEqual(result["recent"][0]["category"], "验证码")
        self.assertEqual(result["recent"][0]["domain"], "student.must.edu.mo")
        self.assertNotIn("2260025370", serialized)
        self.assertNotIn("482731", serialized)


if __name__ == "__main__":
    unittest.main()
