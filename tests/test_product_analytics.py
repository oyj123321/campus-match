import unittest
from datetime import datetime,timedelta
from unittest.mock import patch
from flask import Flask, jsonify, session
from models import db, User, ProductJourney, Match
from product_analytics import enroll_new_user, observe_response, cohort_summary


class ProductAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.app=Flask(__name__)
        self.app.config.update(SECRET_KEY='test',SQLALCHEMY_DATABASE_URI='sqlite:///:memory:')
        db.init_app(self.app)
        self.app.after_request(observe_response)
        self.ctx=self.app.app_context(); self.ctx.push();db.create_all()
        self.client=self.app.test_client()

    def tearDown(self):
        db.session.remove();db.drop_all();self.ctx.pop()

    def test_signup_recorded_once_and_legacy_not_backfilled(self):
        @self.app.route('/register',methods=['POST'],endpoint='api_register')
        def register():
            u=User.query.filter_by(email='new@example.test').first()
            if not u:
                u=User(email='new@example.test',school='A')
                db.session.add(u);db.session.flush();enroll_new_user(u);db.session.commit()
            return jsonify(ok=True)
        for _ in range(2):
            self.client.post('/register',json={'email':'new@example.test'})
        self.assertEqual(ProductJourney.query.count(),1)
        self.assertEqual(cohort_summary()['total'],1)
        ProductJourney.query.delete(); db.session.commit()
        self.client.post('/register',json={'email':'new@example.test'})
        self.assertEqual(ProductJourney.query.count(),0)

    def test_failed_response_does_not_record_milestone(self):
        u=User(email='new@example.test',school='A',email_verified=True)
        db.session.add(u);db.session.commit()
        db.session.add(ProductJourney(user_id=u.id,school='A',registered_at=datetime.utcnow()))
        db.session.commit()
        @self.app.route('/verify',methods=['POST'],endpoint='api_verify')
        def verify():return jsonify(ok=False)
        with self.client.session_transaction() as s:s['user_id']=u.id
        self.client.post('/verify')
        self.assertIsNone(db.session.get(ProductJourney,u.id).verified_at)

    def test_enrollment_survives_failed_email_but_rolls_back_with_account(self):
        @self.app.route('/register',methods=['POST'],endpoint='api_register')
        def register():
            u=User(email='retry@example.test',school='A')
            db.session.add(u);db.session.flush();enroll_new_user(u);db.session.commit()
            return jsonify(ok=False),503
        self.client.post('/register',json={'email':'retry@example.test'})
        self.assertEqual(ProductJourney.query.count(),1)
        u=User(email='rollback@example.test',school='A')
        db.session.add(u);db.session.flush();enroll_new_user(u);db.session.rollback()
        self.assertEqual(ProductJourney.query.count(),1)

    def test_cohort_order_scope_and_repeat_reads(self):
        now=datetime.utcnow()
        a=User(email='a@example.test',school='A');b=User(email='b@example.test',school='B')
        db.session.add_all([a,b]);db.session.flush()
        db.session.add_all([
            ProductJourney(user_id=a.id,school='A',registered_at=now-timedelta(days=5),
                           verified_at=now-timedelta(days=4),profile_at=now-timedelta(days=3),
                           viewed_at=now),
            ProductJourney(user_id=b.id,school='B',registered_at=now-timedelta(days=5))])
        db.session.add(Match(user1_id=a.id,user2_id=b.id,created_at=now-timedelta(days=1)))
        db.session.commit()
        self.assertEqual([s['count'] for s in cohort_summary()['rows']],[2,1,1,1,1,1])
        self.assertEqual([s['count'] for s in cohort_summary(school='B')['rows']],[1,0,0,0,0,0])
        self.assertEqual(cohort_summary(school='missing')['total'],0)

    def test_empty_result_is_not_viewed_and_successful_reads_are_idempotent(self):
        u=User(email='a@example.test',school='A')
        db.session.add(u);db.session.commit()
        db.session.add(ProductJourney(user_id=u.id,school='A',registered_at=datetime.utcnow()))
        db.session.commit()
        results=[]
        @self.app.route('/matches',endpoint='api_get_matches')
        def matches():return jsonify(ok=True,matches=results)
        with self.client.session_transaction() as s:s['user_id']=u.id
        self.client.get('/matches')
        self.assertIsNone(db.session.get(ProductJourney,u.id).viewed_at)
        results.append({'active':True})
        self.client.get('/matches')
        first=db.session.get(ProductJourney,u.id).viewed_at
        self.client.get('/matches')
        self.assertEqual(db.session.get(ProductJourney,u.id).viewed_at,first)

    def test_account_deletion_removes_journey(self):
        from app import _purge_user_account
        u=User(email='a@example.test',school='A');db.session.add(u);db.session.commit()
        db.session.add(ProductJourney(user_id=u.id,school='A',registered_at=datetime.utcnow()))
        db.session.commit();_purge_user_account(u);db.session.commit()
        self.assertEqual(ProductJourney.query.count(),0)
