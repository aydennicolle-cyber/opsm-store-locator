import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from reviewed_place_points import apply_place_point_reviews

class PlacePointReviewsTests(unittest.TestCase):
 def setUp(self):
  self.places=[dict(place_id='p',country='Australia',latitude=-37.9,longitude=145.1,source_date='2026-09-02',owner='Existing owner')]
  self.stores=[dict(store_id='s',latitude='-37.8',longitude='145.2')]
  self.members=[dict(store_id='s',place_id='p',review_status='Accepted',verified_at='2026-09-03')]
  self.row=dict(place_id='p',latitude='-37.8',longitude='145.2',evidence_url='https://example.com/property',verified_at='2026-10-05',confidence='Medium',method='Named property map',reference_store_id='',reason='Named public property point; boundary not surveyed.')
 def apply(self,row):apply_place_point_reviews(self.places,self.stores,self.members,[row])
 def test_coordinate_review_preserves_tenancy_dates_and_unrelated_property_facts(self):
  before=copy.deepcopy(self.members);self.apply(self.row)
  self.assertEqual(self.places[0]['latitude'],-37.8);self.assertEqual(self.places[0]['source_date'],'2026-09-02')
  self.assertEqual(self.places[0]['owner'],'Existing owner');self.assertEqual(self.members,before)
 def test_accepts_explicit_low_confidence_tenant_reference(self):
  self.apply(dict(self.row,method='Accepted tenant reference',confidence='Low',reference_store_id='s'))
  self.assertEqual(self.places[0]['coordinate_reference_store_id'],'s')
 def test_nearby_or_unaccepted_store_cannot_establish_reference(self):
  for change in [dict(place_id='other'),dict(review_status='Needs review')]:
   self.members[0].update(change)
   with self.assertRaises(ValueError):self.apply(dict(self.row,method='Accepted tenant reference',confidence='Low',reference_store_id='s'))
 def test_tenant_reference_cannot_claim_high_confidence_or_different_point(self):
  for fields in [dict(confidence='High'),dict(latitude='-37.8001')]:
   with self.assertRaises(ValueError):self.apply(dict(self.row,method='Accepted tenant reference',confidence='Low',reference_store_id='s')|fields)
 def test_rejects_invalid_evidence_and_nonfinite_or_wrong_country_points(self):
  for fields in [dict(latitude='nan'),dict(latitude=True),dict(longitude='175'),dict(evidence_url='file:///private/x'),dict(verified_at='yesterday'),dict(reason=''),dict(method='Nearby shop')]:
   with self.subTest(fields=fields),self.assertRaises(ValueError):self.apply(self.row|fields)
 def test_unknown_duplicate_and_invalid_rows_fail_before_mutation(self):
  for extra in [self.row,dict(self.row,place_id='missing'),dict(self.row,place_id='p2',longitude='nan')]:
   initial=copy.deepcopy(self.places)
   with self.assertRaises(ValueError):apply_place_point_reviews(self.places,self.stores,self.members,[self.row,extra])
   self.assertEqual(self.places,initial)
 def test_precinct_anchor_preserves_format_and_requires_explicit_low_confidence(self):
  self.places[0].update(place_type='Retail Precinct',location_setting='High Street')
  with self.assertRaises(ValueError):self.apply(self.row|dict(method='Reviewed street geometry'))
  with self.assertRaises(ValueError):self.apply(self.row|dict(method='Reviewed precinct street anchor'))
  self.apply(self.row|dict(method='Reviewed precinct street anchor',confidence='Low'))
  self.assertEqual(self.places[0]['place_type'],'Retail Precinct')
  self.assertEqual(self.places[0]['location_setting'],'High Street')
if __name__=='__main__':unittest.main()
