import unittest
from scripts.environment_coverage import label_coverage, summarize


class EnvironmentCoverageTests(unittest.TestCase):
    def test_capture_trading_and_missing_are_separate(self):
        def place(pid, rows, **coverage):
            return {'place_id': pid, 'place_type': 'Shopping Centre', 'observations': rows,
                    'coverage': {'observations': len(rows), **coverage}}
        payload = {'places': [
            place('complete', [{'role': 'Other business/services'}], directory_complete=True,
                  format_scope='canonical centre', trading_verified=False),
            place('held', [], source_urls=['https://example.org'], held_scope_records=['a']),
            place('missing', []),
            place('optical', [{'role': 'Optical'}]),
        ]}
        label_coverage(payload)
        self.assertIn('Complete source capture', payload['places'][0]['coverage']['research_status_label'])
        self.assertIn('not independently verified', payload['places'][0]['coverage']['trading_verification_label'])
        self.assertEqual(payload['places'][1]['coverage']['research_status_label'], 'Partly researched')
        self.assertEqual(payload['places'][2]['coverage']['research_status_label'], 'Not researched for tenant mix')
        summary = summarize(payload, ['complete', 'optical'])
        self.assertEqual(summary['counts']['places_with_listing_evidence'], 2)
        self.assertEqual(summary['counts']['places_with_non_optical_listing_evidence'], 1)
        self.assertEqual(summary['counts']['complete_centre_source_captures'], 1)
        self.assertEqual(summary['counts']['independently_trading_verified_places'], 0)
        self.assertEqual(summary['bailey_corridor_retail_mix_coverage'], 50)

    def test_complete_street_source_is_not_complete_centre(self):
        p = {'place_id':'street', 'place_type':'High Street Corridor', 'observations':[],
             'coverage':{'directory_complete':True, 'format_scope':'named street'}}
        result = summarize({'places':[p]})['counts']
        self.assertEqual(result['complete_source_captures'], 1)
        self.assertEqual(result['complete_centre_source_captures'], 0)
