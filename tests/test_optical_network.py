#!/usr/bin/env python3
"""Validation tests for the combined optical network data and distance model."""

from __future__ import annotations

import csv
import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "optical_stores.csv"
GEOJSON_PATH = ROOT / "data" / "optical_stores.geojson"
VALID_STATES = {"ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"}
REQUIRED_FIELDS = {
    "retailer",
    "store_id",
    "name",
    "status",
    "state",
    "suburb",
    "postcode",
    "full_address",
    "phone",
    "latitude",
    "longitude",
    "official_url",
    "services",
    "audiology",
    "venue_name",
    "venue_id",
    "location_type",
    "classification_confidence",
    "classification_basis",
    "source_url",
    "fetched_at",
    "store_area_sqm",
    "area_measure",
    "area_source",
    "area_date",
    "area_confidence",
}


def haversine(first: dict, second: dict) -> float:
    radius = 6371.0088
    lat1 = math.radians(float(first["latitude"]))
    lat2 = math.radians(float(second["latitude"]))
    delta_lat = math.radians(float(second["latitude"]) - float(first["latitude"]))
    delta_lon = math.radians(float(second["longitude"]) - float(first["longitude"]))
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


class OpticalNetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with CSV_PATH.open(newline="", encoding="utf-8") as handle:
            cls.rows = list(csv.DictReader(handle))
        cls.geojson = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))

    def test_counts_and_schema_match(self) -> None:
        self.assertEqual(len(self.rows), 802)
        self.assertEqual(len(self.geojson["features"]), 802)
        self.assertEqual(set(self.rows[0]), REQUIRED_FIELDS)
        self.assertEqual(self.geojson["metadata"]["store_count"], 802)

    def test_retailer_counts(self) -> None:
        counts = {
            retailer: sum(row["retailer"] == retailer for row in self.rows)
            for retailer in ("OPSM", "Specsavers", "Bailey Nelson")
        }
        self.assertEqual(counts, {"OPSM": 335, "Specsavers": 399, "Bailey Nelson": 68})

    def test_ids_states_coordinates_and_sources(self) -> None:
        ids = [row["store_id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        for row in self.rows:
            self.assertIn(row["state"], VALID_STATES)
            self.assertTrue(-44.5 <= float(row["latitude"]) <= -9.0)
            self.assertTrue(112.0 <= float(row["longitude"]) <= 154.5)
            self.assertTrue(row["source_url"])
            self.assertTrue(row["fetched_at"])
            self.assertTrue(row["classification_basis"])

    def test_area_provenance_is_explicit(self) -> None:
        valid_measures = {"", "NLA", "GLA", "GFA", "Estimated footprint"}
        for row in self.rows:
            self.assertIn(row["area_measure"], valid_measures)
            if row["store_area_sqm"]:
                self.assertGreater(float(row["store_area_sqm"]), 0)
                self.assertTrue(row["area_source"])
                self.assertTrue(row["area_date"])
                self.assertIn(row["area_confidence"], {"High", "Medium", "Low"})
            else:
                self.assertEqual(row["area_measure"], "")
                self.assertEqual(row["area_source"], "")

    def test_zero_distance_and_symmetry(self) -> None:
        first, second = self.rows[0], self.rows[1]
        self.assertAlmostEqual(haversine(first, first), 0.0, places=9)
        self.assertAlmostEqual(haversine(first, second), haversine(second, first), places=9)

    def test_known_sydney_melbourne_distance(self) -> None:
        sydney = {"latitude": -33.8688, "longitude": 151.2093}
        melbourne = {"latitude": -37.8136, "longitude": 144.9631}
        self.assertGreater(haversine(sydney, melbourne), 710)
        self.assertLess(haversine(sydney, melbourne), 720)

    def test_nearest_ranking_and_radius_bands(self) -> None:
        origin = {"latitude": 0.0, "longitude": 0.0}
        points = [
            {"id": "zero", "latitude": 0.0, "longitude": 0.0},
            {"id": "half", "latitude": 0.004, "longitude": 0.0},
            {"id": "one", "latitude": 0.008, "longitude": 0.0},
            {"id": "two", "latitude": 0.017, "longitude": 0.0},
            {"id": "five", "latitude": 0.044, "longitude": 0.0},
            {"id": "ten", "latitude": 0.089, "longitude": 0.0},
            {"id": "outside", "latitude": 0.1, "longitude": 0.0},
        ]
        ranked = sorted(points, key=lambda point: haversine(origin, point))
        self.assertEqual([point["id"] for point in ranked], [
            "zero", "half", "one", "two", "five", "ten", "outside"
        ])
        expected = {0.5: 2, 1: 3, 2: 4, 5: 5, 10: 6}
        for radius, count in expected.items():
            self.assertEqual(sum(haversine(origin, point) <= radius for point in points), count)

    def test_park_beach_plaza_memberships_are_confirmed(self) -> None:
        park_beach = {
            row["store_id"]: row
            for row in self.rows
            if row["store_id"] in {"opsm-1229", "specsavers-3339"}
        }
        self.assertEqual(set(park_beach), {"opsm-1229", "specsavers-3339"})
        for row in park_beach.values():
            self.assertEqual(row["location_type"], "Shopping Centre")
            self.assertEqual(row["venue_name"], "Park Beach Plaza")
            self.assertEqual(row["venue_id"], "nsw-park-beach-plaza")
            self.assertEqual(row["classification_confidence"], "High")
            self.assertIn("Official Park Beach Plaza directory", row["classification_basis"])

    def test_centre_memberships_require_non_proximity_evidence(self) -> None:
        membership_path = ROOT / "data" / "centre_store_memberships.csv"
        with membership_path.open(newline="", encoding="utf-8") as handle:
            memberships = list(csv.DictReader(handle))
        self.assertEqual(
            len(memberships),
            len({(row["retailer"], row["store_id"]) for row in memberships}),
        )
        for row in memberships:
            self.assertTrue(row["source_url"].startswith("https://"))
            self.assertNotIn("proximity", row["classification_basis"].lower())
            self.assertEqual(row["confidence"], "High")


if __name__ == "__main__":
    unittest.main()
