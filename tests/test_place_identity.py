"""Prevent retailer/tenancy identities from becoming public retail places."""
import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_retail_places import (storefront_place_name, promote_store_named_centres,
                                apply_place_consolidations, validate_place_integrity,
                                create_place_from_override, cluster_centres)


class PlaceIdentityBoundaryTests(unittest.TestCase):
    def test_nearby_distinct_barker_properties_do_not_share_source_identity(self):
        plaza = dict(centre_id='plaza', name='Barker Plaza', country='Australia',
                     state='SA', latitude=-35.06413, longitude=138.858639)
        central = dict(plaza, centre_id='central', name='Mount Barker Central Shopping Centre',
                       latitude=-35.064257, longitude=138.859492)
        for point in [central, dict(central, latitude=plaza['latitude'], longitude=plaza['longitude'])]:
            groups = cluster_centres([plaza, point])
            self.assertEqual([{r['centre_id'] for r in group} for group in groups],
                             [{'plaza'}, {'central'}])

    def test_retailer_and_unit_labels_are_not_place_names(self):
        for name in ['Sunglass Hut Pacific Fair', 'Sunglass Hut Myer Adelaide -Closed',
                     'Oakley - Westfield', 'Specsavers Centre', 'Kiosk K02 Westfield Coomera',
                     'Shop 12 Shopping Centre']:
            self.assertTrue(storefront_place_name(name), name)
        for name in ['Bailey Street', 'Canberra Outlet Centre', 'The Mall', 'Castle Towers',
                     'Sunglass Hutches Arcade']:
            self.assertFalse(storefront_place_name(name), name)

    def test_invalid_derived_branch_venue_waits_for_review(self):
        store={'country':'Australia','state':'QLD','suburb':'Broadbeach','name':'Sunglass Hut Pacific Fair',
               'venue_id':'raw-branch-venue','venue_name':'Sunglass Hut Pacific Fair',
               'location_type':'Shopping Centre'}
        places=[]; remaps={}
        promote_store_named_centres([store], places, remaps)
        self.assertEqual(places, [])
        self.assertEqual(remaps, {})
        # A reviewed source-ID remap remains authoritative.
        remaps['raw-branch-venue']='canonical-pacific-fair'
        promote_store_named_centres([store], places, remaps)
        self.assertEqual(remaps['raw-branch-venue'], 'canonical-pacific-fair')

    def test_integrity_rejects_retailer_as_place(self):
        bad={'place_id':'bad','name':'Sunglass Hut Example','location_setting':'Shopping Centre'}
        with self.assertRaisesRegex(ValueError,'shopping-centre names'):
            validate_place_integrity([bad],[],[])

    def test_unresolved_historical_tenant_cannot_create_verified_property(self):
        store = dict(store_id='historical-tenant', country='Australia', state='QLD',
                     suburb='Samford', name='Historical optometrist', status='Unknown',
                     venue_id='raw-samford', venue_name='Samford Central Shopping Centre',
                     location_type='Shopping Centre', full_address='Shop 8, Samford Central',
                     latitude='-27.37', longitude='152.88')
        places, remaps = [], {}
        promote_store_named_centres([store], places, remaps, {store['store_id']})
        self.assertEqual(places, [])
        self.assertEqual(remaps, {})
        # Current records retain existing promotion behaviour.
        for status in ['Active', 'Mapped']:
            places, remaps = [], {}
            promote_store_named_centres([dict(store, status=status)], places, remaps,
                                        {store['store_id']})
            self.assertEqual(len(places), 1)
            self.assertEqual(remaps[store['venue_id']], places[0]['place_id'])
        # An independently established property is neither removed nor replaced.
        existing = dict(place_id='independent-property', name=store['venue_name'],
                        country='Australia', state='QLD', locality='Samford',
                        location_setting='Shopping Centre', aliases=[], old_centre_ids=[])
        places, remaps = [existing], {}
        promote_store_named_centres([store], places, remaps, {store['store_id']})
        self.assertEqual(places, [existing])
        self.assertEqual(remaps, {'raw-samford': 'independent-property'})

    def test_cross_type_remap_requires_explicit_review(self):
        source={'place_id':'old','name':'Optical shop','country':'Australia','location_setting':'Shopping Centre'}
        target={'place_id':'street','name':'Queen Street','country':'Australia','location_setting':'High Street','aliases':[]}
        row={'previous_place_id':'old','canonical_place_id':'street','reason':'Written street address',
             'evidence_url':'https://example.com/official-address','last_verified_at':'2026-10-23'}
        with self.assertRaisesRegex(ValueError,'Incompatible'):
            apply_place_consolidations([dict(source),dict(target)],{},[row])
        places=[dict(source),dict(target)]; remaps={'native':'old'}
        result=apply_place_consolidations(places,remaps,[dict(row,canonical_location_setting='High Street')])
        self.assertEqual(result,{'old':'street'})
        self.assertEqual(remaps['native'],'street')
        with self.assertRaisesRegex(ValueError,'Incompatible'):
            apply_place_consolidations([dict(source,country='New Zealand'),dict(target)],{},
                                       [dict(row,canonical_location_setting='High Street')])

    def test_reviewed_override_preserves_explicit_id(self):
        store={'country':'Australia','state':'SA','suburb':'Adelaide','postcode':'5000',
               'full_address':'14-38 Rundle Mall','latitude':'-34.92','longitude':'138.60'}
        override={'canonical_place_id':'place-au-sa-myer-centre-adelaide',
                  'canonical_name':'The Myer Centre','location_setting':'Shopping Centre',
                  'place_type':'Shopping Centre','official_url':'https://example.com/store',
                  'source_date':'2026-10-18','confidence':'High','evidence_basis':'Written centre address'}
        self.assertEqual(create_place_from_override(store,override)['place_id'],override['canonical_place_id'])


class ReconciledPlaceIdentityTests(unittest.TestCase):
    def test_audit_decisions_resolve_to_reviewed_memberships(self):
        data=ROOT/'data'
        places={p['place_id']:p for p in json.loads((data/'retail_places.json').read_text())['places']}
        with (data/'store_place_memberships.csv').open() as f:
            memberships={r['store_id']:r for r in csv.DictReader(f)}
        with (data/'place_id_remaps.csv').open() as f:
            remaps={r['previous_place_id']:r['canonical_place_id'] for r in csv.DictReader(f)}
        decisions=json.loads((ROOT/'docs/PLACE_IDENTITY_AUDIT_2026-10-23.json').read_text())['decisions']
        for row in decisions:
            if row.get('action') == 'rename_preserving_id':
                self.assertEqual(places[row['canonical_place_id']]['name'],row['canonical_name'])
                continue
            self.assertNotIn(row['previous_place_id'],places)
            if 'canonical_place_id' not in row:
                continue
            target=row['canonical_place_id']
            self.assertIn(target,places)
            self.assertEqual(memberships[row['store_id']]['place_id'],target,row['store_id'])
            self.assertEqual(memberships[row['store_id']]['location_setting'],row['location_setting'])
            self.assertEqual(remaps[row['previous_place_id']],target)
            self.assertEqual(remaps[row['source_venue_id']],target)
        self.assertFalse([p['name'] for p in places.values()
                          if p['location_setting']=='Shopping Centre' and storefront_place_name(p['name'])])
        for sid in ['sunglass-hut-AU3191','sunglass-hut-AU3334','sunglass-hut-AU3775']:
            self.assertEqual(memberships[sid]['trading_status'],'Closed')
        # The October 31 review established two distinct Chancellor properties.
        optikus=memberships['independent-other-optical-provision-17587']
        h2=memberships['independent-other-optical-reviewed-au-h2-vision-sippy-downs']
        self.assertEqual(optikus['place_id'],'place-au-qld-chancellor-village-business-centre')
        self.assertEqual(optikus['location_setting'],'Shopping Centre')
        self.assertEqual(h2['place_id'],'place-au-qld-chancellor-village-shopping-centre')
        self.assertNotEqual(optikus['place_id'],h2['place_id'])
        for sid in ['sunglass-hut-B682','sunglass-hut-A571','sunglass-hut-B885']:
            self.assertEqual(memberships[sid]['place_id'],'place-au-qld-pacific-fair')

    def test_centre_road_street_records_are_not_one_centre(self):
        with (ROOT/'data/store_place_memberships.csv').open() as f:
            ms={r['store_id']:r for r in csv.DictReader(f)}
        core=[ms[s] for s in ['opsm-1134','specsavers-3282','independent-other-optical-provision-17060']]
        self.assertTrue(all(r['location_setting']=='High Street' for r in core))
        self.assertEqual(len({r['place_id'] for r in core}),1)
        self.assertNotEqual(core[0]['place_id'],ms['independent-other-optical-osm-au-way-641539883']['place_id'])

if __name__=='__main__':unittest.main()
