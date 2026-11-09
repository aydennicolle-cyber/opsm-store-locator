import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import build_location_news as news
from scripts.location_news_schema import document
from scripts.scan_public_privacy import walk


def fixture():
    v = dict(revision_id='revision-a', published_on='2026-08', recorded_at='2026-10-21', date_basis='Month reported',
             title='A project update', statements=[dict(text='Owner reports construction.',kind='source_report',source_ids=['source-a'])],
             sources=[dict(source_id='source-a',url='https://example.com/report',title='Owner release')], timing='Expected next year', uncertainty='Completion unconfirmed',metrics=[])
    e = dict(event_id='project-a',aliases=['old-project-a'],parent_event_id=None,kind='news',scope='location',relations=[dict(kind='area_store',entity_id='store-a',label='Area nearby',basis='Approximate project location; relevance only',source_urls=['https://example.com/report'],distance_km=0.5)],versions=[v])
    return dict(schema_version=1,document_type='location_news',events=[e],checks=[])


class LocationNewsTests(unittest.TestCase):
    def test_dates_allow_unknown_year_month_day_not_fake_precision(self):
        for value in [None,'2024','2026-08','2026-08-25']:
            d=fixture();d['events'][0]['versions'][0]['published_on']=value;document(d)
        for value in ['2026-02-30','2026-13','yesterday']:
            d=fixture();d['events'][0]['versions'][0]['published_on']=value
            with self.assertRaises(ValueError):document(d)

    def test_nested_private_or_unexpected_fields_fail(self):
        for path in [[],['events',0],['events',0,'versions',0],['events',0,'relations',0],['events',0,'versions',0,'sources',0]]:
            d=fixture();node=d
            for key in path:node=node[key]
            node['unexpected_note']='synthetic hidden field'
            with self.assertRaises(ValueError):walk(d,Path('location_news.json'))

    def test_alias_merges_and_replay_is_idempotent(self):
        e=fixture()['events'][0];changed=copy.deepcopy(e)
        changed['event_id']='old-project-a';changed['aliases']=[]
        changed['versions'][0]['revision_id']='revision-b';changed['versions'][0]['title']='Later correction'
        merged=news.merge_events([e,changed,e]);self.assertEqual(len(merged),1)
        self.assertEqual(len(merged[0]['versions']),2)
        self.assertEqual(merged[0]['versions'][0]['title'],'A project update')

    def test_recheck_does_not_create_new_revision(self):
        v=fixture()['events'][0]['versions'][0];before=news.revision_id('project-a',v)
        v['recorded_at']='2026-10-23';self.assertEqual(before,news.revision_id('project-a',v))

    def test_unknown_entities_and_missing_source_rejected(self):
        with self.assertRaises(ValueError):document(fixture(),set(),set())
        d=fixture();d['events'][0]['versions'][0]['statements'][0]['source_ids']=['missing']
        with self.assertRaises(ValueError):document(d)

    def test_failed_check_cannot_become_success(self):
        d=fixture();d['checks']=[dict(source_url='https://example.com/report',attempted_at='2026-10-23',status='blocked',last_success_at='2026-10-23',note='Blocked')]
        with self.assertRaises(ValueError):document(d)
        d['checks'][0]['last_success_at']='2026-10-21';document(d)

    def test_nearest_is_country_and_eligibility_scoped_without_membership(self):
        rows=[dict(store_id='a',country='Australia',status='Active',usable_for_network='true',latitude=-27,longitude=153),dict(store_id='b',country='New Zealand',status='Active',usable_for_network='true',latitude=-27.001,longitude=153)]
        original=copy.deepcopy(rows)
        self.assertEqual(news.nearest_store(-27.001,153,'Australia',rows)[0]['store_id'],'a')
        self.assertEqual(rows,original)
        self.assertIsNone(news.nearest_store(None,153,'Australia',rows))
        rows[0]['status']='Closed';self.assertIsNone(news.nearest_store(-27,153,'Australia',rows))

    def test_metric_needs_reporting_period(self):
        d=fixture();d['events'][0]['versions'][0]['metrics']=[dict(metric_id='m',name='Visits',value=12,unit='million visits',currency=None,period='',definition='Visits, not unique customers',source_id='source-a',uncertainty='')]
        with self.assertRaises(ValueError):document(d)


class NetworkDetectionTests(unittest.TestCase):
    def test_database_removal_is_not_closure_and_remap_not_opening(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import build_market_intelligence as market
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp);history=data/'history';history.mkdir()
            (data/'data_health.json').write_text(json.dumps({'certification_status':'Certified'}))
            (data/'store_identity_remaps.csv').write_text('source_store_id,canonical_store_id\nold-id,new-id\n')
            base=dict(store_id='old-id',retailer='Test',country='Australia',full_address='10 Test Street',latitude=-27,longitude=153)
            (history/'2026-10-20.json').write_text(json.dumps(dict(snapshot_date='2026-10-20',stores={'old-id':base,'gone':{**base,'store_id':'gone'}})))
            with patch.object(market,'DATA_DIR',data),patch.object(market,'HISTORY_DIR',history):
                out=market.build_history([{**base,'store_id':'new-id','fetched_at':'2026-10-23'}])
            self.assertEqual([e['type'] for e in out['events']],['Record removed'])
            self.assertTrue(all(e['classification']=='detected_change' for e in out['events']))


if __name__ == '__main__':unittest.main()
