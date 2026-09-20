import unittest
from admin_analysis import build_analysis
from matching_analytics import LABELS, diagnose, aggregate
from test_matching_analytics import person


def report(uid, n=100, matched=80, **extra):
    return dict(id=uid, status='completed', participants=n, matched=matched,
                unmatched=n-matched, rate=100*matched/n if n else 0,
                reasons={'combined': n-matched} if matched < n else {},
                schools=[], version=2, policy=[.15, True, False], **extra)


class AnalysisViewTests(unittest.TestCase):
    def test_weighted_baseline_and_earlier_only(self):
        reports = [report(4,100,20), report(3,100,60), report(2,20,20), report(1,100,50)]
        result = build_analysis(reports, LABELS, round_id=3)
        self.assertEqual(result['comparison']['baseline'], 58.3)
        self.assertEqual(result['comparison']['baseline_n'], 120)
        self.assertEqual(result['comparison']['delta'], -40)
        reports[2]['policy'] = ['other']
        result = build_analysis(reports, LABELS, round_id=3)
        self.assertEqual(result['comparison']['previous_id'], 1)

    def test_school_filter_scopes_every_metric_without_leaking_global_values(self):
        row = report(1)
        row['schools'] = [dict(school='A',participants=20,matched=10,unmatched=10,rate=50,
                              reasons={'age':10},one_candidate=3)]
        row['history_exhausted'] = 77
        result = build_analysis([row],LABELS,school='A')
        self.assertEqual(result['latest']['rate'],50)
        self.assertEqual(result['latest']['reasons'],{'age':10})
        self.assertNotIn('history_exhausted',result['latest'])
        self.assertEqual(result['trend'][0]['participants'],20)
        self.assertIsNone(build_analysis([row],LABELS,school='missing')['latest'])
        self.assertEqual(row['matched'],80)

    def test_persistent_drop_alert_and_small_sample_suppression(self):
        rows = [report(5,100,50), report(4,100,50), report(3), report(2), report(1)]
        result = build_analysis(rows,LABELS)
        self.assertTrue(any('连续两轮' in a['text'] for a in result['alerts']))
        rows[0] = report(5,10,5)
        result = build_analysis(rows,LABELS)
        self.assertFalse(any('连续两轮' in a['text'] for a in result['alerts']))
        self.assertTrue(any('样本少于' in a['text'] for a in result['alerts']))

    def test_failure_not_treated_as_zero_and_invalid_round_not_silently_replaced(self):
        failed = dict(id=2,status='failed',participants=100)
        result = build_analysis([failed,report(1)],LABELS,round_id=2)
        self.assertIsNone(result['latest'])
        self.assertEqual(len(result['trend']),1)
        self.assertTrue(result['alerts'])
        self.assertIsNone(build_analysis([report(1)],LABELS,round_id=9)['latest'])

    def test_shared_sole_candidate_and_history_exhaustion(self):
        users = [person(1,'female'),person(2,'male'),person(3,'male')]
        users[0].looking_for='male'
        users[1].looking_for=users[2].looking_for='female'
        state = diagnose(users)
        result = aggregate(users,state,{1,2},{})
        self.assertEqual(result['one_candidate'],2)
        self.assertEqual(result['many_candidates'],1)
        self.assertEqual(result['contested_sole'],2)
        result = aggregate(users,diagnose(users,{(1,2),(1,3)}),set(),{})
        self.assertEqual(result['history_exhausted'],3)
        self.assertEqual(result['no_candidates'],3)

    def test_old_school_detail_is_unknown_not_global(self):
        row=report(1)
        row['schools']=[dict(school='A',participants=10,matched=4)]
        result=build_analysis([row],LABELS,school='A')
        self.assertTrue(result['latest']['diagnosis_unavailable'])
        self.assertEqual(result['latest']['rate'],40)
        self.assertEqual(result['latest']['unmatched'],6)
        self.assertNotIn('reasons',result['latest'])
