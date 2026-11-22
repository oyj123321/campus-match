import os
import unittest
from datetime import date
from unittest.mock import patch

import config


class FestivalChristmasTests(unittest.TestCase):
    def test_env_override(self):
        with patch.dict(os.environ, {"FESTIVAL_CHRISTMAS": "on"}, clear=False):
            self.assertTrue(config.festival_christmas_active())
        with patch.dict(os.environ, {"FESTIVAL_CHRISTMAS": "off"}, clear=False):
            self.assertFalse(config.festival_christmas_active())

    def test_window_covers_christmas_through_new_year(self):
        with patch.dict(os.environ, {"FESTIVAL_CHRISTMAS": ""}, clear=False):
            self.assertTrue(config.FESTIVAL_CHRISTMAS_START <= date(2026, 12, 25) <= config.FESTIVAL_CHRISTMAS_END)
            self.assertTrue(config.FESTIVAL_CHRISTMAS_START <= date(2027, 1, 1) <= config.FESTIVAL_CHRISTMAS_END)
            self.assertFalse(date(2026, 12, 17) >= config.FESTIVAL_CHRISTMAS_START)
            self.assertFalse(date(2027, 1, 2) <= config.FESTIVAL_CHRISTMAS_END)
