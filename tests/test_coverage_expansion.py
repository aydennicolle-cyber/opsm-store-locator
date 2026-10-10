"""Prevent missing-place classifications, future sites and aliases distorting counts."""
import csv,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from public_trading_status import infer_public_trading_status as status
from store_rules import meaningful_address,valid_store_point,current_competitor
from fetch_bailey_nelson_nz_stores import booking_stores,booking_coordinate_match
from reviewed_independents import validate_rows
from test_independent_intake import practice
from reconcile_luc_records import exact_identity
from build_local_coverage import pipeline_status,locate,norm
from discover_optical_coverage import coverage_query

class CoverageRules(unittest.TestCase):
 def test_setting_postcode_and_optometry_service_are_not_required_for_retail(self):
  row=practice();row.update(postal_code='',city='',location_setting='Other',setting_evidence_url='https://example.org/location',business_type='Prescription eyewear retail',services='Prescription glasses')
  validate_rows([row]);self.assertTrue(meaningful_address(row));self.assertTrue(valid_store_point(row))
  row['status']='Opening Soon';validate_rows([row]);self.assertFalse(current_competitor(row))
 def test_postcode_alone_and_nan_are_not_a_premises(self):
  self.assertFalse(meaningful_address(dict(full_address='Sydney NSW 2000')))
  self.assertTrue(meaningful_address(dict(full_address='111-117 Remembrance Driveway, Tahmoor, 2573, Australia')))
  self.assertTrue(meaningful_address(dict(full_address='Cnr Grant & Warners Streets, Port Douglas, Queensland, 4877')))
  self.assertFalse(valid_store_point(dict(country='Australia',latitude='nan',longitude=151)))
 def test_visible_status_wins_over_hours_and_old_image_names_do_not_close_stores(self):
  self.assertEqual(status('<h1>Mornington Coming Soon</h1>',{'openingHours':['Mon 09:00-17:00']}),'Opening Soon')
  self.assertEqual(status('<h1>Queenstown NOW OPEN</h1><img src="comingsoon.jpg">'),'Active')
  self.assertEqual(status('<h1>Branch</h1><img src="comingsoon.jpg">'),'Unknown')
  self.assertEqual(status('<h2>Opening in September</h2>'),'Opening Soon')
 def test_official_booking_fallback_needs_branch_postcode_and_same_numbered_street(self):
  booking=dict(id='N17',slug='queenstown',latitude='-45.012',longitude='168.742',address=dict(streetName='Shop C-09, 19 Grant Road',postalCode='9300'))
  encoded=json.dumps('data:'+json.dumps(booking,separators=(',',':')))
  self.assertEqual(booking_stores('self.__next_f.push([1,'+encoded+'])'),[booking])
  address=dict(streetAddress='19 Grant Road',postalCode='9300');url='https://baileynelson.co.nz/pages/optometrist-queenstown'
  self.assertIsNotNone(booking_coordinate_match(url,address,[booking]))
  self.assertIsNone(booking_coordinate_match(url,{**address,'streetAddress':'9 Grant Road'},[booking]))
  self.assertIsNone(booking_coordinate_match(url,{**address,'postalCode':'9301'},[booking]))
 def test_nearby_different_business_or_tenancy_never_links(self):
  source=dict(name='One Optical',address='Shop 1, 10 Main Street',chain='Brand',latitude=-33.86,longitude=151.2)
  store=dict(name='Different Optical',full_address='Shop 2, 10 Main Street',retailer='Brand',latitude=-33.86,longitude=151.2)
  self.assertFalse(exact_identity(source,store))
  self.assertFalse(exact_identity({**source,'name':'Different Optical'},store))
  self.assertTrue(exact_identity(source,{**store,'name':'One Optical','full_address':'Shop 1, 10 Main St'}))
 def test_planned_and_backup_are_not_assumed_to_have_opening_dates(self):
  self.assertEqual(pipeline_status('', 'Y'),'Planned — BN opening plan')
  self.assertEqual(pipeline_status('', ''),'Prospective — backup')
  self.assertEqual(pipeline_status('Opening October','Y'),'Opening Soon — supplier reported')
 def test_unknown_pipeline_location_stays_unlocated(self):
  self.assertEqual(norm('Main St'),norm('Main Street'))
  result=locate(dict(country='AU',area='Unknown suburb',venue='High Street',region='NSW'),[],[])
  self.assertIsNone(result['latitude']);self.assertEqual(result['precision'],'Unlocated')
 def test_discovery_includes_healthcare_and_eyewear_without_setting_gate(self):
  query=coverage_query('AU');self.assertIn('healthcare',query);self.assertIn('eyewear',query);self.assertNotIn('postcode',query);self.assertNotIn('high_street',query)
 def test_future_stores_are_mappable_but_not_current_competitors(self):
  from build_market_intelligence import build_centres
  stores={r['store_id']:r for r in csv.DictReader((ROOT/'data/optical_stores.csv').open())}
  cert={r['store_id']:r for r in csv.DictReader((ROOT/'data/store_certification.csv').open())}
  # Branches can open after review; apply the rule to current future-site statuses.
  for key,row in stores.items():
   if row['status']!='Opening Soon':continue
   with self.subTest(store=key):
    self.assertTrue(valid_store_point(stores[key]));self.assertEqual(cert[key]['eligible_for_analytics'],'false')
    self.assertEqual(build_centres([stores[key]]),[])
  self.assertEqual(stores['independent-other-optical-reviewed-au-stephen-henry-optometry']['location_type'],'Other')

if __name__=='__main__':unittest.main()
