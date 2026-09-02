#!/usr/bin/env python3
"""Acceptance tests for canonical places, mappings, corridors and lookalike ranks."""

from __future__ import annotations

import csv
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NAMED = {"OPSM", "Specsavers", "Bailey Nelson", "Oscar Wylee"}
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


def read_csv(name: str) -> list[dict]:
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def named_source_count() -> int:
    total = 0
    for folder in NAMED_SOURCE_FOLDERS:
        with (ROOT / "retailers" / folder / "stores.csv").open(newline="", encoding="utf-8") as handle:
            total += sum(1 for _ in csv.DictReader(handle))
    return total


class RetailPlaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.places_payload = json.loads((DATA / "retail_places.json").read_text(encoding="utf-8"))
        cls.places = cls.places_payload["places"]
        cls.memberships = read_csv("store_place_memberships.csv")
        cls.reviews = read_csv("place_review.csv")
        cls.lookalikes = json.loads((DATA / "lookalike_places.json").read_text(encoding="utf-8"))

    def test_canonical_ids_are_unique_and_typed(self) -> None:
        ids = [place["place_id"] for place in self.places]
        self.assertEqual(len(ids), len(set(ids)))
        for place in self.places:
            if place["location_setting"] == "Shopping Centre":
                self.assertRegex(place["place_id"], r"^place-(au|nz)-[a-z0-9-]+$")
            else:
                self.assertRegex(place["place_id"], r"^corridor-(au|nz)-[a-z0-9-]+$")
            self.assertTrue(-90 <= float(place["latitude"]) <= 90)
            self.assertTrue(-180 <= float(place["longitude"]) <= 180)

    def test_named_network_is_usable_and_place_safe(self) -> None:
        named = [row for row in self.memberships if row["retailer"] in NAMED]
        self.assertEqual(len(named), named_source_count())
        self.assertTrue(all(row["usable_for_network"] == "true" for row in named))
        self.assertTrue(all(row["location_setting"] for row in named))
        place_ids = {place["place_id"] for place in self.places}
        for row in named:
            if row["location_setting"] in {"Shopping Centre", "High Street"}:
                self.assertIn(row["place_id"], place_ids)
            elif row["location_setting"] == "Uncertain":
                self.assertEqual(row["review_status"], "Needs review")

    def test_bailey_first_pass_is_complete(self) -> None:
        bailey = [row for row in self.memberships if row["retailer"] == "Bailey Nelson"]
        self.assertEqual(len(bailey), 82)
        self.assertTrue(all(row["review_status"] == "Accepted" for row in bailey))
        self.assertTrue(all(row["location_setting"] in {"Shopping Centre", "High Street"} for row in bailey))
        self.assertTrue(all(row["place_id"] for row in bailey))
        self.assertFalse(any(row["retailer"] == "Bailey Nelson" for row in self.reviews))

    def test_reviewed_consultant_examples_have_defensible_places(self) -> None:
        memberships = {row["store_id"]: row for row in self.memberships}
        expected = {
            "opsm-1121": ("Shopping Centre", "Marketplace Gungahlin"),
            "specsavers-3583": ("Shopping Centre", "Marketplace Gungahlin"),
            "specsavers-3657": ("Shopping Centre", "Cooleman Court"),
            "specsavers-nz-3841": ("Shopping Centre", "Silverdale Mall"),
            "opsm-nz-2353": ("Shopping Centre", "Silverdale Centre"),
            "specsavers-3469": ("High Street", "Manning Street"),
            "specsavers-nz-3853": ("High Street", "The Strand"),
        }
        for store_id, (setting, place_name) in expected.items():
            with self.subTest(store_id=store_id):
                row = memberships[store_id]
                self.assertEqual(row["location_setting"], setting)
                self.assertEqual(row["place_name"], place_name)
                self.assertEqual(row["review_status"], "Accepted")

        silverdale = next(place for place in self.places if place["name"] == "Silverdale Mall")
        self.assertEqual(silverdale["owner"], "Millwater Park Limited")
        self.assertEqual(silverdale["manager"], "Barfoot & Thompson Commercial")

        silverdale_centre = next(place for place in self.places if place["name"] == "Silverdale Centre")
        self.assertEqual(silverdale_centre["owner"], "Stride Property Limited")
        self.assertEqual(silverdale_centre["manager"], "Stride Property Limited")

        whakatane_opsm = memberships["opsm-nz-2830"]
        self.assertEqual(whakatane_opsm["review_status"], "Accepted")
        self.assertEqual(whakatane_opsm["location_setting"], "High Street")
        self.assertEqual(whakatane_opsm["place_id"], "corridor-nz-bay-of-plenty-whakatane-the-strand")

    def test_promoted_review_queue_has_no_named_network_exceptions(self) -> None:
        self.assertEqual(self.reviews, [])

    def test_known_duplicate_westfield_tenants_share_one_canonical_place(self) -> None:
        memberships = {row["store_id"]: row for row in self.memberships}
        groups = [
            ["bailey-nelson-carindale", "opsm-1266", "oscar-wylee-18", "specsavers-3246"],
            ["bailey-nelson-chermside", "opsm-1346", "oscar-wylee-21", "specsavers-3393"],
            ["bailey-nelson-southland", "opsm-1407", "oscar-wylee-57", "specsavers-3218"],
            ["bailey-nelson-carousel", "opsm-1366", "oscar-wylee-61", "specsavers-3349"],
        ]
        for store_ids in groups:
            present = [memberships[store_id]["place_id"] for store_id in store_ids if store_id in memberships]
            self.assertGreaterEqual(len(present), 3)
            self.assertEqual(len(set(present)), 1)

        westpoint = [
            row["place_id"] for row in self.memberships
            if "westpoint" in row["store_name"].lower() or row["place_name"] == "Westpoint Shopping Centre"
        ]
        self.assertGreaterEqual(len(westpoint), 2)
        self.assertEqual(set(westpoint), {"place-au-nsw-westpoint-shopping-centre"})

    def test_capalaba_park_duplicate_is_consolidated(self) -> None:
        expected_place_id = "place-au-qld-capalaba-park-shopping-centre"
        capalaba = [
            row for row in self.memberships
            if row["store_id"] in {"opsm-1246", "specsavers-3374", "oscar-wylee-131"}
        ]
        self.assertEqual(len(capalaba), 3)
        self.assertEqual({row["place_id"] for row in capalaba}, {expected_place_id})
        self.assertEqual({row["place_name"] for row in capalaba}, {"Capalaba Park Shopping Centre"})
        remaps = read_csv("place_id_remaps.csv")
        self.assertIn(
            {
                "previous_place_id": "place-au-qld-capalaba-park-shopping-centre-corner-redland-bay-mt-cotton-roads-capalaba-qld-4157",
                "canonical_place_id": expected_place_id,
                "reason": "Evidence-backed place identity consolidation",
            },
            remaps,
        )

    def test_current_place_names_preserve_legacy_aliases_and_ids(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        townsville = places["place-au-qld-stockland-townsville"]
        self.assertEqual(townsville["name"], "Townsville Shopping Centre")
        self.assertIn("Stockland Townsville", townsville["aliases"])
        riverton = places["place-au-wa-riverton-stockland"]
        self.assertEqual(riverton["name"], "Riverton Forum")
        self.assertIn("Stockland Riverton", riverton["aliases"])
        werribee = places["place-au-vic-werribee-plaza"]
        self.assertEqual(werribee["name"], "Pacific Werribee")
        self.assertIn("Werribee Plaza", werribee["aliases"])
        self.assertEqual(places["place-au-vic-cranbourne-park-shopping-centre-sp107"]["name"], "Cranbourne Park")
        self.assertEqual(places["place-au-wa-joondalup-lakeside-s-city"]["name"], "Lakeside Joondalup")
        self.assertEqual(places["place-au-vic-broadmeadows-shopping-centre"]["name"], "Broadmeadows Central")
        self.assertEqual(places["place-au-sa-elizabeth-shopping-centre"]["name"], "Elizabeth City Centre")
        self.assertEqual(places["place-au-qld-cleveland-shopping-centre"]["name"], "Cleveland Central")
        self.assertEqual(places["place-au-wa-clarkson-ocean-keys-shopping-centre"]["name"], "Ocean Keys Shopping Centre")
        self.assertIn(
            "Clarkson Ocean Keys Shopping Centre",
            places["place-au-wa-clarkson-ocean-keys-shopping-centre"]["aliases"],
        )
        self.assertEqual(places["place-au-nsw-forster-stockland"]["name"], "Stockland Forster")
        self.assertEqual(places["place-au-qld-burleigh-heads-stockland"]["name"], "Stockland Burleigh Heads")
        self.assertEqual(places["place-au-nsw-shellharbour-stockland"]["name"], "Stockland Shellharbour")
        self.assertEqual(places["place-au-qld-stocklands-hervey-bay"]["name"], "Stockland Hervey Bay")
        self.assertEqual(places["place-au-vic-point-cook-town-centre"]["name"], "Stockland Point Cook")
        self.assertEqual(places["place-au-vic-wendouree-stockland"]["name"], "Stockland Wendouree")
        self.assertEqual(places["place-au-wa-harrisdale-stockland-shopping-centre"]["name"], "Stockland Harrisdale")
        self.assertEqual(places["place-au-unknown-stockland-birtinya"]["state"], "QLD")
        self.assertEqual(places["place-au-vic-keysborough-parkmore-shopping-centre"]["name"], "Parkmore Shopping Centre")
        self.assertIn(
            "Keysborough Parkmore Shopping Centre",
            places["place-au-vic-keysborough-parkmore-shopping-centre"]["aliases"],
        )
        self.assertEqual(places["place-au-wa-cockburn-gateway-shopping-centre"]["name"], "Cockburn Gateway")
        self.assertEqual(places["place-au-unknown-croydon-central"]["state"], "VIC")
        self.assertEqual(places["place-au-unknown-jesmond-central"]["state"], "NSW")

    def test_authoritative_places_can_exist_without_optical_tenants(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        for place_id, expected_name in {
            "place-au-nsw-wallsend-village": "Wallsend Village",
            "place-au-qld-the-station-oxley": "The Station Oxley",
        }.items():
            with self.subTest(place_id=place_id):
                place = places[place_id]
                self.assertEqual(place["name"], expected_name)
                self.assertEqual(place["optical_store_count"], 0)
                self.assertEqual(place["confidence"], "High")
                self.assertTrue(place["official_url"].startswith("https://"))

    def test_lookalikes_are_separated_and_exclude_bailey_places(self) -> None:
        self.assertEqual(
            set(self.lookalikes["rankings"]),
            {"au-shopping-centre", "au-high-street", "nz-shopping-centre", "nz-high-street"},
        )
        self.assertEqual(len(self.lookalikes["bailey_benchmarks"]), 82)
        bailey_place_ids = {place["place_id"] for place in self.places if place["has_bailey"]}
        for key, rows in self.lookalikes["rankings"].items():
            country, setting = key.split("-", 1)
            for index, row in enumerate(rows, start=1):
                self.assertEqual(row["rank"], index)
                self.assertNotIn(row["place_id"], bailey_place_ids)
                self.assertEqual(row["country"], "Australia" if country == "au" else "New Zealand")
                self.assertEqual(row["location_setting"], "Shopping Centre" if setting == "shopping-centre" else "High Street")
                self.assertTrue(0 <= row["screening_completeness"] <= 100)
                self.assertIn("market_features", row)


if __name__ == "__main__":
    unittest.main()
