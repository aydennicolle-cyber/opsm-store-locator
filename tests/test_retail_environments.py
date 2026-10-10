import copy
import json
import unittest
from pathlib import Path
from scripts.build_retail_environments import key
from scripts.scan_public_privacy import walk

ROOT=Path(__file__).resolve().parents[1]


class RetailEnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'data/retail_environments.json').read_text())
        cls.places={p['place_id']:p for p in cls.data['places']}

    def test_scope_and_unknowns_preserved(self):
        for p in self.places.values():
            self.assertFalse(p['coverage']['complete'])
            self.assertEqual(p['absent_features'],{})
            self.assertEqual(p['coverage']['observations'],len(p['observations']))
            self.assertEqual(p['coverage']['distinct_names'],len({key(r['name']) for r in p['observations']}))
            if p['format']=='High Street':self.assertIn('Named-street study',p['scope'])

    def test_all_features_have_evidence_and_dates(self):
        features={f['id'] for f in self.data['features']}
        for p in self.places.values():
            sources={r['source_id'] for r in p['observations']} | {'optical:'+o['store_id'] for o in p['optical']}
            for fid,refs in p['features'].items():
                self.assertIn(fid,features);self.assertTrue(set(refs)<=sources)
            for r in p['observations']:
                self.assertTrue(r['source_url'].startswith('https://'));self.assertTrue(r['observed_at']);self.assertTrue(r['scope_basis'])

    def test_optical_outlets_and_independent_identities(self):
        for p in self.places.values():
            self.assertEqual(len(p['optical']),len({o['store_id'] for o in p['optical']}))
            for o in p['optical']:
                if o['retailer']=='Independent / Other optical':self.assertEqual(o['operator'],o['name'])
            self.assertEqual(p['bn_presence']=='present',any(o['retailer']=='Bailey Nelson' for o in p['optical']))

    def test_precinct_directory_is_not_silently_street_membership(self):
        p=self.places['corridor-au-qld-fortitude-valley-james-street']
        self.assertTrue(p['coverage']['held_scope_records'])
        self.assertFalse(p['observations'])

    def test_tenant_unit_address_withheld(self):
        held=[p for p in self.places.values() if p['address_note']]
        self.assertTrue(held)
        self.assertTrue(all(not p['address'] for p in held))

    def test_commercial_keys_rejected_by_public_scan(self):
        for field in ['revenue_group','cohort_membership','prior_source_store_code','full_period_trading']:
            with self.assertRaises(ValueError):walk({'nested':[{field:'synthetic'}]},Path('synthetic.json'))
        walk(self.data,Path('retail_environments.json'))


if __name__=='__main__':unittest.main()
