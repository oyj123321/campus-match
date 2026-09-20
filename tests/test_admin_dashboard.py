import unittest
import json
from pathlib import Path
from unittest.mock import patch

from flask import Flask

import admin_dashboard
from models import AccountDeletion, TrafficDay, User, db
from datetime import datetime, timedelta


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

    def test_gender_counts_include_unknown_and_empty(self):
        result = admin_dashboard._gender_summary("all", [
            User(gender="male"), User(gender="female"), User(gender=None), User(gender="other")])
        self.assertEqual((result["male"], result["female"], result["unknown"]), (1, 1, 2))
        self.assertEqual(result["male_pct"], 25)
        self.assertEqual(admin_dashboard._gender_summary("empty", [])["female_pct"], 0)

    def test_retention_counts_time_boundaries_and_resumed_feedback(self):
        start = datetime(2026, 9, 18, 16)
        with self.app.app_context():
            user = User.query.first()
            user.open_to_match = True
            user.exit_reason_code = "busy"
            user.exit_reason_at = start
            paused = User(email="paused@example.test", school="test", open_to_match=False)
            db.session.add(paused)
            db.session.add_all([AccountDeletion(created_at=start),
                                AccountDeletion(created_at=start - timedelta(seconds=1))])
            db.session.commit()
            result = admin_dashboard._retention_data(User.query.all(), start, start - timedelta(days=6))
            self.assertEqual(result["paused"], 1)
            self.assertEqual(result["feedback_total"], 1)
            self.assertFalse(result["recent"][0]["paused"])
            self.assertEqual(result["deleted_today"], 1)
            self.assertEqual(result["deleted_week"], 2)
            self.assertEqual(result["deleted_total"], 2)

    def test_feedback_is_escaped_and_limited(self):
        with self.app.app_context():
            for number in range(55):
                db.session.add(User(email=f"{number}@example.test", school="test",
                                    exit_reason_code="other", exit_reason_note="<script>alert(1)</script>",
                                    exit_reason_at=datetime(2026, 9, 1) + timedelta(minutes=number)))
            db.session.commit()
            result = admin_dashboard._retention_data(User.query.all(), datetime.utcnow(), datetime.utcnow())
            self.assertEqual(result["feedback_total"], 55)
            self.assertEqual(len(result["recent"]), 50)
        self._login()
        with patch.object(admin_dashboard, "MAIL_ENABLED", False):
            html = self.client.get("/admin").get_data(as_text=True)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_empty_database_dashboard(self):
        with self.app.app_context():
            User.query.delete()
            db.session.commit()
        self._login()
        with patch.object(admin_dashboard, "MAIL_ENABLED", False):
            response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)
        self.assertIn("暂无退出反馈", response.get_data(as_text=True))

    def test_matching_report_renders_for_admin_only(self):
        from models import MatchingRound
        with self.app.app_context():
            db.session.add(MatchingRound(status='completed', report_json=json.dumps({
                'participants': 3, 'matched': 2, 'unmatched': 1, 'rate': 66.7,
                'quota_excluded': 0, 'age_missing': 0, 'no_candidates': 1,
                'reasons': {'age': 1}, 'schools': []})))
            db.session.commit()
        self.assertEqual(self.client.get('/admin').status_code, 302)
        self._login()
        with patch.object(admin_dashboard, '_resend_summary', return_value={}):
            response = self.client.get('/admin')
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn('66.7%', text)
        self.assertIn('仅放宽年龄即可出现候选', text)
        self.assertNotIn('student@um.edu.mo', text)

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
        self.assertIn("当前 SMTP 通道没有接入远端投递详情", response.get_data(as_text=True))
        self.assertNotIn("剩余约 100", response.get_data(as_text=True))

    def test_aliyun_dashboard_uses_local_budget_and_points_to_directmail(self):
        self._login()
        budget = {
            "used": 12, "remaining": 1988, "limit": 2000, "pending": 0,
            "failed": 0, "stalled": 0, "warning": False, "protected": False,
            "recent": [],
        }
        with patch.multiple(admin_dashboard, MAIL_ENABLED=True, MAIL_PROVIDER="aliyun"), \
                patch("mail_operations.summary", return_value=budget):
            response = self.client.get("/admin")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("本地剩余 1988 / 2000", html)
        self.assertIn("已启用 · aliyun", html)
        self.assertIn("阿里云的送达、退信与无效地址详情", html)
        self.assertNotIn("Resend 未启用", html)

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
