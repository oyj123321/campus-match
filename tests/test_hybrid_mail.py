import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import hybrid_mail as hybrid
import mail_operations as ops


class HybridTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        for target, value in [(ops, ('LEDGER_PATH', Path(temporary.name) / 'mail.db')),
                              (hybrid.settings, ('RESEND_DAILY_LIMIT', 2)),
                              (hybrid.settings, ('ALIYUN_DAILY_LIMIT', 3)),
                              (hybrid.settings, ('RESEND_FROM', 'hello@example.com')),
                              (hybrid.settings, ('ALIYUN_FROM', 'no-reply@notify.example.com'))]:
            p = patch.object(target, *value)
            p.start()
            self.addCleanup(p.stop)
        self.config = dict(resend_api_key='test', username='smtp', password='test')

    def test_budget_switch_and_exhaustion(self):
        self.assertEqual([hybrid.reserve_provider()[0] for _ in range(6)],
                         ['resend', 'resend', 'aliyun', 'aliyun', 'aliyun', None])

    def test_concurrent_budget(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: hybrid.reserve_provider()[0], range(20)))
        self.assertEqual(results.count('resend'), 2)
        self.assertEqual(results.count('aliyun'), 3)

    def test_rolling_recovery(self):
        with patch.object(hybrid.time, 'time', return_value=100000):
            self.assertEqual(hybrid.reserve_provider()[0], 'resend')
            self.assertEqual(hybrid.reserve_provider()[0], 'resend')
        with patch.object(hybrid.time, 'time', return_value=100000 + ops.WINDOW + 1):
            self.assertEqual(hybrid.reserve_provider()[0], 'resend')

    def test_no_retry_on_failure(self):
        with patch('email_service._send_resend', return_value=(False, 'timeout')) as resend, \
             patch('email_service._send_smtp') as smtp:
            self.assertEqual(hybrid.send('a@example.com', 'subject', 'body', self.config), (False, 'timeout'))
            smtp.assert_not_called()
            self.assertEqual(resend.call_args.args[3]['mail_from'], 'hello@example.com')

    def test_smtp_sender_after_budget(self):
        hybrid.reserve_provider()
        hybrid.reserve_provider()
        with patch('email_service._send_smtp', return_value=(True, 'sent')) as smtp:
            self.assertTrue(hybrid.send('a@example.com', 'subject', 'body', self.config)[0])
            self.assertEqual(smtp.call_args.args[3]['mail_from'], 'no-reply@notify.example.com')

    def test_missing_credentials(self):
        with patch('email_service._send_resend') as resend:
            self.assertFalse(hybrid.send('a@example.com', 'subject', 'body', {})[0])
            resend.assert_not_called()

    def test_usage(self):
        hybrid.reserve_provider()
        self.assertEqual(hybrid.usage()[0]['used'], 1)

    def test_all_kinds_route_through_hybrid(self):
        from email_service import _dispatch_email
        with patch.object(hybrid, 'send', return_value=(True, 'sent')) as sender:
            for kind in ('verification', 'match', 'optional'):
                result = _dispatch_email('a@example.com', kind, kind, {'provider': 'hybrid'}, kind=kind)
                self.assertTrue(result[0])
            self.assertEqual(sender.call_count, 3)
