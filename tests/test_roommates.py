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

    def test_undergraduates_use_colleges_and_graduates_use_the_dorm(self):
        macau = timezone(timedelta(hours=8))
        self.assertEqual(current_season(datetime(2026, 11, 22, tzinfo=macau)), "2026-2027")
        self.assertEqual(current_season(datetime(2026, 7, 1, tzinfo=macau)), "2025-2026")
        self.assertEqual(self.save(self.user).status_code, 302)
        self.assertEqual(Profile.query.filter_by(user_id=self.user.id).one().college, "研究生宿舍")
        self.save(self.other, college="绍邦书院")
        self.save(self.man)
        self.save(self.undergrad, degree="bachelor", college="满珍纪念书院")
        peer = User(email="five@um.edu.mo", school="澳门大学", name="戊", email_verified=True,
                    gender="female", education_level="bachelor")
        phd = User(email="six@um.edu.mo", school="澳门大学", name="博士生", email_verified=True,
                   gender="female", education_level="doctorate")
        db.session.add_all([peer, phd])
        db.session.commit()
        self.save(peer, degree="bachelor", college="绍邦书院")
        self.save(phd, degree="doctorate", college="满珍纪念书院")
        self.login(self.undergrad)
        html = self.client.get("/roommates").get_data(as_text=True)
        self.assertNotIn("戊", html)
        self.assertNotIn("甲", html)
        self.save(peer, degree="bachelor", college="满珍纪念书院")
        self.login(self.undergrad)
        html = self.client.get("/roommates").get_data(as_text=True)
        self.assertIn("戊", html)
        self.assertNotIn("甲", html)
        self.assertNotIn("博士生", html)
        self.login(self.user)
        html = self.client.get("/roommates").get_data(as_text=True)
        self.assertIn("乙", html)
        self.assertIn("研究生宿舍", html)
        self.assertNotIn("丙", html)
        self.assertNotIn("丁", html)
        self.assertNotIn("博士生", html)
        mixed = self.client.get("/roommates?degree=all").get_data(as_text=True)
        self.assertIn("博士生", mixed)
        self.assertNotIn("丁", mixed)
        self.assertEqual(self.client.post(
            f"/roommates/wishes/{self.undergrad.id}", data={"csrf": "csrf"}).status_code, 403)

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
        third = User(email="seven@um.edu.mo", school="澳门大学", name="研三", email_verified=True,
                     gender="female", education_level="master")
        db.session.add(third)
        db.session.commit()
        self.save(third)
        self.login(self.other)
        self.assertEqual(self.client.post(f"/roommates/wishes/{third.id}", data={"csrf": "csrf"}).status_code, 400)
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

    def test_other_macau_schools_use_their_own_dorms(self):
        self.user.school = "澳门科技大学"
        db.session.commit()
        self.assertEqual(self.save(self.user, college="满珍纪念书院").status_code, 302)
        self.assertEqual(Profile.query.filter_by(user_id=self.user.id).one().college, "研究生宿舍")
        self.user.education_level = "bachelor"
        db.session.commit()
        self.assertEqual(self.save(self.user, degree="bachelor").status_code, 302)
        self.assertEqual(Profile.query.filter_by(user_id=self.user.id).one().college, "校园宿舍")

        self.other.school = "澳门理工大学"
        db.session.commit()
        self.assertEqual(self.save(self.other, college="不存在的楼").status_code, 400)
        self.assertEqual(self.save(self.other, college="明德楼").status_code, 302)
        self.undergrad.school = "澳门理工大学"
        db.session.commit()
        self.save(self.undergrad, degree="bachelor", college="南岸")
        self.login(self.other)
        self.assertNotIn("丁", self.client.get("/roommates").get_data(as_text=True))

        self.man.school = "澳门城市大学"
        self.man.gender = "female"
        db.session.commit()
        self.assertEqual(self.save(self.man, college="南园").status_code, 400)
        self.assertEqual(self.save(self.man, college="伟兴").status_code, 302)

    def test_sleep_time_is_written_by_the_student(self):
        self.assertEqual(self.save(self.user, sleep="1").status_code, 400)
        self.assertEqual(self.save(self.user, sleep="23:30").status_code, 302)
        self.assertEqual(Profile.query.filter_by(user_id=self.user.id).one().sleep, "23:30")
        page = self.client.get("/roommates").get_data(as_text=True)
        self.assertIn('name="sleep"', page)
        self.assertNotIn("<select name=\"sleep\"", page)
        self.assertIn('value="23:30"', page)
        self.save(self.other, sleep="early")
        self.login(self.user)
        shown = self.client.get("/roommates").get_data(as_text=True)
        self.assertIn("23 点前睡", shown)
        self.assertNotIn(">early<", shown)

    def test_off_campus_renters_match_by_area_across_degrees(self):
        self.assertEqual(self.save(self.user, college="校外合租").status_code, 400)
        self.assertEqual(self.save(self.user, college="校外合租", area="氹").status_code, 400)
        self.assertEqual(self.save(self.user, college="校外合租", area="氹仔").status_code, 302)
        saved = Profile.query.filter_by(user_id=self.user.id).one()
        self.assertEqual(saved.college, "校外合租")
        self.assertEqual(saved.area, "氹仔")
        self.save(self.undergrad, degree="bachelor", college="校外合租", area="氹仔")
        self.save(self.other, college="校外合租", area="澳门半岛")
        self.login(self.user)
        html = self.client.get("/roommates").get_data(as_text=True)
        self.assertIn("丁", html)
        self.assertNotIn("乙", html)
        self.assertIn("本科和研究生都看", html)
        self.login(self.undergrad)
        same = self.client.get("/roommates?degree=same").get_data(as_text=True)
        self.assertNotIn("甲", same)
        self.assertIn("甲", self.client.get("/roommates").get_data(as_text=True))

    def test_degree_place_and_mutual_wish_stay_consistent(self):
        self.assertEqual(self.save(self.user, degree="bachelor", college="满珍纪念书院").status_code, 400)
        self.assertEqual(Profile.query.count(), 0)
        self.save(self.undergrad, degree="bachelor", college="满珍纪念书院")
        peer = User(email="eight@um.edu.mo", school="澳门大学", name="戊二", email_verified=True,
                    gender="female", education_level="bachelor")
        db.session.add(peer)
        db.session.commit()
        self.save(peer, degree="bachelor", college="满珍纪念书院")
        self.login(self.undergrad)
        self.client.post(f"/roommates/wishes/{peer.id}", data={"csrf": "csrf"})
        self.assertEqual(self.save(self.undergrad, degree="bachelor", college="绍邦书院").status_code, 302)
        self.assertEqual(Wish.query.count(), 0)
        self.save(self.undergrad, degree="bachelor", college="满珍纪念书院")
        self.save(peer, degree="bachelor", college="满珍纪念书院")
        season = current_season()
        db.session.add(Wish(season=season, from_id=self.undergrad.id, to_id=peer.id))
        db.session.add(Wish(season=season, from_id=peer.id, to_id=self.undergrad.id))
        db.session.commit()
        self.login(self.undergrad)
        page = self.client.get("/roommates").get_data(as_text=True)
        self.assertIn(peer.email, page)
        self.assertEqual(Pair.query.count(), 1)
        self.assertEqual(self.save(self.undergrad, degree="bachelor", college="绍邦书院").status_code, 400)
        self.assertEqual(Profile.query.filter_by(user_id=self.undergrad.id).one().college, "满珍纪念书院")
