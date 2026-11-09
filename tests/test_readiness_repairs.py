"""Regressions for evidence recovery without changing identity or review dates."""
import sys
import csv
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_retail_places as places
import build_market_intelligence as market
import audit_centre_recognition as recognition
import build_optical_network as network


class ReadinessRepairsTests(unittest.TestCase):
    def test_reviewed_region_survives_source_reload_without_refreshing_original_capture(self):
        from reviewed_store_facts import apply_public_facts
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'facts.csv'
            path.write_text(
                'store_id,state,evidence_url,verified_at,reason\n'
                'branch,Marlborough,https://example.org/council,2026-09-03,Council confirms region\n')
            for _ in range(2):
                store = dict(store_id='branch', retailer='OPSM', country='New Zealand',
                             state='Nelson', full_address='70 Market St, Blenheim, NLS, 7201',
                             latitude=-41.5131, longitude=173.95649,
                             status='Active', fetched_at='2026-09-01')
                original = dict(store)
                apply_public_facts([store], path)
                self.assertEqual(store['state'], 'Marlborough')
                for field in ('store_id', 'full_address', 'latitude', 'longitude', 'status', 'fetched_at'):
                    self.assertEqual(store[field], original[field])
                self.assertEqual(store['public_facts_verified_at'], '2026-09-03')

    def test_address_only_review_preserves_identity_and_coordinate_evidence(self):
        from build_retail_environments import place_address
        place = dict(place_id='centre', name='Centre', aliases=[], latitude=-35.1,
                     longitude=149.1, coordinate_verified_at='2026-09-01')
        row = dict(place_id='centre', canonical_name='Centre', address='Corner A and B Streets',
                   evidence_url='https://example.org/identity', verified_at='2026-09-02',
                   reason='Original identity review', address_checked_at='2026-10-25',
                   address_evidence_url='https://example.org/visit',
                   address_basis='Corner address confirmed; no point or tenant review.')
        for _ in range(2):
            places.apply_canonical_place_overrides([place], {}, rows=[row])
            evidence = place_address(place, {})['address_evidence']
            self.assertEqual(evidence['checked_at'], '2026-10-25')
            self.assertEqual(evidence['source_url'], row['address_evidence_url'])
            self.assertEqual(evidence['basis'], row['address_basis'])
            self.assertIsNone(evidence['source_date'])
            self.assertEqual(place['source_date'], '2026-09-02')
            self.assertEqual(place['source_url'], row['evidence_url'])
            self.assertEqual(place['coordinate_verified_at'], '2026-09-01')
            self.assertEqual((place['latitude'], place['longitude']), (-35.1, 149.1))
        with self.assertRaisesRegex(ValueError, 'Invalid address review date'):
            places.apply_canonical_place_overrides([place], {}, rows=[dict(row, address_checked_at='2026-02-30')])

    def test_historical_address_dates_and_limits_reach_profile_without_refreshing_source(self):
        from build_retail_environments import place_address
        place = dict(place_id='historic-centre', name='Historic Centre', aliases=[])
        row = dict(place_id='historic-centre', canonical_name='Historic Centre',
                   address='210 Auburn Street', evidence_url='https://example.org/sale',
                   verified_at='2026-10-26', address_source_date='2019-05-21',
                   reason='Historical sale listing; not current tenant verification.')
        for _ in range(2):
            places.apply_canonical_place_overrides([place], {}, rows=[row])
            evidence = place_address(place, {})['address_evidence']
            self.assertEqual(evidence['source_date'], '2019-05-21')
            self.assertEqual(evidence['checked_at'], '2026-10-26')
            self.assertEqual(evidence['basis'], row['reason'])
        places.apply_canonical_place_overrides([place], {}, rows=[dict(row, address_source_date='')])
        self.assertIsNone(place_address(place, {})['address_evidence']['source_date'])
        with self.assertRaisesRegex(ValueError, 'Invalid address source date'):
            places.apply_canonical_place_overrides([place], {}, rows=[dict(row, address_source_date='2019-02-30')])

    def test_source_refresh_cannot_overwrite_reviewed_public_facts(self):
        store = dict(store_id='reviewed-branch', retailer='Sunglass Hut',
                     official_url='https://example.org/old', fetched_at='2026-09-01')
        class StopAfterFacts(Exception):
            pass
        def source_refresh(stores, remaps):
            stores[0].update(official_url='https://example.org/raw', services='Raw service')
        def inspect_review(stores):
            self.assertEqual(stores[0]['official_url'], 'https://example.org/current')
            self.assertEqual(stores[0]['services'], 'Reviewed service')
            self.assertEqual(stores[0]['public_facts_verified_at'], '2026-09-03')
            self.assertEqual(stores[0]['fetched_at'], '2026-09-01')
            raise StopAfterFacts
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'store_public_fact_overrides.csv').write_text(
                'store_id,official_url,services,evidence_url,verified_at,reason\n'
                'reviewed-branch,https://example.org/current,Reviewed service,https://example.org/current,2026-09-03,Explicit operator correction\n')
            with patch.object(network, 'DATA_DIR', path), \
                 patch.object(network, 'read_freshness', return_value={}), \
                 patch.object(network, 'load_stores', return_value=[store]), \
                 patch.object(network, 'identity_remaps', return_value={}), \
                 patch.object(network, 'refresh_canonical', side_effect=source_refresh), \
                 patch.object(network, 'refresh_oakley_canonical'), \
                 patch.object(network, 'apply_coordinate_overrides', side_effect=inspect_review):
                with self.assertRaises(StopAfterFacts):
                    network.main()

    def test_generic_city_name_is_not_explicit_centre_evidence(self):
        store = dict(name='City Specs — Fairfield', suburb='Fairfield', state='NSW', country='Australia')
        centre = dict(venue_name='Neeta City Shopping Centre', suburb='Fairfield', state='NSW', country='Australia')
        self.assertFalse(recognition.explicit_place_name_overlap(store, centre))
        store['name'] = 'City Specs — Neeta City'
        self.assertTrue(recognition.explicit_place_name_overlap(store, centre))

    def test_registry_address_requires_existing_identity_and_preserves_uncertain_dates(self):
        row = dict(venue_id='raw', state='NSW', street_address='253 Pacific Highway',
                   source_url='https://example.org/about', source_date='2026-07-23')
        place = dict(place_id='canonical', state='NSW', location_setting='Shopping Centre',
                     address='', latitude=-30, longitude=153)
        with patch.object(places, 'read_csv', return_value=[row]):
            places.recover_registered_addresses([place], {})
            self.assertEqual(place['address'], '')
            places.recover_registered_addresses([place], {'raw': 'canonical'})
            self.assertEqual(place['address'], '253 Pacific Highway')
            self.assertEqual(place['address_evidence']['record_date'], '2026-07-23')
            self.assertEqual(place['address_evidence']['checked_at'], '')
            self.assertIsNone(place['address_evidence']['source_date'])
            self.assertEqual((place['latitude'], place['longitude']), (-30, 153))
            place['address'] = 'Reviewed address'
            places.recover_registered_addresses([place], {'raw': 'canonical'})
            self.assertEqual(place['address'], 'Reviewed address')
        place['address'] = ''
        conflict = dict(row, street_address='Different address')
        with patch.object(places, 'read_csv', return_value=[row, conflict]):
            places.recover_registered_addresses([place], {'raw': 'canonical'})
            self.assertEqual(place['address'], '')
        with patch.object(places, 'read_csv', return_value=[dict(row, street_address='Shop 1, 253 Pacific Highway')]):
            places.recover_registered_addresses([place], {'raw': 'canonical'})
            self.assertEqual(place['address'], '')

    def test_new_eyewear_shop_numbers_do_not_establish_centres(self):
        for brand in ('AM Eyewear', 'Valley Eyewear', 'The Eye Piece'):
            store = dict(retailer=brand, name=brand, country='Australia', state='NSW', suburb='Sydney',
                         full_address='Shop 1, 10 Hunter Street, Sydney NSW 2000')
            result = network.classify(store)
            self.assertEqual(result['location_type'], 'Main Street / Street-front')
            self.assertEqual(result['venue_id'], '')
            self.assertEqual(result['classification_confidence'], 'Medium')
            # A unit alone remains insufficient. Explicit centre names still work.
            store['full_address'] = 'Shop 1, Sydney NSW 2000'
            self.assertEqual(network.classify(store)['location_type'], 'Unclassified')
            store['full_address'] = 'Shop 1, Westfield Bondi Junction, 500 Oxford Street, Bondi Junction NSW 2022'
            self.assertEqual(network.classify(store)['location_type'], 'Shopping Centre')

    def test_property_address_recovery_preserves_ids_aliases_and_reference_limits(self):
        root = Path(__file__).resolve().parents[1]
        records = {r['place_id']: r for r in json.loads((root / 'data/retail_places.json').read_text())['places']}
        geelong = records['place-au-vic-westfield-bay-city']
        self.assertEqual(geelong['name'], 'Westfield Geelong')
        self.assertIn('Westfield Bay City', geelong['aliases'])
        self.assertEqual(geelong['address'], '95 Malop Street, Geelong VIC 3220')
        innaloo = records['place-au-wa-westfield-innaloo']
        self.assertEqual(innaloo['locality'], 'Innaloo')
        self.assertEqual(innaloo['address'], 'Ellen Stirling Boulevard, Innaloo WA 6018')
        chermside = records['place-au-qld-westfield-chermside']
        self.assertEqual(chermside['address'], 'Cnr Gympie & Hamilton Rds, Chermside QLD 4032')
        for place in (geelong, innaloo, chermside):
            self.assertEqual(place['address_evidence']['checked_at'], '2026-10-25')
            self.assertIsNone(place['address_evidence']['source_date'])
        self.assertIn('Southland', records['place-au-vic-westfield-southland']['aliases'])
        self.assertNotIn('place-au-vic-westfield-geelong', records)
        payload = json.loads((root / 'data/retail_places.json').read_text())
        self.assertEqual(payload['place_id_remaps']['place-au-vic-westfield-geelong'], geelong['place_id'])
        with (root / 'data/store_place_memberships.csv').open() as stream:
            memberships = {r['store_id']: r for r in csv.DictReader(stream)}
        for sid in ('opsm-1485', 'oscar-wylee-50', 'specsavers-3314', 'sunglass-hut-B766', 'sunglass-hut-B860'):
            self.assertEqual(memberships[sid]['place_id'], geelong['place_id'])

    def test_mixed_use_tenants_do_not_become_conventional_centres(self):
        root = Path(__file__).resolve().parents[1]
        records = {r['place_id']: r for r in json.loads((root / 'data/retail_places.json').read_text())['places']}
        with (root / 'data/store_place_memberships.csv').open() as stream:
            memberships = {r['store_id']: r for r in csv.DictReader(stream)}
        for sid, pid in [('sunglass-hut-B668', 'place-au-vic-crown-melbourne'),
                         ('sunglass-hut-B905', 'place-au-qld-sirocco-mooloolaba'),
                         ('sunglass-hut-B636', 'place-nz-otago-town-pier-building')]:
            self.assertEqual(memberships[sid]['place_id'], pid)
            self.assertEqual(memberships[sid]['review_status'], 'Accepted')
            self.assertEqual(records[pid]['location_setting'], 'Other')
            self.assertEqual(records[pid]['coordinate_confidence'], 'Low')
            self.assertEqual(records[pid]['coordinate_reference_store_id'], sid)

    def test_recognition_cannot_recreate_reviewed_noncentre_or_closed_business_labels(self):
        common = dict(latitude='-27', longitude='153', state='QLD', suburb='Brisbane',
                      postcode='4000', location_type='Shopping Centre', status='Active')
        stores = [dict(common, store_id='reviewed-street', venue_id='retailer-label', venue_name='Optiko'),
                  dict(common, store_id='closed', venue_id='closed-label', venue_name='Closed shop', status='Closed'),
                  dict(common, store_id='tenant', venue_id='actual-centre', venue_name='Actual Centre')]
        registry = [dict(venue_id='independent-property', latitude='-27', longitude='153')]
        result = recognition.build_known_centres(stores, registry, {'reviewed-street'})
        self.assertEqual({r['venue_id'] for r in result}, {'actual-centre', 'independent-property'})

    def test_readiness_register_includes_challenges_to_accepted_memberships(self):
        root = Path(__file__).resolve().parents[1]
        register = json.loads((root / 'docs/OPTICAL_READINESS_REGISTER.json').read_text())
        with (root / 'data/centre_recognition_review.csv').open() as stream:
            candidates = list(csv.DictReader(stream))
        issues = {r['subject_id']: r for r in register['issues'] if r['kind'] == 'recognition'}
        self.assertEqual(set(issues), {r['store_id'] for r in candidates})
        for row in candidates:
            issue = issues[row['store_id']]
            if row['priority'] == 'High':
                self.assertEqual(issue['priority'], 'High')
            self.assertTrue(issue['candidate_only'])
        self.assertIn('centre_recognition_review.csv', register['input_hashes'])

    def test_named_street_venue_is_not_promoted_to_a_shopping_centre(self):
        stores = [dict(venue_id='street-venue', location_type='Main Street / Street-front'),
                  dict(venue_id='office-venue', location_type='Other')]
        with patch.object(market, 'read_csv', return_value=[]):
            self.assertEqual(market.build_centres(stores), [])

    def test_retired_identity_suppression_is_safe_after_full_upstream_rebuild(self):
        row = dict(place_id='retired', source_venue_ids='old', reason='Ambiguous historical label',
                   evidence_url='https://example.org/review', verified_at='2026-09-03')
        stores = [dict(store_id='s', venue_id='old')]
        with patch.object(places, 'read_csv', return_value=[row]):
            with self.assertRaises(ValueError):
                places.apply_place_suppressions([], {}, stores, {})
            result = places.apply_place_suppressions([], {}, stores, {'s': {'place_id': 'accepted'}})
            self.assertTrue(result[0]['already_absent'])
            self.assertEqual(result[0]['source_venue_ids'], ['old'])
            with self.assertRaises(ValueError):
                places.apply_place_suppressions([], {'old': 'unexplained-live-target'}, stores, {'s': {}})

    def test_rebuilt_memberships_keep_concession_and_property_identities(self):
        data = Path(__file__).resolve().parents[1] / 'data'
        with (data / 'store_place_memberships.csv').open() as stream:
            members = {r['store_id']: r for r in csv.DictReader(stream)}
        expected = {'sunglass-hut-AU3395': 'place-au-unknown-the-district-docklands',
                    'sunglass-hut-B761': 'place-au-unknown-skygate-dfo',
                    'sunglass-hut-C279': 'place-au-wa-dfo-perth',
                    'sunglass-hut-B868': 'place-au-nsw-bankstown-central',
                    'sunglass-hut-AU4613': 'place-au-wa-clarkson-ocean-keys-shopping-centre',
                    'opsm-1360': 'place-au-vic-westfield-fountain-gate',
                    'sunglass-hut-B826': 'place-au-vic-westfield-fountain-gate',
                    'opsm-1339': 'place-au-qld-clifford-gardens-shopping-centre',
                    'specsavers-3572': 'place-au-qld-clifford-gardens-shopping-centre',
                    'sunglass-hut-B812': 'place-au-sa-myer-centre-adelaide',
                    '1001-optometry-7240046': 'place-au-vic-box-hill-central-south',
                    'sunglass-hut-B671': 'place-au-nsw-queen-victoria-building',
                    'sunglass-hut-Q101': 'place-nz-auckland-manawa-bay',
                    'sunglass-hut-B657': 'place-nz-canterbury-the-crossing',
                    'sunglass-hut-F986': 'place-au-wa-enex-perth',
                    'sunglass-hut-B768': 'place-au-qld-harbour-town-gold-coast'}
        for sid, pid in expected.items():
            self.assertEqual(members[sid]['place_id'], pid)
            self.assertEqual(members[sid]['review_status'], 'Accepted')
        records = {r['place_id']: r for r in json.loads((data / 'retail_places.json').read_text())['places']}
        self.assertNotIn('place-au-qld-dfo-brisbane', records)
        self.assertIn('place-au-unknown-skygate-dfo', records)
        self.assertNotIn('place-au-vic-fountain-gate-shopping-centre', records)
        fountain = records['place-au-vic-westfield-fountain-gate']
        self.assertEqual(fountain['address'], '25-55 Overland Drive, Fountain Gate VIC 3805')
        remaps = json.loads((data / 'retail_places.json').read_text())['place_id_remaps']
        self.assertEqual(remaps['place-au-vic-fountain-gate-shopping-centre'], fountain['place_id'])
        for retired in ('corridor-au-qld-newtown-james-street', 'corridor-au-qld-toowoomba-james-street'):
            self.assertNotIn(retired, records)
            self.assertNotIn(retired, remaps)  # A street is not an alias of a centre.
        self.assertIn('place-au-vic-box-hill-central-north', records)
        self.assertEqual(records['place-au-vic-box-hill-central-south']['address'], '1 Main Street, Box Hill VIC 3128')
        qvb = records['place-au-nsw-queen-victoria-building']
        self.assertEqual(qvb['coordinate_confidence'], 'Low')
        self.assertEqual(qvb['coordinate_reference_store_id'], 'sunglass-hut-B671')
        self.assertEqual(qvb['address'], '455 George St, Sydney NSW 2000')
        manawa = records['place-nz-auckland-manawa-bay']
        self.assertIn('Manawa Bay', manawa['aliases'])
        self.assertEqual(manawa['coordinate_method'], 'Operator-linked property map')
        self.assertEqual((manawa['latitude'], manawa['longitude']), (-36.9972548, 174.8003402))
        # Same brand of outlet property is not evidence of the same place.
        adelaide = records['place-au-unknown-harbour-town']
        gold_coast = records['place-au-qld-harbour-town-gold-coast']
        self.assertIn('harbourtownadelaide.com.au', adelaide['official_url'])
        self.assertNotEqual(adelaide['place_id'], gold_coast['place_id'])
        self.assertEqual(gold_coast['address'], '147-189 Brisbane Road, Biggera Waters QLD 4216')
        self.assertEqual(gold_coast['coordinate_confidence'], 'Low')
        self.assertEqual(records['place-au-wa-enex-perth']['address'], '100 St Georges Terrace, Perth WA 6000')
        self.assertEqual(records['place-nz-canterbury-the-crossing']['address'], '166 Cashel Street, Christchurch')

    def test_official_address_recovery_keeps_point_and_original_check_date(self):
        row = dict(place_id='p', canonical_name='Existing centre', official_url='https://example.org/centre',
                   last_verified_at='2026-09-03', latitude='-37', longitude='145', address='Corner First and Second Roads')
        existing = dict(place_id='p', name='Existing centre', aliases=[], address='', latitude=-36, longitude=144)
        with patch.object(places, 'read_csv', return_value=[row]):
            places.add_official_retail_places([existing])
        self.assertEqual(existing['address'], row['address'])
        self.assertEqual(existing['address_evidence']['checked_at'], '2026-09-03')
        self.assertIsNone(existing['address_evidence']['source_date'])
        self.assertEqual((existing['latitude'], existing['longitude']), (-36, 144))
        existing['address'] = 'Previously reviewed address'
        with patch.object(places, 'read_csv', return_value=[row]):
            places.add_official_retail_places([existing])
        self.assertEqual(existing['address'], 'Previously reviewed address')

    def test_store_derived_reference_does_not_claim_fresh_coordinate_verification(self):
        store = dict(store_id='s', country='Australia', state='VIC', suburb='Suburb', postcode='3000',
                     full_address='Shop 1, Example Centre', latitude='-37', longitude='145')
        override = dict(location_setting='Shopping Centre', canonical_name='Example Centre', place_type='Shopping Centre',
                        official_url='https://example.org/store', source_date='2026-09-02', confidence='High', evidence_basis='Named centre')
        result = places.create_place_from_override(store, override)
        self.assertEqual(result['coordinate_reference_store_id'], 's')
        self.assertIn('does not establish', result['coordinate_reason'])
        self.assertNotIn('coordinate_verified_at', result)
        self.assertNotIn('coordinate_confidence', result)
        self.assertEqual(result['source_date'], '2026-09-02')


if __name__ == '__main__':
    unittest.main()
