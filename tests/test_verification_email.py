import json
import unittest
from unittest.mock import patch

import email_service


class VerificationEmailTests(unittest.TestCase):
    def test_verification_email_is_short_and_has_plain_text_fallback(self):
        config = {"enabled": True, "provider": "resend"}
        with patch.object(email_service, "_dispatch_email", return_value=(True, "sent")) as dispatch:
            result = email_service.send_verification_email("student@example.edu", "482731", config)

        self.assertEqual(result, (True, "sent"))
        recipient, subject, html, passed_config, text = dispatch.call_args.args
        self.assertEqual(recipient, "student@example.edu")
        self.assertEqual(subject, "482731 是你的 CampusMatch 验证码")
        self.assertIs(passed_config, config)
        self.assertIn("482731", html)
        self.assertIn("482731", text)
        self.assertNotIn("<a ", html)
        self.assertNotIn("校园恋爱匹配", html)
        self.assertNotIn("深度问卷", text)

    def test_resend_payload_includes_plain_text(self):
        config = {
            "resend_api_key": "test-key",
            "mail_from": "CampusMatch <hello@campusmatch.com.cn>",
        }
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"id":"mail-id"}'
        with patch.object(email_service.urllib.request, "urlopen", return_value=response) as urlopen:
            ok, _ = email_service._send_resend(
                "student@example.edu", "subject", "<p>html</p>", config, "plain text"
            )

        self.assertTrue(ok)
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["text"], "plain text")
        self.assertEqual(payload["html"], "<p>html</p>")


if __name__ == "__main__":
    unittest.main()
