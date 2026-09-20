import unittest
from unittest.mock import patch

from flask import Flask
from models import AccountDeletion, User, db
from app import api_me


class AccountDeletionTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY="test", SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.app.add_url_rule("/api/me", view_func=api_me, methods=["DELETE"])
        with self.app.app_context():
            db.create_all()
            user = User(email="student@example.test", school="test", email_verified=True)
            db.session.add(user)
            db.session.commit()
            self.uid = user.id
        self.client = self.app.test_client()
        with self.client.session_transaction() as saved:
            saved["user_id"] = self.uid

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_success_counts_once_and_removes_account(self):
        response = self.client.delete("/api/me", json={"confirm_email": "student@example.test"})
        self.assertEqual(response.status_code, 200)
        self.client.delete("/api/me", json={"confirm_email": "student@example.test"})
        with self.app.app_context():
            self.assertEqual(User.query.count(), 0)
            self.assertEqual(AccountDeletion.query.count(), 1)
            self.assertEqual(set(AccountDeletion.__table__.columns.keys()), {"id", "created_at"})

    def test_wrong_confirmation_does_not_count(self):
        response = self.client.delete("/api/me", json={"confirm_email": "wrong@example.test"})
        self.assertNotEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(User.query.count(), 1)
            self.assertEqual(AccountDeletion.query.count(), 0)

    def test_failed_deletion_rolls_back_receipt(self):
        with patch("app._purge_user_account", side_effect=RuntimeError("test failure")):
            with self.assertRaises(RuntimeError):
                self.client.delete("/api/me", json={"confirm_email": "student@example.test"})
        with self.app.app_context():
            self.assertEqual(User.query.count(), 1)
            self.assertEqual(AccountDeletion.query.count(), 0)
