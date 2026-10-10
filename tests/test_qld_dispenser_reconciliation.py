import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from reconcile_qld_dispensers import reconcile, source_hash, phone_key, locality_key


class DispenserReconciliationTests(unittest.TestCase):
    def snapshot(self, **changes):
        raw = dict(name='Example Optometry', address='1 Main Road', suburb='ASHMORE 4214',
                   postcode='4214', phone='07 5555 1234')
        raw.update(changes)
        return dict(source={}, records=[dict(source_id='qld:1', raw=raw, source_record_hash=source_hash(raw))])

    def store(self, **changes):
        row = dict(store_id='example:1', name='Example Optometry', full_address='1 Main Rd, Ashmore',
                   suburb='Ashmore', postcode='4214', phone='+61 7 5555 1234', country='Australia', status='Active')
        row.update(changes)
        return row

    def test_supported_candidate_never_promotes_or_changes_source(self):
        source = self.snapshot()
        result = reconcile(source, [self.store()])['records'][0]
        self.assertEqual(result['triage'], 'single_supported_candidate')
        self.assertEqual(result['promotion_status'], 'Unpromoted discovery lead')
        self.assertNotIn('canonical_store_id', result)
        self.assertEqual(result['raw']['suburb'], 'ASHMORE 4214')
        self.assertEqual(source['records'][0]['raw']['suburb'], 'ASHMORE 4214')

    def test_shared_phone_with_other_town_requires_review(self):
        result = reconcile(self.snapshot(), [self.store(), self.store(store_id='other:2', suburb='Brisbane', postcode='4000')])['records'][0]
        self.assertEqual(result['triage'], 'candidate_review')
        self.assertEqual(len(result['candidates']), 2)

    def test_phone_alone_does_not_establish_identity(self):
        result = reconcile(self.snapshot(), [self.store(name='Different Provider', suburb='Brisbane', postcode='4000')])['records'][0]
        self.assertEqual(result['triage'], 'candidate_review')

    def test_exact_name_can_find_incomplete_existing_record(self):
        result = reconcile(self.snapshot(), [self.store(state='QLD', suburb='', postcode='', phone='', full_address='Australia')])['records'][0]
        self.assertEqual(result['triage'], 'candidate_review')
        self.assertEqual(result['candidates'][0]['store_id'], 'example:1')

    def test_generic_name_and_locality_do_not_match_unrelated_practice(self):
        result = reconcile(self.snapshot(name='Ashmore Optical'), [self.store(name='Ashmore Eyecare', phone='')])['records'][0]
        self.assertEqual(result['triage'], 'no_candidate_found')

    def test_branch_suffixes_surface_incomplete_brand_without_assigning_branch(self):
        existing = self.store(name='My2020', state='QLD', suburb='', postcode='', phone='', full_address='Australia')
        for locality, postcode in [('Sunnybank', '4109'), ('Toowong', '4066'), ('Yeerongpilly', '4105')]:
            source = self.snapshot(name=f'My2020 Optometrists {locality}', suburb=locality, postcode=postcode)
            result = reconcile(source, [existing])['records'][0]
            self.assertEqual(result['triage'], 'candidate_review')
            self.assertEqual(result['candidates'][0]['store_id'], existing['store_id'])
            self.assertIn('same_distinctive_name_incomplete_location', result['candidates'][0]['signals'])
            self.assertEqual(result['promotion_status'], 'Unpromoted discovery lead')
            self.assertNotIn('canonical_store_id', result)

    def test_branch_suffix_does_not_override_known_other_locality_or_state(self):
        source = self.snapshot(name='My2020 Toowong', suburb='Toowong', postcode='4066')
        for changes in [dict(state='QLD', suburb='Yeerongpilly', postcode='4105'), dict(state='NSW', suburb='', postcode='')]:
            result = reconcile(source, [self.store(name='My2020', phone='', **changes)])['records'][0]
            self.assertEqual(result['triage'], 'no_candidate_found')

    def test_generic_incomplete_name_does_not_match_after_removing_locality(self):
        result = reconcile(self.snapshot(name='Ashmore Optical'), [self.store(name='Optometry', state='QLD', suburb='', postcode='', phone='')])['records'][0]
        self.assertEqual(result['triage'], 'no_candidate_found')

    def test_service_eligibility_and_non_premises_are_separate(self):
        result = reconcile(self.snapshot(name='Visiting Optical Service', address='https://example.org'), [])['records'][0]
        self.assertEqual(result['triage'], 'no_candidate_found')
        self.assertIn('non_premises_address_requires_review', result['eligibility_flags'])
        self.assertIn('retail_or_visiting_service_eligibility_requires_review', result['eligibility_flags'])

    def test_capture_integrity_is_required(self):
        source = self.snapshot()
        source['records'][0]['raw']['phone'] = 'changed'
        with self.assertRaises(AssertionError): reconcile(source, [])

    def test_phone_and_locality_normalization(self):
        self.assertEqual(phone_key('+61 7 5555 1234'), '0755551234')
        self.assertEqual(phone_key('1300 123 456'), '1300123456')
        self.assertEqual(locality_key('ASCOT 4007', '4007'), 'ascot')


if __name__ == '__main__':
    unittest.main()
