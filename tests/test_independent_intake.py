"""External source flags and proximity must never silently admit competitors."""
import csv
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import reviewed_independents as reviewed
import stage_independent_candidates as intake
import build_market_intelligence as market


def practice():
    return dict(id="au-example", name="Example Optometrists", country="Australia", state="NSW", city="Sydney", postal_code="2000", full_address="1 Example Street, Sydney NSW 2000", latitude="-33.86", longitude="151.2", official_url="https://example.org/location", services="Optometry and prescription eyewear", status="Active", business_type="Permanent retail optometry", location_setting="Uncertain", identity_reviewed="true", coordinates_reviewed="true", identity_evidence_url="https://example.org/location", coordinate_evidence_url="https://example.org/map", status_evidence_url="https://example.org/location", setting_evidence_url="", verified_at=date.today().isoformat(), evidence_notes="Identity and address checked; setting remains unresolved.")


def supplier(flag="true"):
    return dict(id="17", name="Example Optometrists", country="AU", address="1 Example Street, Sydney NSW 2000", lat="-33.86", lng="151.2", verified_optometry=flag)


class AdmissionTests(unittest.TestCase):
    def test_retailer_without_website_can_retain_authoritative_evidence(self):
        row=practice();row['official_url']='';row['status']='Unknown'
        row['identity_evidence_url']='https://www.health.qld.gov.au/dispenser-directory'
        row['status_evidence_url']=row['identity_evidence_url']
        reviewed.validate_rows([row])
        self.assertEqual(row['official_url'],'')
        self.assertEqual(row['status'],'Unknown')

    def test_missing_website_does_not_bypass_evidence_requirements(self):
        for field in ('identity_evidence_url','coordinate_evidence_url','status_evidence_url'):
            row=practice();row['official_url']='';row[field]=''
            with self.subTest(field=field), self.assertRaises(ValueError):
                reviewed.validate_rows([row])

    def test_supplied_website_must_still_be_a_public_url(self):
        row=practice();row['official_url']='not a URL'
        with self.assertRaises(ValueError):reviewed.validate_rows([row])

    def test_evidence_not_supplier_flags_controls_admission(self):
        reviewed.validate_rows([practice()])
        for field, value in [("identity_reviewed","false"),("coordinates_reviewed","false"),("business_type","Ophthalmology"),("coordinate_evidence_url",""),("full_address","Australia"),("latitude","nan"),("verified_at","2099-01-01")]:
            row=practice();row[field]=value
            with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                reviewed.validate_rows([row])

    def test_duplicate_tenancies_require_resolution(self):
        a=practice();b=deepcopy(a);b["id"]="au-other-name";b["name"]="A Doctor's Name"
        with self.assertRaises(ValueError):reviewed.validate_rows([a,b])

    def test_unknown_setting_is_explicit_and_known_setting_needs_evidence(self):
        row=practice()
        self.assertEqual(reviewed.classifications([row])[reviewed.ID_PREFIX+row['id']]['location_type'],'Unclassified')
        row['location_setting']='Shopping Centre'
        with self.assertRaises(ValueError):reviewed.validate_rows([row])

    def test_research_additions_are_not_reported_as_openings(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);history=root/'history';history.mkdir()
            old=dict(store_id='existing',retailer='Independent / Other optical',country='Australia',name='Old Practice',status='Active',state='NSW',suburb='Sydney',full_address='1 Main Street',latitude='-33.86',longitude='151.2',venue_id='')
            (history/'2026-09-01.json').write_text(json.dumps(dict(snapshot_date='2026-09-01',stores={'existing':old})))
            (root/'data_health.json').write_text(json.dumps(dict(certification_status='Certified')))
            new={**old,'store_id':reviewed.ID_PREFIX+'au-new','name':'Newly Discovered Practice','fetched_at':'2026-09-11'}
            with patch.object(market,'HISTORY_DIR',history),patch.object(market,'DATA_DIR',root):
                result=market.build_history([{**old,'fetched_at':'2026-09-11'},new])
            self.assertEqual(result['events'],[])
            self.assertEqual(result['discovery_records_added'],[new['store_id']])

    def test_published_reviewed_records_preserve_setting_uncertainty(self):
        stores={r['store_id']:r for r in intake.read_csv(ROOT/'data/optical_stores.csv')}
        memberships={r['store_id']:r for r in intake.read_csv(ROOT/'data/store_place_memberships.csv')}
        certificates={r['store_id']:r for r in intake.read_csv(ROOT/'data/store_certification.csv')}
        overrides={r['store_id']:r for r in intake.read_csv(ROOT/'data/store_place_overrides.csv')}
        for row in reviewed.read_reviewed_rows():
            key=reviewed.ID_PREFIX+row['id']
            with self.subTest(store=key):
                if stores[key]['retailer'] == 'Sunglass Hut':
                    # Complete operator refresh retains the original intake ID,
                    # but supersedes its old source date with current evidence.
                    snapshot=json.loads((ROOT/'retailers/sunglass-hut/source_snapshot.json').read_text())
                    self.assertEqual(stores[key]['fetched_at'],snapshot['fetched_at'])
                    self.assertEqual(certificates[key]['source_id'],'sunglass-hut-anz')
                    self.assertIn(stores[key]['official_url'], {r['source_url'] for r in snapshot['stores']})
                elif stores[key]['retailer'] == 'Oakley':
                    snapshot=json.loads((ROOT/'retailers/oakley/source_snapshot.json').read_text())
                    self.assertEqual(stores[key]['fetched_at'],snapshot['fetched_at'])
                    self.assertEqual(certificates[key]['source_id'],'oakley-au')
                    self.assertIn(stores[key]['source_url'],snapshot['source_urls'])
                else:
                    self.assertEqual(stores[key]['fetched_at'][:10],row['verified_at'])
                    self.assertEqual(certificates[key]['source_id'],reviewed.SOURCE_ID)
                self.assertEqual(certificates[key]['usable_for_network'],'true')
                if row['location_setting']=='Uncertain' and key in overrides:
                    # A subsequent evidence-backed membership review may resolve
                    # setting without rewriting the original intake observation.
                    decision=overrides[key]
                    self.assertTrue(decision['official_url'].startswith('https://'))
                    self.assertTrue(decision['evidence_basis'])
                    self.assertEqual(memberships[key]['location_setting'],decision['location_setting'])
                    self.assertEqual(memberships[key]['review_status'],'Accepted')
                    if decision['location_setting'] == 'Other' and not decision['canonical_name']:
                        self.assertFalse(memberships[key]['place_id'])
                        self.assertEqual(certificates[key]['eligible_for_place_analytics'], 'false')
                    else:
                        self.assertTrue(memberships[key]['place_id'])
                elif row['location_setting']=='Uncertain':
                    self.assertEqual(memberships[key]['location_setting'],'Uncertain')
                    self.assertEqual(memberships[key]['place_id'],'')
                    self.assertEqual(certificates[key]['eligible_for_place_analytics'],'false')
                elif row["location_setting"] != "Other":
                    self.assertTrue(memberships[key]['place_id'])
                    # Accepted premises membership does not establish current
                    # trading: announced or closed stores remain on the map.
                    current=stores[key]['status'] in {'Active','Mapped'}
                    self.assertEqual(certificates[key]['eligible_for_place_analytics'],str(current).lower())
                if stores[key]['status'] in {'Opening Soon','Unknown','Temporarily Closed','Closed'}:
                    self.assertEqual(certificates[key]['eligible_for_analytics'],'false')
                    self.assertEqual(certificates[key]['eligible_for_place_analytics'],'false')

    def test_announced_centre_tenancy_is_mapped_but_not_current_competition(self):
        key=reviewed.ID_PREFIX+'au-zoom-optics-box-hill'
        stores={r['store_id']:r for r in intake.read_csv(ROOT/'data/optical_stores.csv')}
        memberships={r['store_id']:r for r in intake.read_csv(ROOT/'data/store_place_memberships.csv')}
        certificates={r['store_id']:r for r in intake.read_csv(ROOT/'data/store_certification.csv')}
        self.assertEqual(stores[key]['status'],'Opening Soon')
        self.assertTrue(stores[key]['coordinate_confidence'].startswith('Low'))
        self.assertEqual(memberships[key]['place_id'],'place-au-nsw-carmel-village-shopping-centre')
        self.assertEqual(certificates[key]['usable_for_network'],'true')
        self.assertEqual(certificates[key]['eligible_for_analytics'],'false')
        self.assertEqual(certificates[key]['eligible_for_place_analytics'],'false')


class IntakeTests(unittest.TestCase):
    def test_supplier_verification_and_nearby_different_name_do_not_accept(self):
        row=intake.candidate_rows([supplier()],"supplier-independent")[0]
        store=dict(store_id="existing",name="Different Optical",country="Australia",latitude="-33.86",longitude="151.2")
        self.assertEqual(intake.suggest(row,[store])["suggested_store_id"],"")
        self.assertNotIn("canonical_store_id",row)

    def test_ids_are_namespaced_and_invalid_coordinates_are_retained(self):
        source=supplier();source['lat']='not known'
        row=intake.candidate_rows([source],"supplier-independent")[0]
        self.assertEqual(row['candidate_id'],'supplier-independent:17')
        self.assertIn('Invalid source coordinates',intake.suggest(row,[])['suggestion_basis'])

    def test_decision_requires_known_canonical_evidence_and_unchanged_source(self):
        row=intake.candidate_rows([supplier()],"supplier-independent")[0]
        decision=dict(candidate_id=row['candidate_id'],source_record_hash=row['source_record_hash'],decision='Linked existing',canonical_store_id='existing',evidence_url='https://example.org/location',reviewed_at=date.today().isoformat(),reason='Exact practice identity and address')
        with self.assertRaises(ValueError):intake.apply_decisions([deepcopy(row)],[decision],set())
        result=intake.apply_decisions([deepcopy(row)],[decision],{'existing'})[0]
        self.assertEqual(result['review_status'],'Linked existing')
        changed=supplier();changed['address']='50 Another Road, Sydney NSW 2000'
        fresh=intake.candidate_rows([changed],"supplier-independent")
        result=intake.apply_decisions(fresh,[decision],{'existing'})[0]
        self.assertEqual(result['review_status'],'Needs review')
        self.assertEqual(result['canonical_store_id'],'')

    def test_rerun_retains_decisions_snapshot_and_rejected_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);out=root/'output'/'intake';source=root/'source.csv';stores=root/'stores.csv'
            rejected=supplier('false');rejected['id']='18'
            intake.write_csv(source,[supplier(),rejected],list(supplier()))
            canonical=dict(store_id='existing',name='Example Optometrists',country='Australia',latitude='-33.86',longitude='151.2')
            intake.write_csv(stores,[canonical],list(canonical))
            with patch.object(intake,'ROOT',root):
                first=intake.stage(source,out,'supplier-independent',stores)
                self.assertEqual(first['review_status'],{'Pending':1,'Source rejected':1})
                row=intake.read_csv(out/'review_queue.csv')[0]
                decision=dict(candidate_id=row['candidate_id'],source_record_hash=row['source_record_hash'],decision='Linked existing',canonical_store_id='existing',evidence_url='https://example.org/location',reviewed_at=date.today().isoformat(),reason='Same identity and address')
                intake.write_csv(out/'decisions.csv',[decision],intake.DECISION_FIELDS)
                before=(out/'decisions.csv').read_bytes()
                second=intake.stage(source,out,'supplier-independent',stores)
                self.assertEqual(second['review_status'],{'Linked existing':1,'Source rejected':1})
                self.assertEqual(before,(out/'decisions.csv').read_bytes())
                self.assertEqual(len(list(out.glob('source-*.csv'))),1)
                with self.assertRaises(ValueError):intake.stage(source,root/'data','supplier-independent',stores)


if __name__ == '__main__':unittest.main()
