import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import public_directory_evidence as evidence
from market_points import resolve_market,authoritative_link
from build_property_intelligence import competitor_context

class PublicDirectoryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.place=dict(place_id='place-au-act-example',name='Example Market',country='Australia',state='ACT',locality='Kingston',format='Shopping Centre',address='34 Example Street',sources=[dict(url='https://example.org/directory',observed_at='2026-10-18')],reviewed_at='2026-10-18',scope='Named property only',latitude=None,longitude=None,coordinate_source_url=None)
        self.payload=dict(schema_version=1,places=[self.place],captures=[])
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.data=Path(self.temp.name)
    def load(self):
        (self.data/evidence.FILE).write_text(json.dumps(self.payload));return evidence.load(self.data)
    def test_accepted_identity_can_be_searchable_without_inventing_point_or_trading(self):
        self.load();places=[];evidence.add_places(places,self.data)
        self.assertEqual(places[0]['name'],'Example Market');self.assertIsNone(places[0]['latitude']);self.assertEqual(places[0]['status'],'Mapped')
        self.assertIsNone(authoritative_link(places[0]));self.assertEqual(resolve_market(places[0],[]),(None,'Map reference unresolved'))
        context=competitor_context(places[0],[dict(latitude=-35,longitude=149,retailer='OPSM')]);self.assertEqual(context['nearest_by_retailer_km'],{});self.assertIsNone(context['independent_2km_count'])
    def test_private_fields_and_identifiers_fail_closed(self):
        for changes in [dict(rank=1),dict(bn_sources=[]),dict(scope='/Users/name/private.json'),dict(scope='bn-target-au-1')]:
            with self.subTest(changes=changes):
                self.payload['places']=[self.place|changes]
                with self.assertRaises(ValueError):self.load()
    def test_invalid_public_source_or_partial_coordinate_is_rejected(self):
        for changes in [dict(sources=[dict(url='http://localhost/a')]),dict(latitude=-35),dict(latitude=-35,longitude=149,coordinate_source_url=None)]:
            with self.subTest(changes=changes):
                self.payload['places']=[self.place|changes]
                with self.assertRaises(ValueError):self.load()
    def test_research_cannot_overwrite_an_existing_identity(self):
        self.load();places=[dict(place_id=self.place['place_id'],name='Existing')];before=copy.deepcopy(places)
        with self.assertRaises(ValueError):evidence.add_places(places,self.data)
        self.assertEqual(places,before)
    def test_explicit_store_reference_preserves_directory_identity(self):
        definitions={self.place['place_id']:self.place}
        before=copy.deepcopy(definitions)
        store=dict(country='Australia',state='ACT')
        override=dict(canonical_place_id=self.place['place_id'],location_setting='Shopping Centre',canonical_name='Tenant supplied label')
        self.assertEqual(evidence.reviewed_reference(store,override,definitions),self.place['place_id'])
        self.assertEqual(definitions,before)
        self.assertIsNone(evidence.reviewed_reference(store,override|{'canonical_place_id':'unknown'},definitions))
        for change in [dict(country='New Zealand'),dict(state='VIC')]:
            with self.assertRaises(ValueError):evidence.reviewed_reference(store|change,override,definitions)
        with self.assertRaises(ValueError):evidence.reviewed_reference(store,override|{'location_setting':'High Street'},definitions)
    def test_additional_count_sample_supports_presence_without_adding_overlapping_totals(self):
        capture=dict(place_id=self.place['place_id'],records=[],source_urls=['https://example.org/map'],source_total=None,directory_complete=False,format_scope='named street',scope='Fixed street segment',capture_method='Addressed records',limitations='Partial',absence_reviews=[],source_record_count=2,anonymous_record_count=2,anonymous_counts=dict(hospitality_venues=0,as_of='2026-10-01',additional_samples=[dict(hospitality_venues=2,observed_at='2026-10-18',source_urls=['https://example.org/map'])]))
        self.payload['captures']=[capture];self.load()
        base=dict(metadata={},features=[],places=[dict(place_id=self.place['place_id'],name='Example',format='High Street',features={},optical=[],observations=[])])
        got=evidence.apply(base,self.data)['places'][0]
        self.assertEqual(got['observations'],[])
        self.assertEqual(got['anonymous_counts']['hospitality_venues'],0)
        self.assertEqual(len(got['features']['category:food and dining']),1)
        self.assertEqual(got['anonymous_counts']['evidence'][0]['count'],2)
        self.assertEqual(got['anonymous_counts']['evidence'][0]['observed_at'],'2026-10-18')
    def test_real_export_has_no_commercial_fields_and_reconciles_anonymous_exclusions(self):
        data=Path(__file__).resolve().parents[1]/'data';x=evidence.load(data)
        for capture in x['captures']:
            if 'source_record_count' in capture:
                self.assertEqual(capture['source_record_count'],len(capture['records'])+capture['anonymous_record_count'])
            if capture['directory_complete']:
                self.assertEqual(capture['source_total'],capture.get('source_record_count',len(capture['records'])))

if __name__=='__main__':unittest.main()
