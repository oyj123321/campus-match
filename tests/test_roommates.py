import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask

from models import db, User, RoommateProfile as Profile, RoommateWish as Wish, RoommatePair as Pair
from roommates import bp, purge_roommates, current_season


class RoommateTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[1] / "templates"))
        self.app.config.update(TESTING=True, SECRET_KEY="roommate-tests", SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
        db.init_app(self.app)
        self.app.register_blueprint(bp)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.user = User(email="one@um.edu.mo", school="澳门大学", name="甲", email_verified=True, gender="female", education_level="master")
        self.other = User(email="two@um.edu.mo", school="澳门大学", name="乙", email_verified=True, gender="female", education_level="master")
        self.man = User(email="three@um.edu.mo", school="澳门大学", name="丙", email_verified=True, gender="male", education_level="master")
        self.undergrad = User(email="four@um.edu.mo", school="澳门大学", name="丁", email_verified=True, gender="female", education_level="bachelor")
        db.session.add_all([self.user, self.other, self.man, self.undergrad])
        db.session.commit()
        self.client = self.app.test_client()
        self.login(self.user)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, user):
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user.id
            session["roommate_csrf"] = "csrf"

    def fields(self, **overrides):
        data = dict(csrf="csrf", college="满珍纪念书院", degree="master", sleep="early", tidy="high",
                    social="quiet", smoke="no", guests="rare", note="早睡")
        data.update(overrides)
        return data

    def save(self, user, **overrides):
        self.login(user)
        return self.client.post("/roommates", data=self.fields(**overrides))

    def test_same_college_and_gender_only_and_masters_can_join(self):
        macau = timezone(timedelta(hours=8))
        self.assertEqual(current_season(datetime(2026, 11, 22, tzinfo=macau)), "2026-2027")
        self.assertEqual(current_season(datetime(2026, 7, 1, tzinfo=macau)), "2025-2026")
        self.assertEqual(self.save(self.user).status_code, 302)
        self.save(self.other)
        self.save(self.man)
        self.save(self.undergrad, degree="bachelor")
        self.save(self.other, college="绍邦书院")
        self.login(self.user)
        html = self.client.get("/roommates").get_data(as_text=True)
        self.assertNotIn("乙", html)
        self.assertNotIn("丙", html)
        self.assertNotIn("丁", html)
        self.save(self.other, college="满珍纪念书院")
        self.login(self.user)
        html = self.client.get("/roommates").get_data(as_text=True)
        self.assertIn("乙", html)
        self.assertNotIn("丙", html)
        self.assertNotIn("丁", html)
        mixed = self.client.get("/roommates?degree=all").get_data(as_text=True)
        self.assertIn("丁", mixed)
        self.assertNotIn("丙", mixed)

    def test_mutual_wish_confirms_one_pair_per_year(self):
        self.save(self.user)
        self.save(self.other)
        self.login(self.user)
        self.assertEqual(self.client.post(f"/roommates/wishes/{self.other.id}", data={"csrf": "csrf"}).status_code, 302)
        self.assertEqual(Pair.query.count(), 0)
        self.login(self.other)
        self.assertEqual(self.client.post(f"/roommates/wishes/{self.user.id}", data={"csrf": "csrf"}).status_code, 302)
        self.assertEqual(Pair.query.count(), 1)
        page = self.client.get("/roommates").get_data(as_text=True)
        self.assertIn(self.user.email, page)
        self.save(self.undergrad, degree="bachelor")
        self.login(self.other)
        self.assertEqual(self.client.post(f"/roommates/wishes/{self.undergrad.id}", data={"csrf": "csrf"}).status_code, 400)
        self.login(self.user)
        self.assertEqual(self.client.post("/roommates/pair/cancel", data={"csrf": "csrf"}).status_code, 302)
        self.assertEqual(Pair.query.count(), 0)
        self.assertEqual(Wish.query.count(), 0)

    def test_guest_is_sent_to_login_and_purge_clears_rows(self):
        self.save(self.user)
        with self.client.session_transaction() as session:
            session.clear()
        self.assertEqual(self.client.get("/roommates").status_code, 302)
        purge_roommates(self.user.id)
        db.session.commit()
        self.assertEqual(Profile.query.count(), 0)
