"""Screening must use the same evidenced centre scale as the property panel."""
import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_property_intelligence import portfolio_metrics
from build_retail_places import add_official_retail_places


class RetailContextTests(unittest.TestCase):
    def test_authoritative_street_does_not_require_an_optical_tenant(self):
        street = dict(place_id="corridor-au-test", canonical_name="Public shopping street",
                      place_type="High Street Corridor", official_url="https://example.org/council",
                      last_verified_at="2026-09-28", latitude="-34.95", longitude="138.6",
                      country="Australia", locality="Test", state="SA")
        places = []
        with patch("build_retail_places.read_csv", return_value=[street, dict(street, place_id="place-au-test", place_type="Shopping Centre")]):
            add_official_retail_places(places)
        self.assertEqual(places[0]["location_setting"], "High Street")
        self.assertEqual(places[1]["location_setting"], "Shopping Centre")
        self.assertEqual(places[0]["optical_store_count"], 0)
        self.assertEqual(places[0]["retailers"], [])
        self.assertEqual(places[0]["latitude"], -34.95)

    def test_metric_units_provenance_and_unmatched_assets(self):
        asset = dict(portfolio_asset_id="source-a", matched_place_id="centre-a",
                     status="ACTIVE", gla_sqm="83000", tenancy_count="307",
                     annual_visits_m="14", source_url="https://example.org/asset",
                     source_date="2026-02-24", last_verified_at="2026-09-02",
                     confidence="High")
        metrics = portfolio_metrics([
            dict(asset, matched_place_id="", gla_sqm="999999"),
            dict(asset, status="RETIRED", gla_sqm="999999"), asset,
            dict(asset, portfolio_asset_id="source-b", gla_sqm="999999"),
        ])
        self.assertEqual(set(metrics), {"centre-a"})
        self.assertEqual(metrics["centre-a"]["annual_visits"], 14_000_000)
        self.assertEqual(metrics["centre-a"]["gla_sqm"], 83_000)
        self.assertEqual(metrics["centre-a"]["tenancy_count"], 307)
        self.assertEqual(metrics["centre-a"]["metric_evidence"]["gla_sqm"]["portfolio_asset_id"], "source-a")
        with self.assertRaises(ValueError):
            portfolio_metrics([dict(asset, gla_sqm="nan")])

    def test_generated_screen_and_property_metrics_agree(self):
        properties = json.loads((ROOT / "data/property_intelligence.json").read_text())["property_summaries"]
        rankings = json.loads((ROOT / "data/lookalike_places.json").read_text())["rankings"]
        checked = set()
        for rows in rankings.values():
            for row in rows:
                if row["location_setting"] != "Shopping Centre":
                    continue
                summary = properties.get(row["place_id"], {})
                fields = [field for field in ("gla_sqm", "annual_visits", "tenancy_count") if field in summary]
                if not fields:
                    continue
                checked.add(row["place_id"])
                self.assertIsNotNone(row["components"]["accessibility_retail_context"], row["place_id"])
                for field in fields:
                    self.assertEqual(row["retail_context_metrics"][field], summary[field], (row["place_id"], field))
                    self.assertEqual(row["retail_context_evidence"][field], summary["metric_evidence"][field])
        self.assertIn("place-au-nsw-westfield-liverpool", checked)
        self.assertIn("place-au-nsw-westfield-parramatta", checked)


if __name__ == "__main__":
    unittest.main()
