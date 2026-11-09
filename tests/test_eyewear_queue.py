"""Admission boundaries for the ongoing eyewear reconciliation."""
import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EyewearReconciliationTests(unittest.TestCase):
    def test_verified_outlets_keep_source_identity_and_service_uncertainty(self):
        with (ROOT / 'data/optical_stores.csv').open() as handle:
            stores = {r['store_id']: r for r in csv.DictReader(handle)}
        for folder in ('gentle-monster', 'valley-eyewear', 'moscot', 'am-eyewear'):
            snapshot = json.loads((ROOT / 'retailers' / folder / 'source_snapshot.json').read_text())
            with (ROOT / 'retailers' / folder / 'stores.csv').open() as handle:
                raw = list(csv.DictReader(handle))
            self.assertEqual(len(raw), snapshot['captured_count'])
            for row in raw:
                store = stores[folder + '-' + row['id']]
                self.assertEqual(store['source_url'], row['source_url'])
                self.assertEqual(float(store['latitude']), float(row['latitude']))
                self.assertEqual(store['status'], 'Active')
        self.assertIn('Eye examinations', stores['valley-eyewear-burleigh-heads']['services'])
        self.assertNotIn('Eye examinations', stores['moscot-melbourne']['services'])
        self.assertEqual(stores['am-eyewear-shop-darlinghurst']['business_type'], 'Prescription eyewear retail')
        airport = stores['gentle-monster-779149678137852858']
        self.assertIn('T1 International Terminal', airport['full_address'])
        self.assertEqual(airport['location_type'], 'Other')
        self.assertEqual(stores['gentle-monster-779149709720963067']['venue_id'], 'vic-chadstone')

    def test_ray_ban_source_identity_services_and_membership(self):
        snapshot = json.loads((ROOT / "retailers/ray-ban/source_snapshot.json").read_text())
        with (ROOT / "retailers/ray-ban/stores.csv").open() as handle:
            raw = list(csv.DictReader(handle))
        self.assertEqual({r["id"] for r in raw}, {r["id"] for r in snapshot["stores"]})
        self.assertEqual(len(raw), snapshot["captured_count"])
        self.assertEqual(len(raw), snapshot["directory_count"])
        with (ROOT / "data/optical_stores.csv").open() as handle:
            store = next(r for r in csv.DictReader(handle) if r["store_id"] == "ray-ban-C280")
        self.assertEqual(store["retailer"], "Ray-Ban")
        self.assertIn("Eye examinations", store["services"])
        self.assertEqual(store["status"], "Active")
        with (ROOT / "data/optical_stores.csv").open() as handle:
            existing = next(r for r in csv.DictReader(handle) if r["store_id"] == "opsm-1410")
        self.assertEqual(store["venue_id"], existing["venue_id"])
        self.assertTrue(any("optometrist" in e["facts"] for e in snapshot["supplementary_evidence"]))
        with (ROOT / "data/store_place_overrides.csv").open() as handle:
            mapping = next(r for r in csv.DictReader(handle) if r["store_id"] == store["store_id"])
        self.assertEqual(mapping["canonical_name"], "Chadstone Shopping Centre")
        self.assertEqual(mapping["official_url"], "https://www.chadstone.com.au/stores/ray-ban")


class RemainingEyewearTests(unittest.TestCase):
    def test_remapped_oakley_and_eye_piece_are_not_duplicated(self):
        with (ROOT / 'data/optical_stores.csv').open() as f:
            rows = list(csv.DictReader(f))
        stores = {r['store_id']: r for r in rows}
        self.assertEqual(len(stores), len(rows))
        with (ROOT / 'data/store_identity_remaps.csv').open() as f:
            remaps = {r['source_store_id']: r['canonical_store_id'] for r in csv.DictReader(f)}
        for brand in ('oakley', 'the-eye-piece'):
            with (ROOT / 'retailers' / brand / 'stores.csv').open() as f:
                for source in csv.DictReader(f):
                    raw = brand + '-' + source['id']
                    canonical = remaps.get(raw, raw)
                    self.assertIn(canonical, stores)
                    self.assertEqual(stores[canonical]['retailer'], 'Oakley' if brand == 'oakley' else 'The Eye Piece')
                    if raw != canonical:
                        self.assertNotIn(raw, stores)
        self.assertFalse(any(r['retailer'] == 'LINDBERG' for r in rows))
        self.assertEqual(stores['oakley-C271']['country'], 'New Zealand')
        self.assertEqual(stores['oakley-C273']['country'], 'New Zealand')
        airport = stores['oakley-C290']
        self.assertIn('Sydney', airport['name'])
        self.assertAlmostEqual(float(airport['latitude']), -33.93348991293692, places=6)
        self.assertNotIn('Eye examinations', airport['services'])
        self.assertIn('Eye examinations', stores['the-eye-piece-10909']['services'])

    def test_airport_membership_is_explicit_and_terminals_stay_separate(self):
        places = json.loads((ROOT / 'data/retail_places.json').read_text())['places']
        terminals = {p['place_id']: p for p in places if p['place_type'] == 'Airport Terminal'}
        self.assertTrue(terminals)
        with (ROOT / 'data/store_place_memberships.csv').open() as f:
            memberships = {r['store_id']: r for r in csv.DictReader(f)}
        ids = []
        for sid in ('sunglass-hut-B773', 'sunglass-hut-B754', 'sunglass-hut-B757'):
            member = memberships[sid]
            self.assertIn(member['place_id'], terminals)
            self.assertEqual(member['mapping_confidence'], 'High')
            self.assertEqual(member['location_setting'], 'Other')
            self.assertTrue(member['evidence_url'].startswith('https://'))
            ids.append(member['place_id'])
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(memberships['oakley-C290']['place_id'], ids[1])
        self.assertEqual(memberships['gentle-monster-779149678137852858']['place_id'], ids[0])
        self.assertNotIn(memberships['opsm-1488']['place_id'], terminals)

if __name__ == "__main__":
    unittest.main()
