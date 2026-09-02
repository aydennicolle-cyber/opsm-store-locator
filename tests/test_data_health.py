#!/usr/bin/env python3
"""Tests for census certification, source health, and retail-place inventory."""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NAMED_SOURCE_FOLDERS = (
    "opsm",
    "opsm-nz",
    "specsavers",
    "specsavers-nz",
    "bailey-nelson",
    "bailey-nelson-nz",
    "oscar-wylee",
    "oscar-wylee-nz",
)


def named_source_count() -> int:
    total = 0
    for folder in NAMED_SOURCE_FOLDERS:
        with (ROOT / "retailers" / folder / "stores.csv").open(newline="", encoding="utf-8") as handle:
            total += sum(1 for _ in csv.DictReader(handle))
    return total


class DataHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.health = json.loads((DATA / "data_health.json").read_text(encoding="utf-8"))
        cls.places = json.loads((DATA / "retail_places.json").read_text(encoding="utf-8"))
        with (DATA / "optical_stores.csv").open(newline="", encoding="utf-8") as handle:
            cls.stores = list(csv.DictReader(handle))
        with (DATA / "store_certification.csv").open(newline="", encoding="utf-8") as handle:
            cls.certification = list(csv.DictReader(handle))

    def test_health_dimensions_and_baselines_are_explicit(self) -> None:
        self.assertEqual(
            set(self.health["dimensions"]),
            {
                "source_freshness",
                "usable_store_coverage",
                "location_setting_coverage",
                "place_mapping_coverage",
                "review_reconciliation",
            },
        )
        self.assertEqual(self.health["baselines"], {"stores": 1491, "places": 394})
        self.assertIn("best-available public store data", self.health["coverage_statement"])

    def test_every_observed_store_has_certification(self) -> None:
        store_ids = {row["store_id"] for row in self.stores}
        certification_ids = {row["store_id"] for row in self.certification}
        self.assertEqual(certification_ids, store_ids)
        self.assertEqual(set(self.health["store_certification"]), store_ids)
        self.assertEqual(self.health["observed"]["stores"], len(store_ids))
        for row in self.certification:
            self.assertIn(row["operational_status"], {"Usable", "Needs review", "Limited"})
            self.assertIn(row["location_setting"], {"Shopping Centre", "High Street", "Other", "Uncertain"})
        named = [row for row in self.certification if row["retailer"] in {"OPSM", "Specsavers", "Bailey Nelson", "Oscar Wylee"}]
        self.assertEqual(len(named), named_source_count())
        self.assertTrue(all(row["usable_for_network"] == "true" for row in named))

    def test_declared_sources_have_health_results(self) -> None:
        manifest = json.loads((DATA / "source_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual({source["id"] for source in manifest["sources"]}, {source["id"] for source in self.health["sources"]})
        for source in self.health["sources"]:
            self.assertIn(source["status"], {"current", "stale", "partial", "missing"})
            self.assertGreater(source["max_age_days"], 0)

    def test_retail_places_have_canonical_schema(self) -> None:
        places = self.places["places"]
        self.assertEqual(self.places["metadata"]["place_count"], len(places))
        self.assertEqual(len({place["place_id"] for place in places}), len(places))
        required = {
            "place_id",
            "name",
            "place_type",
            "country",
            "state",
            "latitude",
            "longitude",
            "aliases",
            "status",
            "certification_status",
            "evidence_tier",
            "location_setting",
            "mapping_confidence",
        }
        self.assertTrue(required.issubset(places[0]))

    def test_property_health_is_separate_from_store_health(self) -> None:
        property_health = self.health["property_intelligence"]
        self.assertEqual(
            set(property_health["dimensions"]),
            {
                "research_coverage", "relationship_freshness", "centre_class_coverage",
                "bailey_centre_research_coverage", "bailey_centre_class_coverage",
                "conflict_reconciliation",
            },
        )
        self.assertNotIn("research_coverage", self.health["dimensions"])
        self.assertGreaterEqual(property_health["counts"]["groups"], 26)
        self.assertGreater(property_health["counts"]["relationships"], 0)
        self.assertEqual(property_health["counts"]["researched_bailey_centres"], property_health["counts"]["bailey_centres"])
        self.assertEqual(property_health["counts"]["classed_bailey_centres"], property_health["counts"]["bailey_centres"])
        self.assertEqual(property_health["counts"]["unmatched_active_portfolio_assets"], 0)
        self.assertEqual(property_health["counts"]["development_assets"], 1)


if __name__ == "__main__":
    unittest.main()
