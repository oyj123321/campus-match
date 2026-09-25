import os
import unittest
from datetime import date
from unittest.mock import patch

import config


class FestivalAutumnTests(unittest.TestCase):
    def test_env_override(self):
        with patch.dict(os.environ, {"FESTIVAL_AUTUMN": "on"}, clear=False):
            self.assertTrue(config.festival_autumn_active())
        with patch.dict(os.environ, {"FESTIVAL_AUTUMN": "off"}, clear=False):
            self.assertFalse(config.festival_autumn_active())

    def test_window_uses_macau_calendar(self):
        with patch.dict(os.environ, {"FESTIVAL_AUTUMN": ""}, clear=False):
            self.assertTrue(config.FESTIVAL_AUTUMN_START <= date(2026, 9, 25) <= config.FESTIVAL_AUTUMN_END)
            self.assertFalse(date(2026, 10, 20) <= config.FESTIVAL_AUTUMN_END and date(2026, 10, 20) >= config.FESTIVAL_AUTUMN_START)
