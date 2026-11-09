import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_specsavers_stores as builder


class ReviewedSpecsaversAdditions(unittest.TestCase):
    def test_rebuild_preserves_upcoming_records_and_original_source_dates(self):
        if builder.IS_NZ:
            self.skipTest('AU reviewed additions fixture')
        with builder.CSV_PATH.open(newline='') as stream:
            before = {r['id']: r for r in csv.DictReader(stream)}
        with tempfile.TemporaryDirectory() as folder:
            csv_path = Path(folder) / 'stores.csv'
            geo_path = Path(folder) / 'stores.geojson'
            with patch.object(builder, 'CSV_PATH', csv_path), patch.object(builder, 'GEOJSON_PATH', geo_path):
                builder.main()
            with csv_path.open(newline='') as stream:
                rebuilt = {r['id']: r for r in csv.DictReader(stream)}
            self.assertEqual(before, rebuilt)
            snapshot = json.loads(builder.SNAPSHOT_PATH.read_text())
            self.assertEqual(json.loads(geo_path.read_text())['metadata']['fetched_at'], snapshot['fetched_at'])
            for slug in ('engadine', 'gisborne'):
                self.assertEqual(rebuilt[slug]['status'], 'Opening Soon')
                self.assertEqual(rebuilt[slug]['fetched_at'], '2026-10-26')

    def test_new_snapshot_collision_requires_reconciliation(self):
        if builder.IS_NZ:
            self.skipTest('AU reviewed additions fixture')
        addition = json.loads(builder.ADDITIONS_PATH.read_text())['records'][0]['record']
        # Native IDs may change; a shared official URL must still stop duplication.
        captured = {**addition, 'id': 'new-native-id', 'status': 'Active'}
        with self.assertRaisesRegex(ValueError, 'Reconcile reviewed addition'):
            builder.merge_reviewed_additions([captured], builder.ADDITIONS_PATH)
