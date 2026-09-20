import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from flask import Flask

import batch_job
from app import api_me, api_me_pause, api_me_exit_feedback, _purge_user_account
from models import db, User, Match, PoolEvent, ParticipationWeek, WeeklyParticipation
from operations_analytics import operations_data, record_completed_week, set_pool_participation, record_match_success


class OperationsAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY="test", SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.app.add_url_rule("/api/me", view_func=api_me, methods=["PUT"])
        self.app.add_url_rule("/api/me/pause", view_func=api_me_pause, methods=["POST"])
        self.app.add_url_rule("/api/me/exit-feedback", view_func=api_me_exit_feedback, methods=["POST"])
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.user = User(email="one@example.test", school="School A", gender="male", name="test",
                         email_verified=True, education_level="bachelor", looking_for="both",
                         profile_mode="privacy", bio="A" * 40, feature_vector_json="[1, 0]",
                         open_to_match=True, opt_in_week="2026-W38")
        self.other = User(email="two@example.test", school="School B", gender="female")
        db.session.add_all([self.user, self.other])
        db.session.commit()
        self.assertTrue(self.user.ready_to_match())
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = self.user.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def data(self, users=None):
        return operations_data(users if users is not None else User.query.all(), "2026-W38", datetime(2026, 9, 20))

    def test_funnel_denominators_and_empty_scope(self):
        result = self.data()
        self.assertEqual([s["count"] for s in result["stages"]], [2, 1, 1, 1, 1])
        self.assertEqual(result["stages"][1]["rate"], 50)
        empty = self.data([])
        self.assertTrue(all(s["rate"] is None for s in empty["stages"]))
        self.assertIsNone(empty["match_rate"])
        self.assertIsNone(empty["latest_week"])

    def test_pause_resume_and_repeat_requests(self):
        for _ in range(2):
            self.assertEqual(self.client.post("/api/me/pause", json={}).status_code, 200)
        self.assertEqual(PoolEvent.query.filter_by(kind="pause").count(), 1)
        self.assertIsNone(db.session.get(User, self.user.id).opt_in_week)
        for _ in range(2):
            self.assertEqual(self.client.put("/api/me", json={"open_to_match": True}).status_code, 200)
        self.assertEqual(PoolEvent.query.filter_by(kind="resume").count(), 1)

    def test_invalid_reason_does_not_pause_or_add_event(self):
        self.assertNotEqual(self.client.post("/api/me/pause", json={"reason_code": "invalid"}).status_code, 200)
        self.assertTrue(db.session.get(User, self.user.id).is_open_to_match())
        self.assertEqual(PoolEvent.query.count(), 0)

    def test_feedback_and_account_deletion_cleanup(self):
        self.client.post("/api/me/pause", json={"reason_code": "busy", "reason_note": "school work"})
        self.client.post("/api/me/exit-feedback", json={"reason_code": "need_break"})
        self.assertEqual(PoolEvent.query.filter_by(kind="feedback").count(), 2)
        record_completed_week([self.user.id], date(2026, 9, 14))
        _purge_user_account(self.user)
        db.session.commit()
        self.assertEqual(PoolEvent.query.count(), 0)
        self.assertEqual(WeeklyParticipation.query.count(), 0)
        self.assertEqual(ParticipationWeek.query.count(), 1)

    def test_transition_rolls_back_with_account_change(self):
        set_pool_participation(self.user, False)
        db.session.flush()
        db.session.rollback()
        self.assertTrue(self.user.is_open_to_match())
        self.assertEqual(PoolEvent.query.count(), 0)

    def test_same_week_rerun_merges_and_success_is_sticky(self):
        week = date(2026, 9, 14)
        record_completed_week([self.user.id], week)
        record_completed_week([self.user.id], week)
        self.assertEqual(WeeklyParticipation.query.count(), 1)
        self.assertFalse(WeeklyParticipation.query.first().matched)
        db.session.add(Match(user1_id=self.user.id, user2_id=self.other.id, created_at=datetime(2026, 9, 15)))
        db.session.commit()
        record_completed_week([self.user.id], week)
        self.assertTrue(WeeklyParticipation.query.first().matched)
        Match.query.delete()
        db.session.commit()
        record_completed_week([self.user.id], week)
        self.assertTrue(WeeklyParticipation.query.first().matched)
        self.assertEqual(ParticipationWeek.query.count(), 1)

    def test_streak_requires_consecutive_weeks_and_scopes_to_pool(self):
        for week in (date(2026, 9, 7), date(2026, 9, 14)):
            record_completed_week([self.user.id], week)
        self.assertEqual(self.data()["waiting_total"], 1)
        self.assertEqual(self.data()["distribution"], [{"weeks": 2, "count": 1}])
        self.assertEqual(self.data([self.other])["waiting_total"], 0)
        self.user.open_to_match = False
        db.session.commit()
        self.assertEqual(self.data()["waiting_total"], 0)
        self.user.open_to_match = True
        record_completed_week([self.user.id], date(2026, 9, 28))
        self.assertEqual(self.data()["waiting_total"], 0)
        self.assertEqual(self.data()["distribution"], [{"weeks": 1, "count": 1}])

    def test_later_reveal_ends_streak_and_counts_unique_people(self):
        for week in (date(2026, 9, 7), date(2026, 9, 14)):
            record_completed_week([self.user.id], week)
        for _ in range(2):
            db.session.add(Match(user1_id=self.user.id, user2_id=self.other.id, created_at=datetime(2026, 9, 19)))
        db.session.commit()
        result = self.data()
        self.assertEqual(result["waiting_total"], 0)
        self.assertEqual(result["participants"], 1)
        self.assertEqual(result["matched"], 1)
        self.assertEqual(result["match_rate"], 100)

    def test_empty_completed_week_breaks_streak(self):
        record_completed_week([self.user.id], date(2026, 9, 7))
        record_completed_week([], date(2026, 9, 14))
        self.assertEqual(self.data()["distribution"], [])
        self.assertEqual(self.data()["participants"], 0)

    def test_success_survives_partner_deletion(self):
        record_completed_week([self.user.id], date(2026, 9, 14))
        match = Match(user1_id=self.user.id, user2_id=self.other.id, created_at=datetime(2026, 9, 19))
        db.session.add(match)
        db.session.flush()
        record_match_success(match)
        db.session.commit()
        _purge_user_account(self.other)
        db.session.commit()
        self.assertEqual(self.data()["matched"], 1)
        self.assertEqual(self.data()["distribution"], [])

    def test_event_rolling_window_and_filter(self):
        now = datetime(2026, 9, 20)
        db.session.add_all([
            PoolEvent(user_id=self.user.id, kind="pause", created_at=now - timedelta(days=7)),
            PoolEvent(user_id=self.user.id, kind="resume", created_at=now - timedelta(days=7, seconds=1)),
            PoolEvent(user_id=self.other.id, kind="pause", created_at=now),
        ])
        db.session.commit()
        result = self.data([self.user])
        self.assertEqual(result["pauses"], 1)
        self.assertEqual(result["resumes"], 0)
        self.assertEqual(len(result["events"]), 2)

    def test_failed_batch_does_not_record_completion(self):
        with patch.object(batch_job, "SCHOOL_DOMAINS", {"School A": []}), \
                patch.object(batch_job, "ready_users", return_value=[self.user]), \
                patch.object(batch_job, "run_batch_school", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                batch_job.run_batch_all({}, require_opt_in=True)
        self.assertEqual(ParticipationWeek.query.count(), 0)

    def test_successful_batch_records_actual_participants(self):
        result = {"users": 1, "pairs": 0, "created": 0, "updated": 0, "matched_ids": set()}
        with patch.object(batch_job, "SCHOOL_DOMAINS", {"School A": []}), \
                patch.object(batch_job, "ready_users", return_value=[self.user]), \
                patch.object(batch_job, "run_batch_school", return_value=dict(result, school="School A")), \
                patch.object(batch_job, "run_batch_cross", return_value=result), \
                patch.object(batch_job, "MAIL_NO_MATCH_ENABLED", False):
            batch_job.run_batch_all({}, require_opt_in=True)
        self.assertEqual(ParticipationWeek.query.count(), 1)
        self.assertEqual(WeeklyParticipation.query.count(), 1)
        self.assertEqual(WeeklyParticipation.query.first().user_id, self.user.id)
