"""A rebuild must preserve authoritative demographic uncertainty."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_market_intelligence as market


class MarketRebuildEvidenceTests(unittest.TestCase):
    def test_unmatched_authoritative_receipt_prevents_nearest_area_assignment(self):
        store = {"store_id": "reviewed-point", "country": "Australia",
                 "latitude": "-38.2", "longitude": "145.0"}
        receipt = {"match_status": "Unmatched", "sa2_code": None, "sa2_name": None,
                   "source_url": "https://geo.abs.gov.au/recorded-query",
                   "checked_at": "2026-09-01"}
        with patch.object(market, "authoritative_link", return_value=receipt), \
                patch.object(market, "query_sa2_for_point") as remote:
            result = market.link_stores_to_market([store], [])[store["store_id"]]
        remote.assert_not_called()
        self.assertEqual(result["sa2_code"], "")
        self.assertEqual(result["match_confidence"], "Unmatched")
        self.assertIsNone(result["boundary_distance_km"])
        self.assertIn("unresolved", result["coverage_note"])
        self.assertEqual(result["checked_at"], receipt["checked_at"])


if __name__ == "__main__":
    unittest.main()
