import unittest
from datetime import datetime, timedelta

from pool_rhythm import grant_debut_week, is_dormant, current_week_key


class Fake:
    def __init__(self, **kw):
        self.debut_opted_at = None
        self.opt_in_week = None
        self.dormant_notice_at = None
        self.open = True
        self.ready = True
        self.last_login_at = datetime.utcnow()
        self.created_at = datetime.utcnow() - timedelta(days=40)
        self.__dict__.update(kw)

    def is_open_to_match(self):
        return self.open

    def ready_to_match(self):
        return self.ready

    def in_match_pool(self):
        return self.open and self.ready


class PoolRhythmTests(unittest.TestCase):
    def test_first_week_opts_in_once(self):
        user = Fake()
        now = datetime(2026, 10, 16, 12, 0, 0)
        self.assertTrue(grant_debut_week(user, now))
        self.assertEqual(user.opt_in_week, current_week_key(now))
        self.assertIsNotNone(user.debut_opted_at)
        user.opt_in_week = None
        self.assertFalse(grant_debut_week(user, now))
        self.assertIsNone(user.opt_in_week)

    def test_closed_or_unready_skips(self):
        closed = Fake(open=False)
        unready = Fake(ready=False)
        self.assertFalse(grant_debut_week(closed))
        self.assertFalse(grant_debut_week(unready))

    def test_three_quiet_weeks_is_dormant(self):
        now = datetime(2026, 10, 16, 12, 0, 0)
        quiet = Fake(last_login_at=now - timedelta(days=22), opt_in_week="2026-W30")
        self.assertTrue(is_dormant(quiet, now_utc=now, now_local=now))

    def test_recent_login_or_opt_in_is_not_dormant(self):
        now = datetime(2026, 10, 16, 12, 0, 0)
        recent = Fake(last_login_at=now - timedelta(days=2), opt_in_week="2026-W30")
        opted = Fake(last_login_at=now - timedelta(days=22), opt_in_week=current_week_key(now))
        paused = Fake(open=False, last_login_at=now - timedelta(days=22))
        told = Fake(last_login_at=now - timedelta(days=22), dormant_notice_at=now)
        self.assertFalse(is_dormant(recent, now_utc=now, now_local=now))
        self.assertFalse(is_dormant(opted, now_utc=now, now_local=now))
        self.assertFalse(is_dormant(paused, now_utc=now, now_local=now))
        self.assertFalse(is_dormant(told, now_utc=now, now_local=now))


if __name__ == "__main__":
    unittest.main()
