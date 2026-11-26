import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from flask import Flask

import admin_dashboard
from conduct import (
    REPORT_SUSPEND_DAYS,
    ReportError,
    counted_report_count,
    file_report,
    lift_suspension,
    review_report,
    write_is_frozen,
)
from models import Blocklist, Match, User, UserReport, db

ROOT = Path(__file__).resolve().parents[1]


class ReportSuspensionTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.target = User(email="target@um.edu.mo", school="澳门大学", email_verified=True, name="目标")
        db.session.add(self.target)
        self.reporters = []
        for i in range(5):
            person = User(email=f"b{i}@um.edu.mo", school="澳门大学", email_verified=True, name=f"同学{i}")
            db.session.add(person)
            self.reporters.append(person)
        partner = User(email="partner@um.edu.mo", school="澳门大学", email_verified=True, name="配对")
        db.session.add(partner)
        db.session.commit()
        self.partner = partner

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_three_reports_do_not_suspend(self):
        for person in self.reporters[:3]:
            file_report(person, self.target, "骚扰")
        self.assertEqual(counted_report_count(self.target.id), 3)
        self.assertFalse(self.target.is_suspended())

    def test_same_person_cannot_count_twice(self):
        file_report(self.reporters[0], self.target, "第一次")
        with self.assertRaises(ReportError) as caught:
            file_report(self.reporters[0], self.target, "再写一次")
        self.assertEqual(caught.exception.key, "err.report_dup")
        self.assertEqual(counted_report_count(self.target.id), 1)

    def test_blocks_do_not_suspend(self):
        for person in self.reporters:
            db.session.add(Blocklist(user_id=person.id, blocked_user_id=self.target.id))
        db.session.commit()
        self.assertFalse(self.target.is_suspended())

    def test_fourth_report_pauses_for_seven_days_and_drops_match(self):
        for person in self.reporters[:3]:
            file_report(person, self.target, "虚假资料")
        match = Match(user1_id=self.target.id, user2_id=self.partner.id, active=True)
        db.session.add(match)
        db.session.flush()
        started = datetime.utcnow()
        file_report(self.reporters[3], self.target, "继续骚扰")
        self.assertTrue(self.target.is_suspended())
        self.assertGreaterEqual(
            self.target.suspended_until,
            started + timedelta(days=REPORT_SUSPEND_DAYS) - timedelta(seconds=2),
        )
        db.session.refresh(match)
        self.assertFalse(match.active)

    def test_dismissed_report_does_not_count(self):
        for person in self.reporters[:4]:
            file_report(person, self.target, "待审")
        self.assertTrue(self.target.is_suspended())
        report = UserReport.query.filter_by(reporter_id=self.reporters[3].id).one()
        review_report(report, "dismissed", "说不清")
        self.assertEqual(counted_report_count(self.target.id), 3)
        self.assertTrue(self.target.is_suspended())
        lift_suspension(self.target)
        self.assertFalse(self.target.is_suspended())

    def test_extra_report_during_pause_does_not_extend_it(self):
        for person in self.reporters[:4]:
            file_report(person, self.target, "骚扰")
        until = self.target.suspended_until
        file_report(self.reporters[4], self.target, "又一条")
        self.assertEqual(self.target.suspended_until, until)

    def test_new_report_after_expiry_starts_another_week(self):
        for person in self.reporters[:4]:
            file_report(person, self.target, "骚扰")
        self.target.suspended_until = datetime.utcnow() - timedelta(days=1)
        file_report(self.reporters[4], self.target, "又来了")
        self.assertGreater(self.target.suspended_until, datetime.utcnow() + timedelta(days=6))

    def test_reads_logout_and_deletion_stay_open(self):
        self.assertFalse(write_is_frozen("GET", "/matches", True))
        self.assertFalse(write_is_frozen("POST", "/api/logout", True))
        self.assertFalse(write_is_frozen("DELETE", "/api/me", True))
        self.assertTrue(write_is_frozen("POST", "/api/reports", True))
        self.assertFalse(write_is_frozen("POST", "/api/reports", False))

    def test_pool_returns_after_the_week(self):
        with patch.object(User, "ready_to_match", lambda self: True):
            self.target.open_to_match = True
            self.target.suspended_until = datetime.utcnow() + timedelta(hours=1)
            self.assertFalse(self.target.in_match_pool())
            self.target.suspended_until = datetime.utcnow() - timedelta(seconds=1)
            self.assertTrue(self.target.in_match_pool())


class AdminReportQueueTests(unittest.TestCase):
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
        self.secret_patch = patch.object(admin_dashboard, "ADMIN_SECRET", "strong-admin-password")
        self.secret_patch.start()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.target = User(email="target@um.edu.mo", school="澳门大学", email_verified=True, name="目标")
        self.reporter = User(email="r@um.edu.mo", school="澳门大学", email_verified=True, name="举报人")
        db.session.add_all([self.target, self.reporter])
        db.session.commit()
        file_report(self.reporter, self.target, "对方要转账")
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        self.secret_patch.stop()
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self):
        self.client.get("/admin/login")
        with self.client.session_transaction() as saved:
            csrf = saved["admin_csrf"]
        self.client.post("/admin/login", data={"password": "strong-admin-password", "csrf": csrf})
        return csrf

    def test_queue_shows_the_report_to_the_admin(self):
        self.assertEqual(self.client.get("/admin/reports").status_code, 302)
        self.login()
        html = self.client.get("/admin/reports").get_data(as_text=True)
        self.assertIn("对方要转账", html)
        self.assertIn("target@um.edu.mo", html)
        self.assertIn("r@um.edu.mo", html)
        self.assertIn("待审", html)
