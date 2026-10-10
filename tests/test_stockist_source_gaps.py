"""Guard public-locator omissions without accepting conflicting geography."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fetch_priority_optical_networks import bupa, bupa_australian_location
from fetch_additional_optical_networks import stockist_1001


class StockistSourceGapTests(unittest.TestCase):
    def location(self, **changes):
        row = dict(id=19555346, name='Bupa Optical & Hearing Norwood',
                   country=None, state='South Australia', city='Norwood',
                   postal_code='5067', address_line_1='254 The Parade',
                   latitude='-34.92115339', longitude='138.64043160',
                   phone='08 7150 1563', website='https://example.org/norwood',
                   filters=[dict(name='optical'), dict(name='hearing')])
        row.update(changes)
        return row

    def test_missing_country_keeps_evidenced_australian_optical_branch(self):
        with patch('fetch_priority_optical_networks.fetch_text', return_value=json.dumps([self.location()])):
            _, rows = bupa()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['id'], rows[0]['state'], rows[0]['country']), (19555346, 'SA', 'Australia'))
        self.assertIn('254 The Parade', rows[0]['full_address'])
        self.assertEqual(rows[0]['audiology'], 'true')

    def test_missing_country_with_weak_or_conflicting_fields_stops_refresh(self):
        for changes in [dict(state='Auckland'), dict(postal_code=''),
                        dict(latitude='-36.9', longitude='174.8'),
                        dict(latitude='nan'), dict(address_line_1=''), dict(city='')]:
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                bupa_australian_location(self.location(**changes))

    def test_explicit_other_country_is_not_overridden_and_nonoptical_is_excluded(self):
        self.assertFalse(bupa_australian_location(self.location(country='New Zealand')))
        for country in ['AU', 'aus', ' Australia ']:
            self.assertTrue(bupa_australian_location(self.location(country=country)))
        with patch('fetch_priority_optical_networks.fetch_text', return_value=json.dumps([self.location(filters=[dict(name='hearing')])])):
            self.assertEqual(bupa()[1], [])

    def test_1001_uses_branch_website_when_custom_link_is_missing(self):
        rows=[self.location(id=1, country='Australia', name='Example', custom_fields=[], website='https://example.org/branch'),
              self.location(id=2, country='Australia', name='Second', custom_fields=[dict(name='Find Out More', value='https://example.org/custom')], website='https://example.org/fallback')]
        with patch('fetch_additional_optical_networks.fetch_text', return_value=json.dumps(rows)):
            _, result=stockist_1001()
        self.assertEqual([r['official_url'] for r in result], ['https://example.org/branch','https://example.org/custom'])
