import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from capture_nsw_providers import capture_tables, HEADERS
from reconcile_qld_dispensers import reconcile


class NSWProviderCaptureTests(unittest.TestCase):
    row = ['Example\nOptometry', 'Shop 2', '18 Main Road', 'Tweed Heads', 'NSW', '2485', '07 5555 1234']

    def test_preserves_multiline_cells_and_distinct_duplicate_rows(self):
        records = capture_tables([[[HEADERS, self.row]], [[HEADERS, self.row]]])
        self.assertEqual(records[0]['raw']['name'], 'Example Optometry')
        self.assertEqual(records[0]['raw']['address'], 'Shop 2, 18 Main Road')
        self.assertEqual(records[0]['raw']['original_cells'], self.row)
        self.assertNotEqual(records[0]['source_id'], records[1]['source_id'])
        self.assertEqual(records[0]['source_record_hash'], records[1]['source_record_hash'])
        self.assertEqual(records[1]['source_page'], 2)

    def test_fails_on_missing_page_or_changed_columns(self):
        for pages in [[], [[]], [[[HEADERS]]], [[[HEADERS, self.row[:-1]]]],
                      [[[[*HEADERS[:-1], 'Email'], self.row]]]]:
            with self.assertRaises(ValueError): capture_tables(pages)

    def test_cross_border_name_candidates_respect_row_state(self):
        snapshot = dict(source={}, records=capture_tables([[[HEADERS, self.row]]]))
        stores = [dict(store_id=state, name='Example Optometry', full_address='Australia',
                       state=state, suburb='', postcode='', phone='', country='Australia', status='Mapped')
                  for state in ['NSW', 'QLD']]
        row = reconcile(snapshot, stores)['records'][0]
        self.assertEqual([c['store_id'] for c in row['candidates']], ['NSW'])
        self.assertEqual(row['promotion_status'], 'Unpromoted discovery lead')
        self.assertNotIn('canonical_store_id', row)


if __name__ == '__main__':
    unittest.main()
