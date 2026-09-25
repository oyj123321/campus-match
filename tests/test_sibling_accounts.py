import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MAIL_ENABLED"] = "false"

import unittest

from app import app, ensure_schema, find_sibling_account
from models import db, User


class SiblingAccountTests(unittest.TestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        ensure_schema()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_tourism_old_and_new_domains_are_independent(self):
        db.session.add(User(email="s250532@ift.edu.mo", school="澳门旅游大学", email_verified=True))
        db.session.commit()
        self.assertIsNone(find_sibling_account("s250532@utm.edu.mo"))
        self.assertIsNone(find_sibling_account("s250532@iftm.edu.mo"))

    def test_um_aliases_still_block_duplicate_local_part(self):
        db.session.add(User(email="yc12345@um.edu.mo", school="澳门大学", email_verified=True))
        db.session.commit()
        sibling = find_sibling_account("yc12345@connect.um.edu.mo")
        self.assertIsNotNone(sibling)
        self.assertEqual(sibling.email, "yc12345@um.edu.mo")
