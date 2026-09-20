import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['MAIL_ENABLED'] = 'false'
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch
from age_rules import apply_age_fields, age_compatible
from matcher import batch_match_school, real_time_match
from app import app, ensure_schema, serialize_match_payload
from models import db, User, Match
from questionnaire import QUESTIONS
from match_pool import eligible_candidates

def person(id, gender='male', age=None, low=None, high=None):
    u=User(id=id, school='澳门大学', email=f'test{id}@um.edu.mo', email_verified=True,
           name='Test', gender=gender, looking_for='both', education_level='bachelor',
           profile_mode='privacy', bio='A'*40, age=age, preferred_age_min=low,
           preferred_age_max=high, open_to_match=True)
    u.feature_vector=[1.,0.]
    return u

class AgeRulesTests(unittest.TestCase):
    def test_mutual_inclusive_and_unknown(self):
        a,b=person(1,age=23,low=22,high=26),person(2,age=26,low=23,high=24)
        self.assertTrue(age_compatible(a,b))
        b.preferred_age_min=24
        self.assertFalse(age_compatible(a,b))
        a.preferred_age_min=a.preferred_age_max=None
        self.assertFalse(age_compatible(a,b))
        b.preferred_age_min=b.preferred_age_max=None;b.age=None
        self.assertTrue(age_compatible(a,b))
        a.preferred_age_min=18;a.preferred_age_max=100
        self.assertFalse(age_compatible(a,b))
    def test_validation_and_no_partial_mutation(self):
        for bad in [True, '23', 23.5, 17, 101, [], {}]:
            u=person(1,age=25)
            self.assertEqual(apply_age_fields(u,{'age':bad}),'age.invalid')
            self.assertEqual(u.age,25)
        self.assertEqual(apply_age_fields(person(1),{},True),'age.required')
        self.assertEqual(apply_age_fields(person(1),{'preferred_age_min':20,'preferred_age_max':30}),'age.needOwn')
        self.assertEqual(apply_age_fields(person(1,age=23),{'preferred_age_min':30,'preferred_age_max':20}),'age.rangeInvalid')
    def test_clear_age_and_preferences_together(self):
        u=person(1,age=23,low=20,high=25)
        self.assertIsNone(apply_age_fields(u,{'age':None,'preferred_age_min':None,'preferred_age_max':None}))
        self.assertIsNone(u.age)
    def test_full_legacy_stays_ready(self):
        u=person(1);u.profile_mode='full';u.wechat_id='test'
        with patch.object(User,'questionnaire_completed',return_value=True):
            self.assertTrue(u.in_match_pool())
    def test_age_filter_before_both_batch_algorithms(self):
        for both in [True,False]:
            a,b,c=person(1,'female',23,22,26),person(2,'male',40),person(3,'male',24)
            if not both:
                a.looking_for='male';b.looking_for=c.looking_for='female'
            result=batch_match_school([a,b,c])
            self.assertEqual({result[0][0].id,result[0][1].id},{1,3})
    def test_realtime_excludes_unknown_and_out_of_range(self):
        a=person(1,age=23,low=22,high=26)
        result=real_time_match(a,[person(2,age=None),person(3,age=40),person(4,age=24)])
        self.assertEqual([u.id for u,s in result],[4])
    def test_pair_filter_and_min_score_before_assignment(self):
        a,b,c=person(1,'female',23),person(2,age=24),person(3,age=25)
        a.looking_for='male';b.looking_for=c.looking_for='female'
        result=batch_match_school([a,b,c],pair_filter=lambda x,y:y.id!=2)
        self.assertEqual(result[0][1].id,3)
        self.assertEqual(batch_match_school([a,b,c],min_score=1.1),[])

class AgeAPITests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING']=True
        self.ctx=app.app_context();self.ctx.push();db.create_all()
        self.u=person(1);db.session.add(self.u);db.session.commit()
        self.client=app.test_client()
        with self.client.session_transaction() as s:s['user_id']=1
    def tearDown(self):
        db.session.remove();db.drop_all();self.ctx.pop()
    def test_full_requires_age_direct_api(self):
        r=self.client.post('/api/questionnaire',json={'answers':{}})
        self.assertFalse(r.json['ok']);self.assertIn('周岁',r.json['error'])
    def test_full_submission_persists_age(self):
        answers={str(q['id']):3 if q['type']=='scale' else [q['options'][0]] for q in QUESTIONS if q['type'] in ('scale','multi')}
        self.u.wechat_id='test';db.session.commit()
        r=self.client.post('/api/questionnaire',json={'answers':answers,'age':23,'preferred_age_min':21,'preferred_age_max':26})
        self.assertTrue(r.json['ok'],r.json)
        self.assertEqual(db.session.get(User,1).age,23)
    def test_privacy_can_submit_without_age(self):
        r=self.client.post('/api/express-profile',json={'name':'Test','gender':'male','looking_for':'both','education_level':'bachelor','bio':'A'*40,'age':None})
        self.assertTrue(r.json['ok'],r.json)
        self.assertTrue(db.session.get(User,1).in_match_pool())
    def test_unknown_cannot_request_limits_api(self):
        r=self.client.put('/api/me',json={'preferred_age_min':22,'preferred_age_max':26})
        self.assertFalse(r.json['ok'])
    def test_old_full_user_unrelated_update_allowed(self):
        self.u.profile_mode='full';self.u.wechat_id='test';db.session.commit()
        r=self.client.put('/api/me',json={'name':'Updated'})
        self.assertTrue(r.json['ok'],r.json)
    def test_candidate_filter_and_no_historical_deactivation(self):
        b=person(2,age=24,low=22,high=26);db.session.add(b);db.session.commit()
        self.assertEqual(eligible_candidates(self.u),[])
        m=Match(user1_id=1,user2_id=2,score=.8,active=True);db.session.add(m);db.session.commit()
        r=self.client.put('/api/me',json={'age':40})
        self.assertTrue(r.json['ok'],r.json);self.assertTrue(m.active)
    def test_partner_payload_hides_limits_and_inactive_age(self):
        self.u.age=24;self.u.preferred_age_min=22;self.u.preferred_age_max=26
        self.assertEqual(serialize_match_payload(self.u, .8, {})['age'],24)
        self.assertNotIn('preferred_age_min',serialize_match_payload(self.u, .8, {}))
        self.assertIsNone(serialize_match_payload(self.u, .8, {}, active=False)['age'])
    def test_schema_migration_preserves_old_pool_flags(self):
        db.session.remove()
        for name in ('age','preferred_age_min','preferred_age_max','age_confirmed_at'):
            db.session.execute(db.text(f'ALTER TABLE users DROP COLUMN {name}'))
        db.session.commit();ensure_schema();ensure_schema()
        old=db.session.get(User,1)
        self.assertIsNone(old.age);self.assertTrue(old.open_to_match)

if __name__=='__main__':unittest.main()

