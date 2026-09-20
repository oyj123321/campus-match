import json
import unittest
from unittest.mock import patch
from flask import Flask
from models import db, User, MatchingRound
from matching_analytics import diagnose, aggregate, dashboard_reports
from batch_job import run_batch_all


def person(uid, gender, age=23):
    u = User(id=uid, email=f'{uid}@example.test', school='澳门大学',
             gender=gender, looking_for='both', age=age,
             education_level='bachelor', allow_cross_degree=False,
             profile_mode='privacy', bio='a' * 40)
    u.feature_vector = [1., 0.]
    return u


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        db.init_app(self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_independent_limits_and_combined(self):
        for reason in ('age', 'degree', 'school', 'combined'):
            a, b = person(1, 'male'), person(2, 'female', 40)
            if reason in ('age', 'combined'):
                a.preferred_age_min, a.preferred_age_max = 20, 25
            if reason in ('degree', 'combined'):
                b.education_level = 'master'
            if reason == 'school':
                b.school = '另一学校'
            report = aggregate([a, b], diagnose([a, b]), set(), {})
            self.assertEqual(report['reasons'], {reason: 2})
            self.assertEqual(sum(report['reasons'].values()), report['unmatched'])

    def test_competition_and_history(self):
        users = [person(1, 'male'), person(2, 'female'), person(3, 'male')]
        result = aggregate(users, diagnose(users), {1, 2}, {})
        self.assertEqual(result['reasons'], {'allocation': 1})
        self.assertEqual(result['matched'], 2)
        result = aggregate(users[:2], diagnose(users[:2], {(1, 2)}), set(), {})
        self.assertEqual(result['reasons'], {'combined': 2})

    def test_empty_and_single_pool(self):
        self.assertEqual(aggregate([], {}, set(), {})['rate'], 0)
        users = [person(1, 'male')]
        self.assertEqual(aggregate(users, diagnose(users), set(), {})['reasons'], {'structure': 1})

    def test_multiple_alternatives_are_not_double_counted(self):
        a, b, c = person(1, 'female'), person(2, 'male', 40), person(3, 'male')
        a.preferred_age_min, a.preferred_age_max = 20, 25
        c.education_level = 'master'
        users = [a, b, c]
        report = aggregate(users, diagnose(users), {2, 3}, {})
        self.assertEqual(report['reasons'], {'multiple_options': 1})

    def test_actual_batch_creates_report_and_counts_users_once(self):
        from config import SCHOOL_DOMAINS
        users = [person(1, 'male'), person(2, 'female')]
        for user in users:
            user.school = next(iter(SCHOOL_DOMAINS))
            user.email_verified = True
            user.open_to_match = True
        db.session.add_all(users)
        db.session.commit()
        with patch('batch_job.ready_users', side_effect=lambda school=None, **kw:
                   [u for u in users if school is None or u.school == school]), patch(
            'batch_job.send_match_result_email', return_value=(True, 'test')), patch(
            'batch_job.get_compatibility_insight', return_value={}), patch(
            'batch_job.MAIL_NO_MATCH_ENABLED', False):
            run_batch_all({}, False)
        report = json.loads(MatchingRound.query.one().report_json)
        self.assertEqual(report['participants'], 2)
        self.assertEqual(report['matched'], 2)
        self.assertEqual(report['unmatched'], 0)
        self.assertEqual(report['reasons'], {})

    def test_success_persists_aggregate_only(self):
        users = [person(1, 'male'), person(2, 'female')]
        snapshot = (users, diagnose(users), {'participants': 2, 'quota_excluded': 0})
        with patch('matching_analytics.capture', return_value=snapshot), patch(
            'batch_job._run_batch_all', return_value=[{'matched_ids': {1, 2}}, {'no_match_notified': 0}]):
            run_batch_all({}, False)
        row = MatchingRound.query.one()
        self.assertEqual(row.status, 'completed')
        self.assertEqual(json.loads(row.report_json)['matched'], 2)
        self.assertNotIn('example.test', row.report_json)
        self.assertNotIn('matched_ids', row.report_json)
        self.assertEqual(dashboard_reports()['latest']['rate'], 100)

    def test_failure_is_not_reported_as_zero_matches(self):
        with patch('matching_analytics.capture', return_value=([], {}, {'participants': 0})), patch(
            'batch_job._run_batch_all', side_effect=RuntimeError('test')):
            with self.assertRaises(RuntimeError):
                run_batch_all({}, False)
        self.assertEqual(MatchingRound.query.one().status, 'failed')
        self.assertIsNone(dashboard_reports()['latest'])

    def test_capture_failure_does_not_stop_matching(self):
        with patch('matching_analytics.capture', side_effect=RuntimeError('test')), patch(
            'batch_job._run_batch_all', return_value=[]) as run:
            self.assertEqual(run_batch_all({}, False), [])
            run.assert_called_once()
