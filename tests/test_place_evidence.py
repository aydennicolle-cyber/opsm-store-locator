"""Weak addresses and shared geography cannot establish property identity."""
import copy
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_retail_places as places_build


class PlaceEvidenceTests(unittest.TestCase):
    def place(self, name='Example Centre', **extra):
        row = dict(place_id=places_build.centre_place_id('Australia', 'VIC', name),
                   name=name, country='Australia', state='VIC', postcode='3000',
                   latitude=-37.8126, longitude=144.9630, address='19 High Street',
                   place_type='Shopping Centre', location_setting='Shopping Centre',
                   official_url='https://example.org/centre', aliases=[])
        return {**row, **extra}

    def store(self, address):
        return dict(country='Australia', state='VIC', postcode='3000',
                    latitude=-37.8126, longitude=144.9630, full_address=address)

    def test_country_road_and_intersection_are_not_tenancy_proof(self):
        weak = ['Australia', 'High Street', 'Corner High Street and Smith Road',
                'Cnr Mains Rd & McCullough St, Sunnybank QLD 4109']
        for address in weak:
            with self.subTest(address=address):
                self.assertIsNone(places_build.official_address_place_match(
                    self.store(address), [self.place(address=address)]))
        self.assertIsNone(places_build.official_address_place_match(
            self.store('111 High Street, Australia'), [self.place(address='High Street')]))

    def test_numbered_address_still_matches_with_unit_and_abbreviation(self):
        centre = self.place(address='19 High Street, Melbourne VIC 3000')
        self.assertIs(places_build.official_address_place_match(
            self.store('Shop 2, 19 High St, Melbourne VIC 3000'), [centre]), centre)
        for address in ['17-21 Market Street', '1A/17 Mitchell Drive', '250 Elizabeth Street']:
            with self.subTest(address=address):
                self.assertTrue(places_build.numbered_street_address(address))

    def test_street_number_substring_does_not_match(self):
        self.assertIsNone(places_build.official_address_place_match(
            self.store('19 High Street'), [self.place(address='9 High Street')]))

    def test_two_properties_with_same_address_are_ambiguous(self):
        first = self.place('North Building')
        second = self.place('South Building')
        self.assertIsNone(places_build.official_address_place_match(
            self.store('19 High Street'), [first, second]))

    def test_tenant_evidence_does_not_become_the_centres_official_website(self):
        evidence_url = 'https://retailer.example/locations/example-centre'
        for official_url in ('', 'https://centre.example/'):
            with self.subTest(official_url=official_url):
                centre = self.place(official_url=evidence_url)
                override = dict(place_id=centre['place_id'], canonical_name=centre['name'],
                                official_url=official_url, evidence_url=evidence_url,
                                verified_at='2026-10-04', reason='Named tenant premises')
                with patch.object(places_build, 'read_csv', return_value=[override]):
                    places_build.apply_canonical_place_overrides([centre], {})
                self.assertEqual(centre['official_url'], official_url)
                self.assertEqual(centre['source_url'], evidence_url)
                self.assertEqual(centre['source_date'], '2026-10-04')

    def test_shared_city_or_brand_does_not_establish_alias(self):
        examples = [("Melbourne's GPO", 'The Strand Melbourne'),
                    ('Liverpool Plaza', 'Westfield Liverpool'),
                    ('Box Hill Central North', 'Box Hill Central South')]
        with patch.object(places_build, 'reviewed_place_aliases', return_value=({}, {})):
            for candidate, existing in examples:
                with self.subTest(candidate=candidate):
                    # Generated aliases cannot supply their own verification.
                    self.assertFalse(places_build.reviewed_osm_place_match(
                        self.place(candidate), self.place(existing, aliases=[candidate])))

    def test_reviewed_alias_and_stable_remap_are_accepted(self):
        centre = self.place('Current Name')
        former = self.place('Former Name')
        with patch.object(places_build, 'reviewed_place_aliases', return_value=(
                {former['place_id']: centre['place_id']}, {})):
            self.assertTrue(places_build.reviewed_osm_place_match(former, centre))
        with patch.object(places_build, 'reviewed_place_aliases', return_value=(
                {}, {centre['place_id']: {'former-name'}})):
            self.assertTrue(places_build.reviewed_osm_place_match(former, centre))
            self.assertFalse(places_build.reviewed_osm_place_match(
                {**former, 'state': 'NSW'}, centre))

    def osm_pass(self, candidate_name, existing):
        payload = dict(fetched_at='2026-09-01', elements=[dict(type='node', id=123,
            lat=-37.8126, lon=144.9630, tags={'shop': 'mall', 'name': candidate_name,
            'website': 'https://example.org/property', 'addr:state': 'VIC'})])
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'osm.json'
            source.write_text(json.dumps(payload))
            with patch.object(places_build, 'OSM_DISCOVERY', [(source, 'Australia', 'au')]):
                return places_build.add_broad_osm_centres(existing)

    def test_spatial_candidate_is_preserved_without_mutating_accepted_places(self):
        existing = [self.place('The Strand Melbourne')]
        before = copy.deepcopy(existing)
        with patch.object(places_build, 'reviewed_place_aliases', return_value=({}, {})):
            leads = self.osm_pass("Melbourne's GPO", existing)
        self.assertEqual(existing, before)
        self.assertEqual(leads[0]['source_id'], 'osm-au-node-123')
        self.assertEqual(leads[0]['source_fetched_at'], '2026-09-01')
        self.assertEqual(leads[0]['review_status'], 'Unpromoted discovery lead')

    def test_ambiguous_reviewed_name_is_not_assigned_to_first_property(self):
        existing = [self.place('North Building'), self.place('South Building')]
        before = copy.deepcopy(existing)
        labels = {row['place_id']: {'shared-name'} for row in existing}
        with patch.object(places_build, 'reviewed_place_aliases', return_value=({}, labels)):
            leads = self.osm_pass('Shared Name', existing)
        self.assertEqual(existing, before)
        self.assertEqual(set(leads[0]['candidate_place_ids']), {r['place_id'] for r in existing})

    def test_distinct_arcade_is_not_removed_when_neighbour_is_added(self):
        existing = [self.place('The Block Arcade')]
        with patch.object(places_build, 'reviewed_place_aliases', return_value=({}, {})):
            leads = self.osm_pass('Collins Arcade', existing)
        self.assertEqual(leads, [])
        self.assertEqual({p['name'] for p in existing}, {'The Block Arcade', 'Collins Arcade'})
        self.assertTrue(all(not p['aliases'] for p in existing))

    def test_intermediate_aliases_with_one_reviewed_destination_are_not_ambiguous(self):
        existing = [self.place('Former Centre'), self.place('Current Centre')]
        labels = {row['place_id']: {'shared-name'} for row in existing}
        remaps = {existing[0]['place_id']: existing[1]['place_id']}
        with patch.object(places_build, 'reviewed_place_aliases', return_value=(remaps, labels)):
            leads = self.osm_pass('Shared Name', existing)
        self.assertEqual(leads, [])
        self.assertEqual(existing[0]['aliases'], [])
        self.assertEqual(existing[1]['aliases'], ['Shared Name'])

    def test_current_dataset_rejects_known_wrong_property_assignments(self):
        with (ROOT / 'data/store_place_memberships.csv').open() as f:
            memberships = {r['store_id']: r for r in csv.DictReader(f)}
        expected = {'opsm-2265': 'Cooleman Court', 'opsm-1295': 'Caneland Central',
                    'opsm-2968': 'Westfield North Lakes', 'opsm-1268': 'Sunnybank Plaza'}
        for store_id, name in expected.items():
            with self.subTest(store_id=store_id):
                self.assertEqual(memberships[store_id]['place_name'], name)
                self.assertEqual(memberships[store_id]['review_status'], 'Accepted')
        payload = json.loads((ROOT / 'data/retail_places.json').read_text())
        by_id = {r['place_id']: r for r in payload['places']}
        self.assertNotIn("Melbourne's GPO", by_id['place-au-vic-the-strand-melbourne']['aliases'])
        self.assertNotIn('Liverpool Plaza', by_id['place-au-nsw-westfield-liverpool']['aliases'])
        self.assertEqual(memberships['independent-other-optical-osm-au-node-11404319140']['place_id'],
                         'corridor-au-vic-vic-high-street')
        with (ROOT / 'data/optical_stores.csv').open() as f:
            for store in csv.DictReader(f):
                if store['full_address'] in {'Australia', 'New Zealand'}:
                    self.assertNotEqual(memberships[store['store_id']]['evidence_basis'],
                        'Official store address matches the authoritative canonical place address')


if __name__ == '__main__':
    unittest.main()
