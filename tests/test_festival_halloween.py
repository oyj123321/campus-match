import os
import unittest
from datetime import date
from unittest.mock import patch

import config


class FestivalHalloweenTests(unittest.TestCase):
    def test_env_override(self):
        with patch.dict(os.environ, {"FESTIVAL_HALLOWEEN": "on"}, clear=False):
            self.assertTrue(config.festival_halloween_active())
        with patch.dict(os.environ, {"FESTIVAL_HALLOWEEN": "off"}, clear=False):
            self.assertFalse(config.festival_halloween_active())

    def test_window_covers_halloween_week(self):
        with patch.dict(os.environ, {"FESTIVAL_HALLOWEEN": ""}, clear=False):
            self.assertTrue(config.FESTIVAL_HALLOWEEN_START <= date(2026, 10, 31) <= config.FESTIVAL_HALLOWEEN_END)
            self.assertFalse(date(2026, 11, 3) <= config.FESTIVAL_HALLOWEEN_END)
