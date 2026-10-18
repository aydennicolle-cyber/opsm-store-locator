import copy
import csv
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from reconcile_environment_optics import reconcile


class OpticalEvidenceTests(unittest.TestCase):
    def payload(self, census=None, names=('Specsavers',)):
        return {'features': [], 'places': [{'place_id': 'centre', 'name': 'Centre',
            'features': {}, 'optical': census or [], 'observations': [
                {'source_id': str(i), 'name': name, 'role': 'Optical',
                 'source_url': 'https://example.org/store', 'observed_at': '2026-10-15'}
                for i, name in enumerate(names)]}]}

    def test_reviewed_duplicate_retains_raw_record_but_counts_one_outlet(self):
        p = self.payload([{'store_id': 'c', 'operator': 'City Optics'}], ('City Optics', 'City Optics'))
        place = p['places'][0]
        place['directory_records'] = copy.deepcopy(place['observations'])
        place['coverage'] = {'captured_listings': 2}
        place['features'] = {'brand:city optics': ['0', '1'], 'category:food': ['1']}
        reviews = [{'place_id': 'centre', 'source_id': str(i), 'store_id': 'c', 'decision': decision} for i, decision in enumerate(['pair', 'duplicate'])]
        result = reconcile(p, {'centre'}, reviews)[0]
        self.assertEqual(result['directory_listed_count'], 1)
        self.assertEqual(result['census_linked_count'], 1)
        self.assertEqual(result['unresolved_issue_count'], 0)
        self.assertEqual(len(place['directory_records']), 2)
        self.assertEqual(place['directory_records'][1]['scope_status'], 'suspected_duplicate')
        self.assertEqual(place['coverage']['captured_listings'], 2)
        self.assertEqual(place['coverage']['usable_listings'], 1)
        self.assertNotIn('category:food', place['features'])

    def test_directory_presence_without_census_link_is_searchable_not_network_outlet(self):
        p = self.payload(); reconcile(p, {'centre'}); place = p['places'][0]
        self.assertEqual(place['optical'], [])
        self.assertIn('operator:specsavers', place['features'])
        self.assertEqual(place['other_optical_presence'], 'present')
        self.assertEqual(place['optical_reconciliation']['directory_listed_count'], 1)
        self.assertEqual(place['optical_reconciliation']['review_count'], 1)

    def test_missing_directory_does_not_mean_zero_or_absence(self):
        p = self.payload(names=()); reconcile(p, set())
        r = p['places'][0]['optical_reconciliation']
        self.assertIsNone(r['directory_listed_count'])
        self.assertEqual(r['census_not_in_directory'], [])

    def test_multiple_outlets_are_not_collapsed_by_brand(self):
        census = [{'store_id': str(i), 'operator': 'Specsavers'} for i in range(2)]
        p = self.payload(census); before = copy.deepcopy(census); reconcile(p, {'centre'})
        r = p['places'][0]['optical_reconciliation']
        self.assertIsNone(r['directory_records'][0]['store_id'])
        self.assertEqual(p['places'][0]['optical'], before)

    def test_unique_same_place_pair_and_omission_do_not_create_closure(self):
        census = [{'store_id': 's', 'operator': 'Specsavers'}, {'store_id': 'o', 'operator': 'OPSM'}]
        p = self.payload(census); reconcile(p, {'centre'})
        r = p['places'][0]['optical_reconciliation']
        self.assertEqual(r['directory_records'][0]['store_id'], 's')
        self.assertEqual(r['census_not_in_directory'], ['o'])
        self.assertEqual(len(p['places'][0]['optical']), 2)

    def test_directory_bn_presence_does_not_pass_no_record_filter(self):
        p = self.payload(names=('Bailey Nelson',)); reconcile(p, {'centre'})
        self.assertEqual(p['places'][0]['bn_presence'], 'present')

    def test_alias_variants_match_only_within_accepted_place(self):
        p = self.payload([{'store_id': 'e', 'operator': 'Eye Concepts — Burwood'}], ('Eye Concepts Optometrist',))
        reconcile(p, {'centre'})
        self.assertEqual(p['places'][0]['optical_reconciliation']['directory_records'][0]['store_id'], 'e')

    def test_explicit_levels_preserve_two_separate_branches(self):
        p = self.payload([{'store_id':'a','operator':'Specsavers','name':'Parramatta Level 1'}, {'store_id':'b','operator':'Specsavers','name':'Parramatta Level 5'}], ('Specsavers - Level 1', 'Specsavers - Level 5'))
        reconcile(p, {'centre'})
        r = p['places'][0]['optical_reconciliation']
        self.assertEqual([x['store_id'] for x in r['directory_records']], ['a', 'b'])
        self.assertEqual(r['census_not_in_directory'], [])

    def test_unresolved_branch_is_not_hidden_by_same_operator(self):
        p = self.payload([{'store_id':'a','operator':'Specsavers'}, {'store_id':'b','operator':'Specsavers'}])
        reconcile(p, {'centre'})
        self.assertEqual(p['places'][0]['optical_reconciliation']['unmatched_census_count'], 2)

    def test_exact_branch_source_resolves_main_store_without_merging_concession(self):
        p = self.payload([{'store_id':'main','operator':'Sunglass Hut','source_url':'https://example.org/store'}, {'store_id':'concession','operator':'Sunglass Hut','source_url':'https://example.org/myer'}], ('Sunglass Hut',))
        reconcile(p, {'centre'})
        r = p['places'][0]['optical_reconciliation']
        self.assertEqual(r['directory_records'][0]['store_id'], 'main')
        self.assertEqual(r['census_not_in_directory'], ['concession'])

    def test_role_correction_preserves_original_capture_classification(self):
        p = self.payload(names=('Specsavers (G)',)); place = p['places'][0]
        place['place_id'] = 'place-au-vic-chadstone-shopping-centre'
        place['observations'][0].update(source_id='ac2e3c57-57a0-4763-a260-5f5afd886cd6', role='Other business or service')
        reconcile(p, {place['place_id']})
        self.assertEqual(place['observations'][0]['original_role'], 'Other business or service')
        self.assertEqual(place['optical_reconciliation']['directory_listed_count'], 1)
        self.assertEqual(place['optical'], [])

    def test_reviewed_centre_assignments_and_false_regional_place(self):
        data = Path(__file__).resolve().parents[1] / 'data'
        with (data / 'store_place_memberships.csv').open() as f:
            rows = {r['store_id']: r for r in csv.DictReader(f)}
        self.assertEqual(rows['specsavers-3487']['place_id'], 'place-au-unknown-gympie-central')
        self.assertEqual(rows['oscar-wylee-118']['place_id'], 'place-au-wa-claremont-quarter')
        self.assertEqual(rows['matthews-eyecare-nz-156549769']['location_setting'], 'High Street')
        self.assertEqual(rows['optical-superstore-63129']['place_id'], 'place-au-sa-westfield-west-lakes')
        for sid in ('au-seekers-fitzroy', 'au-gertrude-street-optical'):
            self.assertEqual(rows['independent-other-optical-reviewed-' + sid]['place_id'], 'corridor-au-vic-fitzroy-gertrude-street')
        places = json.loads((data / 'retail_places.json').read_text())['places']
        self.assertNotIn('place-nz-southland-southland', {p['place_id'] for p in places})
        self.assertNotIn('place-au-sa-westlakes-shopping-centre', {p['place_id'] for p in places})

    def test_reviewed_identity_requires_existing_accepted_membership(self):
        decision = {'place_id':'centre', 'source_id':'0', 'store_id':'s', 'decision':'pair'}
        p = self.payload(names=('Practice name',))
        reconcile(p, {'centre'}, [decision])
        self.assertIsNone(p['places'][0]['optical_reconciliation']['directory_records'][0]['store_id'])
        p = self.payload([{'store_id':'s','operator':'Network name'}], ('Practice name',))
        reconcile(p, {'centre'}, [decision])
        self.assertEqual(p['places'][0]['optical_reconciliation']['directory_records'][0]['store_id'], 's')

    def test_explained_omission_preserves_counts_and_raw_difference(self):
        p = self.payload([{'store_id':'s','operator':'Specsavers'}], ())
        decision = {'place_id':'centre','store_id':'s','decision':'retain_census',
                    'basis':'Official locator corroborates outlet', 'source_url':'https://example.org/s', 'review_date':'2026-10-15'}
        reconcile(p, {'centre'}, [decision])
        r = p['places'][0]['optical_reconciliation']
        self.assertEqual((r['census_linked_count'], r['directory_listed_count']), (1, 0))
        self.assertEqual(r['census_not_in_directory'], ['s'])
        self.assertEqual(r['unresolved_issue_count'], 0)
        self.assertEqual(r['explained_difference_count'], 1)
        self.assertEqual(r['status'], 'Explained source differences')

    def test_two_reviewed_records_cannot_claim_same_outlet(self):
        p = self.payload([{'store_id':'s','operator':'Network'}], ('Practice A','Practice B'))
        decisions = [{'place_id':'centre','source_id':str(i),'store_id':'s','decision':'pair'} for i in range(2)]
        with self.assertRaises(ValueError): reconcile(p, {'centre'}, decisions)

    def test_listing_hold_does_not_manufacture_outlet_or_resolve_gap(self):
        p = self.payload(names=('Unmatched practice',))
        decision = {'place_id':'centre','store_id':'','source_id':'0','decision':'hold',
                    'basis':'Official listing confirms address; premises coordinates still required',
                    'source_url':'https://example.org/s','review_date':'2026-10-15'}
        reconcile(p, {'centre'}, [decision])
        r = p['places'][0]['optical_reconciliation']
        self.assertEqual(r['unresolved_issue_count'], 1)
        self.assertFalse(r['review_items'][0]['resolved'])
        self.assertEqual(r['review_items'][0]['reason'], decision['basis'])
        self.assertEqual(r['census_linked_count'], 0)
        self.assertEqual(r['directory_listed_count'], 1)

    def test_scope_hold_keeps_issue_unresolved_and_preserves_outlet(self):
        p = self.payload([{'store_id':'s','operator':'Specsavers'}], ())
        decision = {'place_id':'centre','store_id':'s','decision':'hold',
                    'basis':'Precise street boundary remains unresolved',
                    'source_url':'https://example.org/s','review_date':'2026-10-15'}
        reconcile(p, {'centre'}, [decision])
        r = p['places'][0]['optical_reconciliation']
        self.assertEqual(r['unresolved_issue_count'], 1)
        self.assertFalse(r['review_items'][0]['resolved'])
        self.assertEqual(r['review_items'][0]['reason'], decision['basis'])
        self.assertEqual(r['census_linked_count'], 1)


if __name__ == '__main__':
    unittest.main()
