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
VALID_NZ_REGIONS = {
    "Auckland",
    "Bay of Plenty",
    "Canterbury",
    "Gisborne",
    "Hawke's Bay",
    "Manawatu-Whanganui",
    "Marlborough",
    "Nelson",
    "Northland",
    "Otago",
    "Southland",
    "Taranaki",
    "Tasman",
    "Waikato",
    "Wellington",
    "West Coast",
}
REQUIRED_FIELDS = {
    "retailer",
    "store_id",
    "affiliations",
    "name",
    "status",
    "country",
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
        self.assertGreater(len(self.rows), 0)
        self.assertEqual(len(self.geojson["features"]), len(self.rows))
        self.assertEqual(set(self.rows[0]), REQUIRED_FIELDS)
        self.assertEqual(self.geojson["metadata"]["store_count"], len(self.rows))

    def test_retailer_counts(self) -> None:
        registry = json.loads((ROOT / "data" / "retailer_registry.json").read_text(encoding="utf-8"))["retailers"]
        counts = {
            item["name"]: sum(row["retailer"] == item["name"] for row in self.rows)
            for item in registry
        }
        expected = {}
        for item in registry:
            total = 0
            for folder in item["source_folders"]:
                with (ROOT / "retailers" / folder / "stores.csv").open(newline="", encoding="utf-8") as handle:
                    total += sum(1 for _ in csv.DictReader(handle))
            expected[item["name"]] = total
        remaps = []
        for path in (ROOT / "data" / "store_identity_remaps.csv", ROOT / "data" / "provision_identity_remaps.csv"):
            with path.open(newline="", encoding="utf-8") as handle:
                remaps.extend(csv.DictReader(handle))
        with (ROOT / "retailers" / "provision" / "stores.csv").open(newline="", encoding="utf-8") as handle:
            expected["Independent / Other optical"] += sum(1 for _ in csv.DictReader(handle))
        for remap in remaps:
            source = remap["source_store_id"]
            retailer = next(item for item in registry if source.startswith(f"{item['slug']}-"))
            expected[retailer["name"]] -= 1
        self.assertEqual(counts, expected)
        countries = {country: sum(row["country"] == country for row in self.rows) for country in ("Australia", "New Zealand")}
        self.assertEqual(sum(countries.values()), len(self.rows))
        bailey_nz = [
            row for row in self.rows if row["retailer"] == "Bailey Nelson" and row["country"] == "New Zealand"
        ]
        self.assertEqual(len(bailey_nz), 14)
        self.assertTrue(all(row["status"] == "Active" for row in bailey_nz))

    def test_retailer_registry_and_identity_remaps(self) -> None:
        registry = json.loads((ROOT / "data" / "retailer_registry.json").read_text(encoding="utf-8"))["retailers"]
        names = [item["name"] for item in registry]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue({
            "George & Matilda", "Eyecare Plus", "Optical Superstore", "1001 Optometry",
            "EyeQ Optometrists", "Laubman & Pank",
        }.issubset(names))
        additional = [item for item in registry if item["network_type"] == "additional"]
        self.assertTrue(all(not item["default_visible"] for item in additional))
        self.assertTrue(all(item["min_marker_zoom"] >= 8 for item in additional))
        ids = {row["store_id"] for row in self.rows}
        remaps = []
        for path in (ROOT / "data" / "store_identity_remaps.csv", ROOT / "data" / "provision_identity_remaps.csv"):
            with path.open(newline="", encoding="utf-8") as handle:
                remaps.extend(csv.DictReader(handle))
        self.assertTrue(remaps)
        self.assertTrue(all(row["source_store_id"] not in ids for row in remaps))
        self.assertTrue(all(row["canonical_store_id"] in ids for row in remaps))

    def test_additional_network_logos_are_local_assets(self) -> None:
        registry = json.loads((ROOT / "data" / "retailer_registry.json").read_text(encoding="utf-8"))["retailers"]
        additional = [item for item in registry if item["network_type"] == "additional"]
        self.assertEqual(len(additional), 6)
        for item in additional:
            logo = item.get("logo", "")
            self.assertTrue(logo.startswith("assets/"), item["name"])
            self.assertTrue((ROOT / logo).is_file(), item["name"])

    def test_provision_is_an_affiliation_not_a_retailer(self) -> None:
        self.assertNotIn("ProVision", {row["retailer"] for row in self.rows})
        affiliated = [row for row in self.rows if "provision" in row["affiliations"].split("|")]
        self.assertGreater(len(affiliated), 300)
        self.assertTrue(all(row["country"] == "Australia" for row in affiliated))

    def test_ids_states_coordinates_and_sources(self) -> None:
        ids = [row["store_id"] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        for row in self.rows:
            if row["country"] == "Australia":
                self.assertIn(row["state"], VALID_STATES)
                self.assertTrue(-44.5 <= float(row["latitude"]) <= -9.0)
                self.assertTrue(112.0 <= float(row["longitude"]) <= 154.5)
            else:
                self.assertEqual(row["country"], "New Zealand")
                self.assertIn(row["state"], VALID_NZ_REGIONS)
                self.assertTrue(-48.0 <= float(row["latitude"]) <= -33.5)
                self.assertTrue(165.0 <= float(row["longitude"]) <= 179.5)
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
