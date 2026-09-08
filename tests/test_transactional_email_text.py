import unittest
from types import SimpleNamespace
from unittest.mock import patch

import email_service


class TransactionalEmailTextTests(unittest.TestCase):
    def setUp(self):
        self.config = {"enabled": True, "public_url": "https://campusmatch.com.cn"}

    def _plain_text_from(self, function, *args, **kwargs):
        with patch.object(email_service, "_dispatch_email", return_value=(True, "sent")) as dispatch:
            function(*args, **kwargs)
        self.assertEqual(len(dispatch.call_args.args), 5)
        return dispatch.call_args.args[4]

    def test_no_match_email_has_plain_text(self):
        text = self._plain_text_from(
            email_service.send_match_result_email,
            "student@example.edu",
            [],
            self.config,
            reason="本轮人数不足",
        )
        self.assertIn("本轮人数不足", text)
        self.assertIn("https://campusmatch.com.cn/matches", text)

    def test_match_email_has_plain_text_contact_details(self):
        match = SimpleNamespace(
            name="同学甲",
            email="classmate@example.edu",
            wechat_id="wechat-id",
            bio="",
            is_express=lambda: False,
        )
        text = self._plain_text_from(
            email_service.send_match_result_email,
            "student@example.edu",
            [(match, 0.8)],
            self.config,
        )
        self.assertIn("同学甲", text)
        self.assertIn("classmate@example.edu", text)
        self.assertIn("wechat-id", text)

    def test_followup_email_has_plain_text(self):
        text = self._plain_text_from(
            email_service.send_icebreaker_followup_email,
            "student@example.edu",
            "同学乙",
            self.config,
        )
        self.assertIn("同学乙", text)
        self.assertIn("/matches", text)

    def test_incomplete_questionnaire_email_has_plain_text(self):
        text = self._plain_text_from(
            email_service.send_incomplete_nudge_email,
            "student@example.edu",
            self.config,
            name="小明",
        )
        self.assertIn("小明", text)
        self.assertIn("/questionnaire", text)


if __name__ == "__main__":
    unittest.main()
