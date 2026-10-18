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
    def test_real_export_has_no_commercial_fields_and_reconciles_anonymous_exclusions(self):
        data=Path(__file__).resolve().parents[1]/'data';x=evidence.load(data)
        for capture in x['captures']:
            if 'source_record_count' in capture:
                self.assertEqual(capture['source_record_count'],len(capture['records'])+capture['anonymous_record_count'])
            if capture['directory_complete']:
                self.assertEqual(capture['source_total'],capture.get('source_record_count',len(capture['records'])))

if __name__=='__main__':unittest.main()
