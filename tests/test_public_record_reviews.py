"""Reviewed identities must survive rebuilds without broadening their evidence."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from luc_record_reviews import apply_record_reviews, canonical_hash
from reviewed_store_facts import apply_public_facts
from build_local_coverage import locate


class PublicRecordReviews(unittest.TestCase):
    def csv_file(self, directory, row):
        path = Path(directory) / 'decisions.csv'
        with path.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=row)
            writer.writeheader(); writer.writerow(row)
        return path

    def review_fixture(self):
        store = dict(store_id='test-branch', retailer='Test Optical', country='Australia', name='Test Optical Suburb', full_address='Shop 1, 10 Main Road', latitude='-33.8', longitude='151.2')
        source = dict(source_id='chain:1', source_record_hash='source-hash', country='AU', outcome='Needs review')
        decision = dict(source_id='chain:1', source_record_hash='source-hash', decision='Linked existing', canonical_store_id=store['store_id'], canonical_record_hash=canonical_hash(store), evidence_url='https://example.org/branch', checked_at='2026-09-12', reason='Reviewed branch and same tenancy address')
        return store, source, decision

    def test_source_and_canonical_changes_require_new_review(self):
        store, source, decision = self.review_fixture()
        with tempfile.TemporaryDirectory() as d:
            path = self.csv_file(d, decision)
            apply_record_reviews([source], [store], path)
            self.assertEqual(source['canonical_store_id'], store['store_id'])
            with self.assertRaisesRegex(ValueError, 'Source changed'):
                apply_record_reviews([{**source, 'source_record_hash': 'changed'}], [store], path)
            with self.assertRaisesRegex(ValueError, 'Canonical identity changed'):
                apply_record_reviews([source], [{**store, 'full_address': 'Shop 2, 10 Main Road'}], path)

    def test_review_cannot_link_across_countries_or_assert_unresolved_identity(self):
        store, source, decision = self.review_fixture()
        with tempfile.TemporaryDirectory() as d:
            path = self.csv_file(d, decision)
            with self.assertRaisesRegex(ValueError, 'Cross-country'):
                apply_record_reviews([{**source, 'country': 'NZ'}], [store], path)
            path = self.csv_file(d, {**decision, 'decision': 'Needs review'})
            with self.assertRaisesRegex(ValueError, 'cannot assert'):
                apply_record_reviews([source], [store], path)

    def test_duplicate_requires_another_supplier_row(self):
        store, source, decision = self.review_fixture()
        decision.update(decision='Duplicate source listing', related_source_id='chain:1')
        with tempfile.TemporaryDirectory() as d:
            path = self.csv_file(d, decision)
            with self.assertRaisesRegex(ValueError, 'another source row'):
                apply_record_reviews([source], [store], path)

    def test_fact_repair_does_not_refresh_unreviewed_facts_or_replace_id(self):
        row = dict(store_id='old-source-id', name='Old name', full_address='New Zealand', status='Mapped', fetched_at='2025-01-01', latitude=-43.55, longitude=172.7)
        correction = dict(store_id=row['store_id'], name='Reviewed name', full_address='10 Example Road, Christchurch', evidence_url='https://example.org/location', verified_at='2026-09-12', reason='Official practice address confirmed')
        with tempfile.TemporaryDirectory() as d:
            path = self.csv_file(d, correction)
            apply_public_facts([row], path)
            self.assertEqual(row['store_id'], 'old-source-id')
            self.assertEqual((row['status'], row['fetched_at'], row['latitude']), ('Mapped', '2025-01-01', -43.55))
            self.assertEqual(row['full_address'], correction['full_address'])
            path = self.csv_file(d, {**correction, 'store_id': 'not-in-network'})
            with self.assertRaisesRegex(ValueError, 'Unknown'):
                apply_public_facts([row], path)
            path = self.csv_file(d, {**correction, 'full_address': 'New Zealand'})
            with self.assertRaisesRegex(ValueError, 'Unusable corrected address'):
                apply_public_facts([row], path)

    def test_reviewed_rebrand_preserves_source_identity_and_requires_known_network(self):
        store = dict(store_id='old-source-id', retailer='Independent / Other optical',
                     name='Previous brand', fetched_at='2025-01-01', status='Temporarily Closed')
        other = dict(store_id='existing-chain-store', retailer='Named Optical Network')
        correction = dict(store_id=store['store_id'], retailer=other['retailer'],
                          evidence_url='https://example.org/rebrand', verified_at='2026-09-12',
                          reason='Both operator pages identify the same rebranded premises')
        with tempfile.TemporaryDirectory() as d:
            apply_public_facts([store, other], self.csv_file(d, correction))
            self.assertEqual(store['retailer'], other['retailer'])
            self.assertEqual((store['store_id'], store['fetched_at'], store['status']),
                             ('old-source-id', '2025-01-01', 'Temporarily Closed'))
            with self.assertRaisesRegex(ValueError, 'Unknown reviewed retailer'):
                apply_public_facts([store, other], self.csv_file(d, {**correction, 'retailer': 'Invented network'}))
            with self.assertRaisesRegex(ValueError, 'lacks evidence'):
                apply_public_facts([store, other], self.csv_file(d, {**correction, 'evidence_url': ''}))

    def test_reviewed_affiliation_preserves_local_brand_source_and_existing_membership(self):
        store = dict(store_id='source-id', retailer='Independent / Other optical', name='Local Practice',
                     affiliations='provision', fetched_at='2025-01-01', status='Mapped')
        correction = dict(store_id=store['store_id'], affiliations='optical-company-network',
                          evidence_url='https://example.org/ownership', verified_at='2026-09-12',
                          reason='Operator explicitly names the corporate group; retain the local trading brand')
        with tempfile.TemporaryDirectory() as d:
            apply_public_facts([store], self.csv_file(d, correction))
        self.assertEqual(store['affiliations'], 'optical-company-network|provision')
        self.assertEqual((store['store_id'], store['retailer'], store['name'], store['fetched_at'], store['status']),
                         ('source-id', 'Independent / Other optical', 'Local Practice', '2025-01-01', 'Mapped'))

    def test_reviewed_affiliation_requires_known_id_and_public_evidence(self):
        store = dict(store_id='source-id', affiliations='')
        correction = dict(store_id='source-id', affiliations='invented-network', evidence_url='https://example.org',
                          verified_at='2026-09-12', reason='Source claim')
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, 'Unknown reviewed affiliation'):
                apply_public_facts([store], self.csv_file(d, correction))
            with self.assertRaisesRegex(ValueError, 'lacks evidence'):
                apply_public_facts([store], self.csv_file(d, {**correction, 'affiliations': 'optical-company-network', 'evidence_url': ''}))

    def test_rebranded_store_retains_original_source_certification(self):
        from build_data_health import source_id_for_store
        for key, expected in [('independent-other-optical-reviewed-test', 'reviewed-independent-practices'),
                              ('independent-other-optical-osm-test', 'osm-opticians'),
                              ('optical-warehouse-test', 'optical-warehouse-au')]:
            store = dict(store_id=key, retailer='The Optical Company', country='Australia', affiliations='')
            self.assertEqual(source_id_for_store(store), expected)

    def test_street_name_in_id_does_not_supply_a_pipeline_locality(self):
        common = dict(country='Australia', state='VIC', name='Toorak Road', latitude=-37.84, longitude=145.0)
        south_yarra = dict(common, place_id='corridor-au-vic-south-yarra-toorak-road', locality='South Yarra')
        toorak = dict(common, place_id='corridor-au-vic-toorak-toorak-road', locality='Toorak')
        row = dict(country='AU', region='VIC', area='Toorak', venue='Toorak Rd')
        result = locate(row, [south_yarra, toorak], [])
        self.assertEqual(result['place_id'], toorak['place_id'])

    def test_public_phone_enrichment_preserves_identity_status_and_source_age(self):
        row = dict(store_id='existing-practice', phone='', name='Practice', status='Mapped',
                   fetched_at='2025-01-01', latitude=-33.8, longitude=151.2)
        original = dict(row)
        correction = dict(store_id=row['store_id'], phone='(02) 9476 1475',
                          evidence_url='https://example.org/contact', verified_at='2026-09-12',
                          reason='Official practice contact supplies this business number')
        with tempfile.TemporaryDirectory() as d:
            apply_public_facts([row], self.csv_file(d, correction))
            self.assertEqual(row['phone'], correction['phone'])
            for field in ('store_id', 'name', 'status', 'fetched_at', 'latitude', 'longitude'):
                self.assertEqual(row[field], original[field])
            # A blank cell does not erase a known contact, and a masked search
            # snippet must not become a callable public phone number.
            apply_public_facts([row], self.csv_file(d, {**correction, 'phone': '', 'services': 'Eyewear'}))
            self.assertEqual(row['phone'], correction['phone'])
            for invalid in ('(02) 94...', '(02) 9476...', 'Call our store', 'https://example.org', '12345'):
                with self.subTest(phone=invalid), self.assertRaisesRegex(ValueError, 'Invalid public phone'):
                    apply_public_facts([dict(original)], self.csv_file(d, {**correction, 'phone': invalid}))

    def test_reviewed_url_role_correction_preserves_raw_evidence_and_trading_date(self):
        original = dict(store_id='practice', official_url='https://supplier.example/stockists',
                        directory_url='https://maps.example/practice', source_url='https://supplier.example/stockists',
                        fetched_at='2025-01-01', status='Active', status_verified_at='2025-02-01',
                        name='Optical Practice', full_address='10 Main Street', phone='0290000000')
        correction = dict(store_id='practice', clear_fields='official_url',
                          evidence_url='https://supplier.example/stockists', verified_at='2026-09-12',
                          reason='Supplier stockist directory is not this practice website')
        with tempfile.TemporaryDirectory() as d:
            store = dict(original)
            apply_public_facts([store], self.csv_file(d, correction))
            self.assertEqual(store['official_url'], '')
            for field in original.keys() - {'official_url'}:
                self.assertEqual(store[field], original[field])
            # A subsequent unrelated review or empty cell cannot erase a known URL.
            store = dict(original)
            apply_public_facts([store], self.csv_file(d, {**correction, 'clear_fields': '', 'official_url': '', 'phone': '0290000001'}))
            self.assertEqual(store['official_url'], original['official_url'])

    def test_url_removal_requires_evidence_and_cannot_erase_identity_or_source(self):
        store = dict(store_id='practice', official_url='https://supplier.example', source_url='https://source.example')
        base = dict(store_id='practice', clear_fields='official_url', evidence_url='https://supplier.example',
                    verified_at='2026-09-12', reason='Reviewed source role')
        with tempfile.TemporaryDirectory() as d:
            for field in ('store_id', 'source_url', 'fetched_at', 'full_address', 'status', 'phone'):
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Unsupported reviewed field removal'):
                    apply_public_facts([dict(store)], self.csv_file(d, {**base, 'clear_fields': field}))
            with self.assertRaisesRegex(ValueError, 'Conflicting reviewed URL'):
                apply_public_facts([dict(store)], self.csv_file(d, {**base, 'official_url': 'https://replacement.example'}))
            with self.assertRaisesRegex(ValueError, 'lacks evidence'):
                apply_public_facts([dict(store)], self.csv_file(d, {**base, 'evidence_url': ''}))
            with self.assertRaisesRegex(ValueError, 'Invalid public URL'):
                apply_public_facts([dict(store)], self.csv_file(d, {**base, 'directory_url': 'not a URL'}))

    def test_reviewed_address_repair_and_separate_membership_evidence(self):
        def rows(name):
            with (ROOT / 'data' / name).open() as f:
                return {r['store_id']: r for r in csv.DictReader(f)}
        stores = rows('optical_stores.csv'); memberships = rows('store_place_memberships.csv')
        cert = rows('store_certification.csv')
        key = 'independent-other-optical-osm-ne-node-4757538924'
        self.assertIn('1025 Ferry Road', stores[key]['full_address'])
        self.assertEqual(stores[key]['location_type'], 'Unclassified')
        # The raw classification stays intact; later explicit property evidence
        # establishes membership independently of the address correction.
        self.assertEqual(memberships[key]['location_setting'], 'Other')
        self.assertEqual(memberships[key]['place_id'], 'place-nz-canterbury-ferrymead-the-sails')
        self.assertEqual(memberships[key]['usable_for_network'], 'true')
        self.assertEqual(cert[key]['eligible_for_analytics'], 'true')
        self.assertEqual(cert[key]['eligible_for_place_analytics'], 'true')
        self.assertNotIn(key, rows('place_review.csv'))
        # A later visual review establishes standalone setting, not membership.
        unresolved = 'independent-other-optical-reviewed-nz-papamoa-optometrists'
        self.assertIn('25 Domain Road', stores[unresolved]['full_address'])
        self.assertEqual(memberships[unresolved]['location_setting'], 'Other')
        self.assertEqual(memberships[unresolved]['review_status'], 'Accepted')
        self.assertIn('25 Domain', rows('store_place_overrides.csv')[unresolved]['evidence_basis'])
        self.assertEqual(memberships[unresolved]['place_id'], '')
        self.assertEqual(cert[unresolved]['eligible_for_analytics'], 'true')
        self.assertEqual(cert[unresolved]['eligible_for_place_analytics'], 'false')
        self.assertNotIn(unresolved, rows('place_review.csv'))
        # An eyewear retailer inside a medical centre is still included.
        medical = 'independent-other-optical-reviewed-nz-frith-laird-manurewa'
        self.assertEqual(memberships[medical]['location_setting'], 'Other')
        self.assertEqual(cert[medical]['eligible_for_analytics'], 'true')

    def test_aldinga_uses_corrected_reference_and_preserves_existing_place_id(self):
        with (ROOT / 'data/store_place_memberships.csv').open() as f:
            members = {r['store_id']: r for r in csv.DictReader(f)}
        with (ROOT / 'data/optical_stores.csv').open() as f:
            stores = {r['store_id']: r for r in csv.DictReader(f)}
        key = 'independent-other-optical-provision-121963'
        self.assertEqual(members[key]['place_id'], 'place-au-unknown-aldinga-central-shopping-centre')
        self.assertAlmostEqual(float(stores[key]['longitude']), 138.4598936)
        self.assertTrue(stores[key]['coordinate_confidence'].startswith('Low'))
        places = json.loads((ROOT / 'data/retail_places.json').read_text())['places']
        self.assertNotIn('place-au-sa-aldinga-shopping-centre', {p['place_id'] for p in places})


if __name__ == '__main__':
    unittest.main()
