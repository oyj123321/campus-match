import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

from flask import Flask
import mail_operations as ops
import email_service
from models import db, User


class MailOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'mail.db'
        self.patcher = patch.object(ops, 'LEDGER_PATH', self.path)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.sender = Mock(return_value=(True, 'accepted'))
        self.config = dict(enabled=True, provider='resend', public_url='https://example.edu')

    def send(self, kind='verification'):
        return ops.dispatch('user@example.edu', 'subject', 'body', self.config, 'text', self.sender, kind)

    def test_concurrent_requests_cannot_exceed_budget(self):
        with patch.object(ops, 'MAIL_DAILY_LIMIT', 10):
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: self.send()[0], range(30)))
            self.assertEqual(sum(results), 10)
            self.assertEqual(self.sender.call_count, 10)
            self.assertEqual(ops.summary()['remaining'], 0)

    def test_reserved_capacity_only_accepts_verification(self):
        with patch.object(ops, 'MAIL_DAILY_LIMIT', 20):
            for _ in range(17):
                self.assertTrue(self.send()[0])
            self.assertEqual(self.send('optional'), (False, 'mail_quota_exhausted'))
            self.assertEqual(self.send('match'), (False, 'mail_queued'))
            self.assertTrue(self.send()[0])
            self.assertEqual(ops.summary()['pending'], 1)

    def test_failure_keeps_reservation_and_does_not_store_body(self):
        self.sender.return_value = False, 'sensitive provider error'
        self.assertFalse(self.send()[0])
        summary = ops.summary()
        self.assertEqual(summary['failed'], 1)
        self.assertEqual(summary['used'], 1)
        data = self.path.read_bytes()
        self.assertNotIn(b'user@example.edu', data)
        self.assertNotIn(b'sensitive provider error', data)

    def test_successful_optional_mail_is_not_repeated_on_pair_retry(self):
        self.assertTrue(self.send('optional')[0])
        self.assertTrue(self.send('optional')[0])
        self.assertEqual(self.sender.call_count, 1)
        self.assertEqual(ops.summary()['used'], 1)

    def test_new_week_notification_is_not_deduplicated(self):
        from datetime import datetime, timezone
        sunday = datetime(2026, 9, 6, 12, tzinfo=timezone.utc).timestamp()
        with patch.object(ops.time, 'time', return_value=sunday):
            self.assertTrue(self.send('match')[0])
        with patch.object(ops.time, 'time', return_value=sunday + 86400):
            self.assertTrue(self.send('match')[0])
        self.assertEqual(self.sender.call_count, 2)

    def test_failed_queue_does_not_claim_to_be_waiting(self):
        with patch.object(ops, 'MAIL_DAILY_LIMIT', 0):
            self.send('match')
        with ops.database() as conn:
            conn.execute("UPDATE pending SET state='failed'")
        self.assertEqual(self.send('match'), (False, 'mail_queue_failed'))
        self.sender.assert_not_called()

    def test_production_disabled_mail_does_not_expose_debug_code(self):
        import app as website
        user = SimpleNamespace(verification_token='SECRET-CODE')
        with website.app.test_request_context(), patch.object(website, 'MAIL_ENABLED', False), patch.object(website, 'FLASK_DEBUG', False):
            response = website._code_json(user, 'user@example.edu', mail_ok=True)
        self.assertIsNone(response.get_json()['dev_token'])

    def test_quota_error_uses_requested_language(self):
        import app as website
        user = SimpleNamespace(verification_token='SECRET-CODE')
        for lang in ('zh', 'tw', 'en', 'pt'):
            with self.subTest(lang=lang), website.app.test_request_context(headers={'X-CM-Lang': lang}), patch.object(website, 'MAIL_ENABLED', True):
                response, status = website._code_json(user, 'user@example.edu', info='mail_quota_exhausted')
                self.assertEqual(status, 503)
                self.assertEqual(response.get_json()['error'], website.t_api('err.mail_quota'))

    def test_window_recovers_and_verification_is_never_queued(self):
        with patch.object(ops, 'MAIL_DAILY_LIMIT', 1):
            self.assertTrue(self.send()[0])
            self.assertFalse(self.send()[0])
            self.assertEqual(ops.summary()['pending'], 0)
            with ops.database() as conn:
                conn.execute('UPDATE sends SET created=0')
            self.assertTrue(self.send()[0])

    def test_ledger_failure_does_not_send(self):
        with patch.object(ops, 'LEDGER_PATH', self.path / 'invalid' / 'db'):
            self.path.touch()
            self.assertEqual(self.send(), (False, 'mail_ledger_unavailable'))
        self.sender.assert_not_called()

    def test_queue_drains_once_without_original_contact_details(self):
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        db.init_app(app)
        with app.app_context():
            db.create_all()
            db.session.add(User(email='user@example.edu', school='test', email_verified=True))
            db.session.commit()
            with patch.object(ops, 'MAIL_DAILY_LIMIT', 0):
                self.assertEqual(self.send('match'), (False, 'mail_queued'))
                self.assertEqual(self.send('match'), (False, 'mail_queued'))
            ops.drain(self.config, self.sender)
            ops.drain(self.config, self.sender)
            self.assertEqual(self.sender.call_count, 1)
            self.assertIn('/matches', self.sender.call_args.args[4])
            self.assertNotEqual(self.sender.call_args.args[2], 'body')
            self.assertEqual(ops.summary()['pending'], 0)
            self.assertEqual(self.send('match'), (True, 'sent'))
            self.assertEqual(self.sender.call_count, 1)
            db.session.remove()
            db.drop_all()

    def test_live_verification_failure_never_exposes_token(self):
        import app as website
        user = SimpleNamespace(verification_token='SECRET-CODE')
        with website.app.test_request_context(), patch.object(website, 'MAIL_ENABLED', True):
            response, status = website._code_json(user, 'user@example.edu', info='mail_quota_exhausted')
        self.assertEqual(status, 503)
        self.assertFalse(response.get_json()['ok'])
        self.assertNotIn('SECRET-CODE', response.get_data(as_text=True))

    def test_aliyun_dispatch_uses_ledger_and_smtp_transport(self):
        config = dict(self.config, provider='aliyun')
        with patch.object(ops, 'dispatch', return_value=(True, 'sent')) as protected:
            result = email_service._dispatch_email(
                'user@example.edu', 'subject', '<p>body</p>', config, 'body', kind='verification')
        self.assertEqual(result, (True, 'sent'))
        self.assertIs(protected.call_args.args[5], email_service._send_smtp)
        self.assertEqual(protected.call_args.args[6], 'verification')

    def test_smtp_465_uses_implicit_ssl_and_clean_envelope_sender(self):
        config = dict(
            server='smtpdm.aliyun.com', port=465,
            username='no-reply@notify.campusmatch.com.cn', password='secret',
            mail_from='CampusMatch <no-reply@notify.campusmatch.com.cn>',
        )
        with patch.object(email_service.smtplib, 'SMTP_SSL') as smtp_ssl:
            server = smtp_ssl.return_value
            server.sendmail.return_value = {}
            result = email_service._send_smtp('student@example.edu', 'subject', '<p>body</p>', config, 'body')
        self.assertEqual(result, (True, 'sent'))
        smtp_ssl.assert_called_once_with('smtpdm.aliyun.com', 465, timeout=15, context=ANY)
        server.login.assert_called_once_with('no-reply@notify.campusmatch.com.cn', 'secret')
        self.assertEqual(server.sendmail.call_args.args[0], 'no-reply@notify.campusmatch.com.cn')

    def test_smtp_recipient_refusal_is_failure(self):
        config = dict(server='smtpdm.aliyun.com', port=465, username='sender@example.edu',
                      password='secret', mail_from='sender@example.edu')
        with patch.object(email_service.smtplib, 'SMTP_SSL') as smtp_ssl:
            smtp_ssl.return_value.sendmail.return_value = {'student@example.edu': (550, b'rejected')}
            result = email_service._send_smtp('student@example.edu', 'subject', '<p>body</p>', config)
        self.assertEqual(result, (False, 'recipient refused'))


if __name__ == '__main__':
    unittest.main()
