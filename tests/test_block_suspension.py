import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from flask import Flask

from conduct import (
    BLOCK_SUSPEND_DAYS,
    distinct_block_count,
    suspend_if_widely_blocked,
    write_is_frozen,
)
from models import Blocklist, Match, User, db


class BlockSuspensionTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.target = User(email="target@um.edu.mo", school="澳门大学", email_verified=True, name="目标")
        db.session.add(self.target)
        self.blockers = []
        for i in range(5):
            person = User(email=f"b{i}@um.edu.mo", school="澳门大学", email_verified=True, name=f"同学{i}")
            db.session.add(person)
            self.blockers.append(person)
        partner = User(email="partner@um.edu.mo", school="澳门大学", email_verified=True, name="配对")
        db.session.add(partner)
        db.session.commit()
        self.partner = partner

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def block(self, person):
        db.session.add(Blocklist(user_id=person.id, blocked_user_id=self.target.id))
        db.session.flush()

    def test_three_blocks_do_not_suspend(self):
        for person in self.blockers[:3]:
            self.block(person)
            self.assertFalse(suspend_if_widely_blocked(self.target))
        self.assertEqual(distinct_block_count(self.target.id), 3)
        self.assertFalse(self.target.is_suspended())
        self.assertIsNone(self.target.suspended_until)

    def test_fourth_distinct_block_pauses_for_seven_days_and_drops_match(self):
        for person in self.blockers[:3]:
            self.block(person)
        match = Match(user1_id=self.target.id, user2_id=self.partner.id, active=True)
        db.session.add(match)
        db.session.flush()
        started = datetime.utcnow()
        self.block(self.blockers[3])
        self.assertTrue(suspend_if_widely_blocked(self.target))
        self.assertTrue(self.target.is_suspended())
        self.assertGreaterEqual(self.target.suspended_until, started + timedelta(days=BLOCK_SUSPEND_DAYS) - timedelta(seconds=2))
        self.assertLessEqual(self.target.suspended_until, started + timedelta(days=BLOCK_SUSPEND_DAYS) + timedelta(seconds=2))
        with patch.object(User, "ready_to_match", lambda self: True):
            self.target.open_to_match = True
            self.assertFalse(self.target.in_match_pool())
            self.target.suspended_until = datetime.utcnow() - timedelta(seconds=1)
            self.assertTrue(self.target.in_match_pool())
            self.target.suspended_until = datetime.utcnow() + timedelta(days=BLOCK_SUSPEND_DAYS)
        db.session.refresh(match)
        self.assertFalse(match.active)

    def test_extra_block_during_pause_does_not_extend_it(self):
        for person in self.blockers[:4]:
            self.block(person)
        suspend_if_widely_blocked(self.target)
        until = self.target.suspended_until
        self.block(self.blockers[4])
        self.assertFalse(suspend_if_widely_blocked(self.target))
        self.assertEqual(self.target.suspended_until, until)

    def test_new_block_after_expiry_starts_another_week(self):
        for person in self.blockers[:4]:
            self.block(person)
        self.target.suspended_until = datetime.utcnow() - timedelta(days=1)
        self.block(self.blockers[4])
        self.assertTrue(suspend_if_widely_blocked(self.target))
        self.assertGreater(self.target.suspended_until, datetime.utcnow() + timedelta(days=6))

    def test_reads_logout_and_deletion_stay_open(self):
        self.assertFalse(write_is_frozen("GET", "/matches", True))
        self.assertFalse(write_is_frozen("POST", "/api/logout", True))
        self.assertFalse(write_is_frozen("DELETE", "/api/me", True))
        self.assertTrue(write_is_frozen("POST", "/api/blocklist", True))
        self.assertTrue(write_is_frozen("POST", "/community", True))
        self.assertTrue(write_is_frozen("POST", "/roommates", True))
        self.assertFalse(write_is_frozen("POST", "/api/blocklist", False))
