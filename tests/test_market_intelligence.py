#!/usr/bin/env python3
"""Validation tests for public leasing intelligence datasets and privacy boundary."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PRIVATE_KEYS = {
    "asking_rent",
    "base_rent",
    "outgoings",
    "incentive",
    "lease_expiry",
    "option_notice_date",
    "negotiation_notes",
    "sales_performance",
    "turnover",
    "private_contact",
}


class MarketIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.markets = json.loads((DATA / "sa2_market.geojson").read_text())
        cls.links = json.loads((DATA / "store_market_links.json").read_text())
        cls.centres = json.loads((DATA / "centres.json").read_text())
        cls.events = json.loads((DATA / "network_events.json").read_text())

    def test_abs_market_layer(self) -> None:
        self.assertEqual(self.markets["metadata"]["feature_count"], 2454)
        self.assertEqual(len(self.markets["features"]), 2454)
        self.assertIn("Australian Bureau of Statistics", self.markets["metadata"]["source"])
        self.assertTrue(self.markets["metadata"]["source_release_date"])
        populated = [
            feature
            for feature in self.markets["features"]
            if feature["properties"].get("population_2025") is not None
        ]
        self.assertGreater(len(populated), 2400)
        required = {
            "sa2_code",
            "sa2_name",
            "population_2025",
            "population_growth_2021_2025_pct",
            "median_age_2021",
            "age_45_plus_pct_2021",
            "median_household_income_weekly_2021",
            "unemployment_rate_2021",
            "retail_businesses_2025",
            "health_businesses_2025",
            "source_url",
            "confidence",
        }
        self.assertTrue(required.issubset(populated[0]["properties"]))

    def test_all_stores_join_to_sa2(self) -> None:
        self.assertEqual(self.links["metadata"]["store_count"], 1491)
        self.assertEqual(self.links["metadata"]["matched_count"], 1269)
        self.assertEqual(len(self.links["links"]), 1491)
        australian = [link for link in self.links["links"].values() if link.get("geography_system") != "Stats NZ"]
        new_zealand = [link for link in self.links["links"].values() if link.get("geography_system") == "Stats NZ"]
        self.assertEqual(len(australian), 1269)
        self.assertEqual(len(new_zealand), 222)
        self.assertTrue(all(link["sa2_code"] for link in australian))
        self.assertTrue(all(not link["sa2_code"] for link in new_zealand))

    def test_centre_entities_and_curated_profile(self) -> None:
        self.assertEqual(self.centres["metadata"]["centre_count"], 394)
        self.assertEqual(len(self.centres["centres"]), 394)
        chadstone = next(
            centre for centre in self.centres["centres"] if centre["centre_id"] == "vic-chadstone"
        )
        self.assertEqual(chadstone["confidence"], "High")
        self.assertGreater(chadstone["gla_sqm"], 200_000)
        self.assertGreater(chadstone["annual_visits"], 10_000_000)
        self.assertTrue(chadstone["public_url"])
        park_beach = next(
            centre
            for centre in self.centres["centres"]
            if centre["centre_id"] == "nsw-park-beach-plaza"
        )
        self.assertEqual(park_beach["name"], "Park Beach Plaza")
        self.assertEqual(park_beach["optical_store_count"], 2)
        self.assertEqual(set(park_beach["retailers"]), {"OPSM", "Specsavers"})
        self.assertEqual(park_beach["confidence"], "High")
        self.assertEqual(park_beach["source_basis"], "Verified public shopping-centre registry")
        self.assertEqual(park_beach["public_url"], "https://www.parkbeachplaza.com.au/")

    def test_network_history_snapshot(self) -> None:
        self.assertEqual(self.events["event_count"], len(self.events["events"]))
        for scope in self.events.get("coverage_baselines_added", []):
            self.assertFalse(
                any(
                    event["type"] == "Opened"
                    and event["retailer"] == scope["retailer"]
                    and event.get("country", "Australia") == scope["country"]
                    for event in self.events["events"]
                )
            )
        snapshots = list((DATA / "history").glob("*.json"))
        self.assertTrue(snapshots)
        latest = json.loads(sorted(snapshots)[-1].read_text())
        self.assertEqual(len(latest["stores"]), 1491)

    def test_public_json_contains_no_private_fields(self) -> None:
        for path in DATA.rglob("*.json"):
            text = path.read_text(encoding="utf-8")
            payload = json.loads(text)
            stack = [payload]
            while stack:
                value = stack.pop()
                if isinstance(value, dict):
                    self.assertFalse(PRIVATE_KEYS.intersection(value), f"Private key in {path}")
                    stack.extend(value.values())
                elif isinstance(value, list):
                    stack.extend(value)


if __name__ == "__main__":
    unittest.main()
