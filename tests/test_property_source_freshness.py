"""A derived property rebuild is not a new external source check."""
import json
import tempfile
import unittest
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_data_health as health


class PropertySourceFreshnessTests(unittest.TestCase):
    def test_rebuild_and_one_recent_property_do_not_refresh_whole_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / 'property.json'
            manifest = {'freshness_policy_days': {'property_relationship': 180},
                        'sources': [{'id': 'property-portfolios', 'category': 'property_relationship',
                                     'snapshot': 'property.json', 'completion_status': 'partial'}]}
            observations = []
            with patch.object(health, 'ROOT', root):
                for rebuilt_at in ['2026-10-01', '2026-10-27']:
                    snapshot.write_text(json.dumps({'generated_at': rebuilt_at,
                                                   'relationships': [{'source_date': '2026-10-27'}]}))
                    observations.append(health.source_results(manifest, datetime(2026, 10, 27, tzinfo=timezone.utc), {})[0])
            self.assertEqual(observations[0], observations[1])
            self.assertIsNone(observations[1]['last_success'])
            self.assertIsNone(observations[1]['age_days'])
            self.assertFalse(observations[1]['fresh'])
            self.assertEqual(observations[1]['status'], 'partial')

    def test_explicit_whole_source_capture_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'property.json').write_text('{"generated_at":"2026-10-27"}')
            manifest = {'freshness_policy_days': {'property_relationship': 180},
                        'sources': [{'id': 'property-portfolios', 'category': 'property_relationship',
                                     'snapshot': 'property.json', 'completion_status': 'partial',
                                     'last_success': '2026-09-02'}]}
            with patch.object(health, 'ROOT', root):
                result = health.source_results(manifest, datetime(2026, 10, 27, tzinfo=timezone.utc), {})[0]
            self.assertEqual(result['last_success'], '2026-09-02')
            self.assertEqual(result['age_days'], 55)
