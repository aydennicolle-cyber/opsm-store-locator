import sys
import unittest
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sunglass_hut import rows, refresh_canonical
from fetch_sunglass_hut import leaves, document

class SunglassHutTests(unittest.TestCase):
    def test_directory_traversal_uses_leaf_ids(self):
        self.assertEqual(leaves({'dm_directoryChildren':[{'slug':'au/nsw','dm_directoryChildren':[{'slug':'au/nsw/a/shop'}]}]}), ['au/nsw/a/shop'])
        with self.assertRaises(ValueError): document('<html>unavailable</html>')

    def test_source_reconciles_and_closed_overrides_hours(self):
        import json
        data=rows()
        source=json.loads((Path(__file__).resolve().parents[1]/'retailers/sunglass-hut/source_snapshot.json').read_text())
        self.assertEqual(len(data),sum(c['directory_count'] for c in source['countries'].values()))
        self.assertEqual(len(data),len({r['id'] for r in data}))
        for row in data:
            self.assertTrue(row['latitude'] and row['longitude'] and row['full_address'])
            self.assertNotIn(row['state'], ('NZ North','NZ South',''))
            if 'closed' in row['name'].lower(): self.assertEqual(row['status'],'Closed')
        self.assertTrue(any(r['status']=='Closed' for r in data))

    def test_refresh_preserves_canonical_mapping_and_coordinates(self):
        row=rows()[0]
        store={'store_id':'existing-id','venue_id':'accepted-place','latitude':-33,'longitude':151}
        refresh_canonical([store], {'sunglass-hut-'+row['id']:'existing-id'})
        self.assertEqual(store['retailer'],'Sunglass Hut')
        self.assertEqual(store['store_id'],'existing-id')
        self.assertEqual(store['venue_id'],'accepted-place')
        self.assertEqual(store['latitude'],-33)
        self.assertEqual(store['status'],row['status'])
