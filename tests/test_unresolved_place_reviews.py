import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from unresolved_place_reviews import fingerprint, load_reviews


class UnresolvedPlaceReviewTests(unittest.TestCase):
    def test_changed_facts_reopen_review_without_losing_history(self):
        store = dict(store_id='s', name='Practice', full_address='Shop 3, 1 Example Road',
                     status='Active', latitude='-27', longitude='153')
        row = dict(store_id='s', store_fingerprint=fingerprint(store), candidate_venue_id='',
                   reviewed_at='2026-09-03', evidence_url='https://example.org/practice',
                   reason='Practice confirmed; named retail property unresolved.')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'reviews.csv'
            with path.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(row)); writer.writeheader(); writer.writerow(row)
            original = path.read_bytes()
            self.assertIn('s', load_reviews([store], path))
            for key, value in [('full_address', '22 Other Street'), ('status', 'Closed'),
                               ('latitude', '-28'), ('name', 'Different practice')]:
                self.assertEqual(load_reviews([dict(store, **{key: value})], path), {})
                self.assertIn('s', load_reviews([dict(store, **{key: value})], path, include_stale=True))
                self.assertEqual(path.read_bytes(), original)
            # Routine fetch metadata alone does not invent new tenancy evidence.
            self.assertIn('s', load_reviews([dict(store, fetched_at='2026-10-25')], path))
            with self.assertRaises(ValueError):
                load_reviews([], path)

    def test_missing_evidence_is_not_a_safe_unresolved_outcome(self):
        store = dict(store_id='s')
        row = dict(store_id='s', store_fingerprint=fingerprint(store), candidate_venue_id='',
                   reviewed_at='2026-09-03', evidence_url='', reason='')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'reviews.csv'
            with path.open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(row)); writer.writeheader(); writer.writerow(row)
            with self.assertRaises(ValueError):
                load_reviews([store], path)
