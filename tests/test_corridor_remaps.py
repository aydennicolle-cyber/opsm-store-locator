"""Corrected street points retain historical place IDs and valid memberships."""
import csv
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_retail_places import apply_place_consolidations


class CorridorRemapTests(unittest.TestCase):
    def test_late_corridor_resolves_only_an_explicit_reviewed_remap(self):
        rows = [dict(previous_place_id='generated-street', canonical_place_id='stable-street')]
        places, aliases = [], {}
        with patch('build_retail_places.read_csv', return_value=[]):
            self.assertEqual(apply_place_consolidations(places, aliases, rows, defer_missing=True), {})
            places.append(dict(place_id='generated-street', centre_id='generated-street'))
            self.assertEqual(apply_place_consolidations(places, aliases, rows), {'generated-street': 'stable-street'})
        self.assertEqual(places[0]['place_id'], 'stable-street')
        self.assertEqual(aliases['generated-street'], 'stable-street')

    def test_missing_corridor_is_not_silently_accepted_after_final_pass(self):
        rows = [dict(previous_place_id='missing-street', canonical_place_id='missing-target')]
        with patch('build_retail_places.read_csv', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'Unknown place consolidation target'):
                apply_place_consolidations([], {}, rows)

    def test_corrected_dunedin_point_retains_existing_street_id(self):
        payload = json.loads((ROOT / 'data/retail_places.json').read_text())
        places = {p['place_id']: p for p in payload['places']}
        stable = 'corridor-nz-otago-dunedin-king-edward-street-1'
        self.assertIn(stable, places)
        self.assertEqual(payload['place_id_remaps']['corridor-nz-otago-dunedin-king-edward-street-2'], stable)
        self.assertLess(float(places[stable]['latitude']), -45.89)
        with (ROOT / 'data/store_place_memberships.csv').open() as f:
            memberships = {r['store_id']: r for r in csv.DictReader(f)}
        self.assertEqual(memberships['matthews-eyecare-nz-120105905']['place_id'], stable)
        self.assertTrue(all(not r['place_id'] or r['place_id'] in places for r in memberships.values()))


if __name__ == '__main__':
    unittest.main()
