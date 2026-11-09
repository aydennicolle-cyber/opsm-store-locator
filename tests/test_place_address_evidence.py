import unittest

from scripts.build_retail_environments import place_address


class PlaceAddressEvidenceTests(unittest.TestCase):
    def test_profile_address_replaces_tenant_address_without_advancing_dates(self):
        raw = {'address': 'Shop AG26, 52 Soldiers Parade'}
        profile = {'display_address': '52 Soldiers Parade', 'checked_at': '2026-10-10',
                   'extent_evidence': {'source_url': 'https://example.org/about',
                                       'source_date': None, 'checked_at': '2026-10-08'}}
        result = place_address(raw, profile)
        self.assertEqual(result['address'], '52 Soldiers Parade')
        self.assertEqual(result['address_evidence']['checked_at'], '2026-10-08')
        self.assertIsNone(result['address_evidence']['source_date'])
        self.assertEqual(raw['address'], 'Shop AG26, 52 Soldiers Parade')

    def test_tenant_address_is_held_without_stripping_unit_and_guessing(self):
        result = place_address({'address': 'Shop 1, Main Street'}, {})
        self.assertEqual(result['address'], '')
        self.assertEqual(result['address_evidence'], {})
        self.assertIn('withheld', result['address_note'])

    def test_general_record_date_is_not_an_address_check(self):
        result = place_address({'address': 'Main Street', 'source_date': '2026-10-25'}, {})
        self.assertEqual(result['address_evidence']['checked_at'], '')
        self.assertIsNone(result['address_evidence']['source_date'])
        self.assertEqual(result['address_evidence']['record_date'], '2026-10-25')
        self.assertIn('not recorded', result['address_evidence']['basis'])

    def test_street_reference_uses_identity_not_tenant_building_number(self):
        raw = dict(location_setting='High Street', name='Dean Street', locality='Albury',
                   state='NSW', address='511-517 Dean St, Shop 2, Albury', source_date='2026-09-02')
        result = place_address(raw, {})
        self.assertEqual(result['address'], 'Dean Street, Albury, NSW')
        self.assertIn('not a building address', result['address_evidence']['basis'])
        self.assertEqual(result['address_evidence']['checked_at'], '')
        self.assertIsNone(result['address_evidence']['source_date'])
        self.assertEqual(result['address_evidence']['record_date'], '2026-09-02')
        self.assertIn('511-517', raw['address'])
        # Existing independently supplied profile addresses take precedence.
        self.assertEqual(place_address(raw, {'display_address': 'Dean Street retail precinct'})['address'],
                         'Dean Street retail precinct')

    def test_missing_locality_or_nonstreet_does_not_gain_invented_reference(self):
        for raw in [dict(location_setting='High Street', name='Main Street'),
                    dict(location_setting='Shopping Centre', name='Centre', locality='Albury')]:
            self.assertEqual(place_address(raw, {})['address'], '')
