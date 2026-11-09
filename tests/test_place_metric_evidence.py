import unittest
from scripts.place_metric_evidence import observation, reconcile, merge_place_metrics


class PlaceMetricEvidenceTests(unittest.TestCase):
    def test_conflicting_reports_are_retained_without_selecting_first(self):
        rows = [observation('gla_sqm', value, {'source_url': url, 'source_date': date})
                for value, url, date in [(100, 'https://example.org/a', '2024-01-01'),
                                          (120, 'https://example.org/b', '2025-01-01')]]
        first = reconcile({'gla_sqm': rows})
        self.assertIsNone(first['gla_sqm'])
        self.assertNotIn('gla_sqm', first['metric_evidence'])
        self.assertIn('gla_sqm', first['metric_conflicts'])
        self.assertEqual(len(first['metric_observations']['gla_sqm']), 2)
        self.assertIsNone(reconcile({'gla_sqm': list(reversed(rows))})['gla_sqm'])

    def test_merge_uses_property_evidence_and_preserves_held_reports(self):
        report = observation('annual_visits', 18600000, {
            'source_url': 'https://example.org/property', 'source_date': '2025-12-31',
            'last_verified_at': '2026-09-02', 'private_notes': 'must not copy',
        })
        prop = reconcile({'annual_visits': [report]})
        result = merge_place_metrics({'source_url': 'https://example.org/store'}, prop)
        self.assertEqual(result['annual_visits'], 18600000)
        self.assertEqual(result['metric_evidence']['annual_visits']['source_url'], 'https://example.org/property')
        self.assertEqual(result['metric_evidence']['annual_visits']['source_date'], '2025-12-31')
        self.assertNotIn('private_notes', report)
        conflict = reconcile({'annual_visits': [report, observation('annual_visits', 1, {})]})
        self.assertIsNone(merge_place_metrics({}, conflict)['annual_visits'])

    def test_same_value_keeps_multiple_sources_and_zero_is_not_missing(self):
        a = observation('tenancy_count', 0, {'source_url': 'https://example.org/a'})
        b = observation('tenancy_count', 0, {'source_url': 'https://example.org/b'})
        result = reconcile({'tenancy_count': [a, b, a]})
        self.assertEqual(result['tenancy_count'], 0)
        self.assertEqual(len(result['metric_observations']['tenancy_count']), 2)
        self.assertFalse(result['metric_conflicts'])

    def test_invalid_values_rejected(self):
        for value in ['nan', 'inf', -1, 1.5]:
            with self.assertRaises(ValueError):
                observation('tenancy_count', value, {})
