import copy
import json
import unittest
from pathlib import Path
from scripts import build_destination_research as research

ROOT = Path(__file__).resolve().parents[1]


class DestinationResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads((ROOT/'data/destination_directory.json').read_text())
        cls.rows = cls.payload['records']
        cls.places = {p['place_id']:p for p in json.loads((ROOT/'data/retail_places.json').read_text())['places']}

    def test_directory_counts_are_not_tenancy_shares(self):
        for summary in research.make_summaries(self.payload, self.places):
            rows = [r for r in self.rows if r['place_id']==summary['place_id']]
            self.assertEqual(summary['source_listing_count'],len(rows))
            self.assertIsNone(summary['tenancy_count_share'])
            self.assertIsNone(summary['floor_area_share'])
            self.assertTrue(summary['share_unavailable_reason'])

    def test_coming_soon_held_and_optical_do_not_enter_nonoptical_comparison(self):
        row = copy.deepcopy(next(r for r in self.rows if research.usable_directory_row(r)))
        for key,value in [('listing_status','Coming soon (directory label)'),('scope_status','Review required'),('role','Optical')]:
            changed={**row,key:value}
            self.assertFalse(research.usable_directory_row(changed))
            self.assertEqual(research.search_directory([changed],row['display_name']),[])

    def test_directory_address_conflict_does_not_create_new_optical_identity(self):
        row=next(r for r in self.rows if r['source_record_id']=='sunglass-hut' and r['place_id'].startswith('corridor'))
        self.assertEqual(row['scope_status'],'Review required')
        self.assertIn('15-17 Jetty Road',row['source_address'])
        self.assertIn('Colley',row['canonical_optical_address'])
        self.assertTrue(row['canonical_optical_store_id'])
        self.assertFalse(research.usable_directory_row(row))

    def test_invalid_street_membership_is_rejected(self):
        row=copy.deepcopy(next(r for r in self.rows if r['place_id'].startswith('corridor')))
        row['scope_status']=research.SCOPE_ACCEPTED
        row['source_address']='1 Colley Terrace, Glenelg SA'
        with self.assertRaisesRegex(ValueError,'explicit address'):
            research.validate_records({'records':[row]},self.places,set())

    def test_unknown_optical_identity_is_rejected(self):
        row=copy.deepcopy(next(r for r in self.rows if r['canonical_optical_store_id']))
        with self.assertRaisesRegex(ValueError,'Unknown canonical optical'):
            research.validate_records({'records':[row]},self.places,set())

    def test_category_search_retains_all_matching_businesses(self):
        found=research.search_directory(self.rows,'food and dining')
        self.assertGreater(len(found),1)
        self.assertTrue(all('Food and dining' in r['categories'] for r in found))
        self.assertEqual(len({r['record_id'] for r in found}),len(found))

    def test_name_overlap_is_conservative_and_preserves_source_ids(self):
        self.assertEqual(research.name_key('A & B'),research.name_key('a and b'))
        self.assertNotEqual(research.name_key('Royal Copenhagen Glenelg'),research.name_key('Royal Copenhagen'))
        ids={r['record_id'] for r in self.rows if research.usable_directory_row(r)}
        for pair in research.compare_directories(self.rows,self.places):
            for match in pair['shared_normalized_names']:
                self.assertTrue(set(match['left_records']+match['right_records']) <= ids)

    def test_unclassified_is_not_absence(self):
        summaries=research.make_summaries(self.payload,self.places)
        for p in summaries:
            actual=sum('Unclassified directory listing' in r['categories'] for r in self.rows if r['place_id']==p['place_id'] and research.usable_directory_row(r))
            self.assertEqual(p['unclassified_listings'],actual)
        back=next(r for r in self.rows if r['display_name']=='Back In Focus')
        self.assertEqual(back['role'],'Other business or service')

    def test_stored_summaries_match_full_database(self):
        stored=json.loads((ROOT/'data/destination_research.json').read_text())
        self.assertEqual(stored['profiles'],research.make_summaries(self.payload,self.places))
        self.assertNotIn('records',stored)


if __name__=='__main__':unittest.main()
