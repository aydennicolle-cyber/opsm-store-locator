import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_retail_places import apply_canonical_place_overrides

class MissingCorridorIdentityTests(unittest.TestCase):
    def test_retired_corridor_cannot_rename_same_road_in_another_town(self):
        places=[{'place_id':'corridor-au-nsw-rockdale-princes-highway','name':'Princes Highway','state':'NSW'}]
        row={'place_id':'corridor-au-nsw-ulladulla-princess-highway','canonical_name':'Princes Highway','aliases':'Princess Highway'}
        remaps={}
        self.assertEqual(apply_canonical_place_overrides(places,remaps,[row],defer_missing_corridors=True),[row])
        with self.assertRaisesRegex(ValueError,'Unknown canonical corridor override'):
            apply_canonical_place_overrides(places,remaps,[row])
        self.assertEqual(places[0]['place_id'],'corridor-au-nsw-rockdale-princes-highway')
        self.assertEqual(remaps,{})
