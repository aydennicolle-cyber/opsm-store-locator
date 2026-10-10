import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from market_points import point_key, resolve_market
from build_market_intelligence import population_change


class MarketPointTests(unittest.TestCase):
    def setUp(self):
        self.point={'latitude':0.5,'longitude':0.5,'country':'Australia'}
        self.a={'properties':{'sa2_code':'a'},'geometry':{'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}}
        self.b={'properties':{'sa2_code':'b'},'geometry':{'type':'Polygon','coordinates':[[[2,2],[3,2],[3,3],[2,3],[2,2]]]}}

    def test_authoritative_match_overrules_wrong_generalised_polygon(self):
        cache={point_key(self.point):{'match_status':'Unique','sa2_code':'b'}}
        props,basis=resolve_market(self.point,[self.a,self.b],cache)
        self.assertEqual(props['sa2_code'],'b')
        self.assertEqual(basis,'ABS authoritative point query')
        moved=dict(self.point,latitude=0.51)
        self.assertEqual(resolve_market(moved,[self.a,self.b],cache)[0]['sa2_code'],'a')

    def test_ambiguous_or_missing_authoritative_code_never_guessed(self):
        for entry in [{'match_status':'Ambiguous'}, {'match_status':'Unmatched'}, {'match_status':'Unique','sa2_code':'unknown'}]:
            self.assertIsNone(resolve_market(self.point,[self.a],{point_key(self.point):entry})[0])

    def test_holes_and_overlapping_display_boundaries_do_not_assign(self):
        self.assertIsNone(resolve_market(self.point,[self.a,self.a],{})[0])
        self.a['geometry']['coordinates'].append([[0.4,0.4],[0.6,0.4],[0.6,0.6],[0.4,0.6],[0.4,0.4]])
        self.assertIsNone(resolve_market(self.point,[self.a],{})[0])

    def test_absolute_growth_uses_counts_and_keeps_missing_and_declines(self):
        self.assertEqual(population_change(11191,10898),293)
        self.assertEqual(population_change(23669,23708),-39)
        self.assertEqual(population_change(10,0),10)
        self.assertIsNone(population_change(100,None))
        self.assertIsNone(population_change(None,100))
