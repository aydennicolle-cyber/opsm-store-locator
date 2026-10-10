"""Private research priorities must not change public trading or place evidence."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_local_coverage import enrich_appraisals


def target(key, **changes):
    return dict(id=key, name=key, country='AU', status='Planned — BN opening plan',
                source_kind='target', committed_fy31='Y', opening_sequence='1',
                latitude=-33.8, longitude=151.1, **changes)


class TargetAppraisalTests(unittest.TestCase):
    def test_name_match_does_not_establish_place_appraisal(self):
        rows=[target('unreviewed', place_id='p')]
        enrich_appraisals(rows, [], [dict(place_id='p', name='Centre')], {}, {}, [])
        self.assertFalse(rows[0]['appraisal']['mapping_accepted'])
        self.assertIsNone(rows[0]['appraisal']['public_screen'])

    def test_reviewed_mapping_can_reuse_public_screen_without_changing_score(self):
        rows=[target('reviewed', place_id='p', location_review_date='2026-09-27')]
        rank=dict(place_id='p', score=42, market_features={'population':100})
        enrich_appraisals(rows, [], [dict(place_id='p', name='Centre')], {'au':[rank]}, {}, [])
        self.assertEqual(rows[0]['appraisal']['public_screen']['score'],42)
        self.assertTrue(rows[0]['appraisal']['mapping_accepted'])

    def test_open_and_canadian_records_do_not_enter_anz_target_queue(self):
        opened=target('open');opened['status']='Open — public confirmed'
        canada=target('ca');canada['country']='CA'
        rows=[opened,canada,target('planned')]
        self.assertEqual(enrich_appraisals(rows,[],[],{},{},[]),['planned'])

    def test_research_priority_preserves_plan_and_missing_mapping(self):
        backup=target('backup');backup['committed_fy31']='N'
        reviewed=target('reviewed',place_id='p',location_review_date='2026-09-27')
        rows=[backup,reviewed,target('unresolved')]
        queue=enrich_appraisals(rows,[],[dict(place_id='p',name='Centre')],{},{},[])
        self.assertEqual(queue,['unresolved','reviewed','backup'])

    def test_future_store_is_not_current_bn_and_proposal_is_separate(self):
        rows=[target('one'),target('two')]
        store=dict(store_id='future',name='Future',retailer='Bailey Nelson',country='Australia',status='Opening Soon',latitude=-33.8,longitude=151.1,full_address='10 Main Street')
        enrich_appraisals(rows,[store],[],{},{},[])
        self.assertIsNone(rows[0]['appraisal']['nearest_current_bn'])
        self.assertEqual(rows[0]['appraisal']['nearest_other_target']['id'],'two')


if __name__=='__main__':unittest.main()
