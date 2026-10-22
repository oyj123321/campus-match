import unittest
from datetime import datetime, timedelta

from pool_rhythm import (
    grant_debut_week, grant_transition_week, is_dormant, current_week_key,
    set_next_availability, apply_ahead_opt_in, next_week_key,
)


class Fake:
    def __init__(self, **kw):
        self.debut_opted_at = None
        self.opt_in_week = None
        self.dormant_notice_at = None
        self.weekly_rule_notice_at = None
        self.rhythm_grace_week = None
        self.next_availability = None
        self.next_availability_week = None
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
        quiet = Fake(
            last_login_at=now - timedelta(days=22),
            opt_in_week="2026-W30",
            weekly_rule_notice_at=now - timedelta(days=22),
        )
        self.assertTrue(is_dormant(quiet, now_utc=now, now_local=now))

    def test_recent_login_or_opt_in_is_not_dormant(self):
        now = datetime(2026, 10, 16, 12, 0, 0)
        recent = Fake(
            last_login_at=now - timedelta(days=2),
            opt_in_week="2026-W30",
            weekly_rule_notice_at=now - timedelta(days=30),
        )
        opted = Fake(
            last_login_at=now - timedelta(days=22),
            opt_in_week=current_week_key(now),
            weekly_rule_notice_at=now - timedelta(days=30),
        )
        paused = Fake(
            open=False,
            last_login_at=now - timedelta(days=22),
            weekly_rule_notice_at=now - timedelta(days=30),
        )
        told = Fake(
            last_login_at=now - timedelta(days=22),
            dormant_notice_at=now,
            weekly_rule_notice_at=now - timedelta(days=30),
        )
        not_told = Fake(last_login_at=now - timedelta(days=22), opt_in_week="2026-W30")
        just_told = Fake(
            last_login_at=now - timedelta(days=22),
            opt_in_week="2026-W30",
            weekly_rule_notice_at=now - timedelta(days=2),
        )
        self.assertFalse(is_dormant(recent, now_utc=now, now_local=now))
        self.assertFalse(is_dormant(opted, now_utc=now, now_local=now))
        self.assertFalse(is_dormant(paused, now_utc=now, now_local=now))
        self.assertFalse(is_dormant(told, now_utc=now, now_local=now))
        self.assertFalse(is_dormant(not_told, now_utc=now, now_local=now))
        self.assertFalse(is_dormant(just_told, now_utc=now, now_local=now))

    def test_transition_week_opts_waiters_once(self):
        now = datetime(2026, 10, 18, 12, 0, 0)
        week = current_week_key(now)
        waiter = Fake()
        self.assertTrue(grant_transition_week(waiter, week=week, has_active_match=False))
        self.assertEqual(waiter.opt_in_week, week)
        self.assertEqual(waiter.rhythm_grace_week, week)
        waiter.opt_in_week = None
        self.assertFalse(grant_transition_week(waiter, week=week, has_active_match=False))
        self.assertIsNone(waiter.opt_in_week)

    def test_transition_week_skips_active_match(self):
        now = datetime(2026, 10, 18, 12, 0, 0)
        week = current_week_key(now)
        paired = Fake()
        self.assertFalse(grant_transition_week(paired, week=week, has_active_match=True))
        self.assertIsNone(paired.opt_in_week)
        self.assertEqual(paired.rhythm_grace_week, week)

    def test_yes_books_the_following_week_once(self):
        now = datetime(2026, 10, 22, 12, 0, 0)
        user = Fake()
        set_next_availability(user, "yes", now)
        self.assertEqual(user.next_availability_week, next_week_key(now))
        self.assertFalse(apply_ahead_opt_in(user, now))
        self.assertIsNone(user.opt_in_week)
        later = now + timedelta(days=7)
        self.assertTrue(apply_ahead_opt_in(user, later))
        self.assertEqual(user.opt_in_week, current_week_key(later))
        user.opt_in_week = None
        self.assertFalse(apply_ahead_opt_in(user, later))
        self.assertIsNone(user.opt_in_week)

    def test_no_and_later_do_not_book_ahead(self):
        now = datetime(2026, 10, 22, 12, 0, 0)
        later = now + timedelta(days=7)
        for choice in ("no", "later"):
            user = Fake()
            set_next_availability(user, choice, now)
            self.assertFalse(apply_ahead_opt_in(user, later))
            self.assertIsNone(user.opt_in_week)

    def test_yes_can_be_changed_before_the_week(self):
        now = datetime(2026, 10, 22, 12, 0, 0)
        user = Fake()
        set_next_availability(user, "yes", now)
        set_next_availability(user, "no", now)
        self.assertFalse(apply_ahead_opt_in(user, now + timedelta(days=7)))
        self.assertIsNone(user.opt_in_week)


if __name__ == "__main__":
    unittest.main()
