import copy
import unittest
from scripts.retail_directory_overlay import apply_captures


class DirectoryOverlayTests(unittest.TestCase):
    def setUp(self):
        self.public = {'features': [], 'places': [{'place_id': 'synthetic', 'name': 'Synthetic',
                       'format': 'Shopping Centre', 'features': {'operator:example': ['canonical']}}]}
        def record(sid, name, **extra):
            return {'source_id': sid, 'name': name, 'source_url': 'https://example.org/directory',
                    'observed_at': '2026-10-01', 'scope_basis': 'Official directory',
                    'scope_status': 'included', 'listing_status': 'listed', 'categories': ['Services'], **extra}
        self.capture = {'place_id': 'synthetic', 'records': [record('1', 'Alpha'), record('2', 'Alpha'),
            record('3', 'Future', listing_status='coming soon'), record('4', 'Outside', scope_status='held'),
            record('5', 'Optical', role='Optical', categories=['Health and wellbeing'])],
            'source_total': 5, 'directory_complete': True, 'format_scope': 'canonical centre',
            'scope': 'Official directory', 'source_urls': ['https://example.org/directory'],
            'capture_method': 'All pages', 'limitations': 'Trading not verified', 'absence_reviews': []}

    def test_scope_status_duplicates_and_optical_are_not_category_evidence(self):
        result = apply_captures(self.public, [self.capture])['places'][0]
        self.assertEqual(result['features']['brand:alpha'], ['1', '2'])
        self.assertNotIn('brand:future', result['features'])
        self.assertNotIn('brand:outside', result['features'])
        self.assertNotIn('category:health and wellbeing', result['features'])
        self.assertEqual(result['features']['operator:example'], ['canonical'])
        self.assertEqual(result['coverage']['distinct_names'], 2)
        self.assertFalse(result['coverage']['trading_verified'])
        self.assertFalse(result['coverage']['complete'])
        self.assertNotIn('coverage', self.public['places'][0], 'public inputs must not mutate')

    def test_absence_requires_reconciled_capture_and_review(self):
        review = {'feature_id': 'brand:missing', 'label': 'Missing', 'kind': 'Retailer',
                  'basis': 'Reviewed all source names', 'source_url': 'https://example.org/directory',
                  'observed_at': '2026-10-01'}
        self.capture['absence_reviews'] = [review]
        self.assertEqual(apply_captures(self.public, [self.capture])['places'][0]['absent_features']['brand:missing'], [review])
        for change in [{'directory_complete': False}, {'source_total': 6}, {'format_scope': 'named street'}]:
            with self.assertRaises(ValueError):
                apply_captures(self.public, [{**self.capture, **change}])
        review['feature_id'] = 'brand:alpha'
        with self.assertRaises(ValueError): apply_captures(self.public, [self.capture])

    def test_missing_attribution_or_duplicate_source_ids_fail(self):
        for change in [{'source_id': '2'}, {'observed_at': ''}, {'source_url': ''}]:
            capture = copy.deepcopy(self.capture)
            capture['records'][0].update(change)
            with self.assertRaises(ValueError): apply_captures(self.public, [capture])

    def test_explicit_publisher_brand_is_searchable_without_adding_another_listing(self):
        self.capture['records'][0]['source_brand'] = 'Documented fascia'
        result = apply_captures(self.public, [self.capture])['places'][0]
        self.assertEqual(result['features']['brand:documented fascia'], ['1'])
        self.assertEqual(result['features']['brand:alpha'], ['1', '2'])
        self.assertEqual(len(result['observations']), 3)
        self.assertFalse(result['coverage']['trading_verified'])
        self.assertNotIn('operator:documented fascia', result['features'])


if __name__ == '__main__': unittest.main()
