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
        reclassified_stable_ids = {
            row["place_id"]
            for row in read_csv("place_canonical_overrides.csv")
            if row.get("location_setting") == "High Street"
        }
        for place in self.places:
            if place["location_setting"] == "Shopping Centre":
                self.assertRegex(place["place_id"], r"^place-(au|nz)-[a-z0-9-]+$")
            elif place["place_id"] in reclassified_stable_ids:
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

    def test_rundle_mall_is_a_stable_high_street_precinct_not_a_single_centre(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        rundle = places["place-au-sa-rundle-mall"]
        self.assertEqual(rundle["location_setting"], "High Street")
        self.assertEqual(rundle["place_type"], "High Street Corridor")
        self.assertEqual(rundle["postcode"], "5000")
        memberships = [
            row for row in self.memberships
            if row["place_id"] == "place-au-sa-rundle-mall"
        ]
        self.assertEqual(len(memberships), 4)
        self.assertTrue(all(row["location_setting"] == "High Street" for row in memberships))

    def test_pitt_street_precinct_does_not_absorb_nearby_stores_by_proximity(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        pitt_street = places["place-au-nsw-pitt-street-mall"]
        self.assertEqual(pitt_street["location_setting"], "High Street")
        self.assertEqual(pitt_street["place_type"], "High Street Corridor")
        self.assertEqual(pitt_street["postcode"], "2000")
        self.assertEqual(pitt_street["optical_store_count"], 0)

        memberships = {row["store_id"]: row for row in self.memberships}
        opsm = memberships["opsm-1304"]
        self.assertEqual(opsm["place_id"], "corridor-au-nsw-sydney-george-street")
        self.assertEqual(opsm["location_setting"], "High Street")
        self.assertEqual(opsm["mapping_confidence"], "High")

        specsavers = memberships["specsavers-3581"]
        self.assertEqual(specsavers["place_id"], "place-au-nsw-westfield-sydney")
        self.assertEqual(specsavers["location_setting"], "Shopping Centre")
        self.assertEqual(specsavers["mapping_confidence"], "High")

        westfield = places["place-au-nsw-westfield-sydney"]
        self.assertIn("Specsavers", westfield["retailers"])
        self.assertIn("Bailey Nelson", westfield["retailers"])

    def test_balgowlah_village_preserves_the_legacy_place_id_and_alias(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        balgowlah = places["place-au-nsw-balgowlah-shopping-centre"]
        self.assertEqual(balgowlah["name"], "Balgowlah Village")
        self.assertEqual(balgowlah["postcode"], "2093")
        self.assertIn("Stockland Balgowlah", balgowlah["aliases"])

    def test_current_runaway_bay_and_sugarland_names_preserve_stable_ids(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        runaway_bay = places["place-au-qld-runaway-bay-shopping-village"]
        self.assertEqual(runaway_bay["name"], "Runaway Bay Centre")
        self.assertIn("Runaway Bay Shopping Village", runaway_bay["aliases"])
        self.assertEqual(runaway_bay["postcode"], "4216")

        sugarland = places["place-au-qld-sugarland-shoppingtown"]
        self.assertEqual(sugarland["name"], "Sugarland Plaza")
        self.assertIn("Sugarland Shoppingtown", sugarland["aliases"])
        self.assertIn("Stockland Bundaberg", sugarland["aliases"])
        self.assertEqual(sugarland["postcode"], "4670")

    def test_current_priority_centre_names_and_addresses_are_publicly_resolved(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        casuarina = places["place-au-nt-casuarina-square"]
        self.assertEqual(casuarina["name"], "Casuarina Square")
        self.assertEqual(casuarina["address"], "247 Trower Road")
        self.assertEqual(casuarina["postcode"], "0810")

        rosebud = places["place-au-vic-rosebud-plaza-shopping-centre"]
        self.assertEqual(rosebud["name"], "Rosebud Plaza")
        self.assertIn("Rosebud Plaza Shopping Centre", rosebud["aliases"])
        self.assertEqual(rosebud["postcode"], "3939")

        winston_hills = places["place-au-nsw-winston-hills-mall"]
        self.assertEqual(winston_hills["address"], "180-192 Caroline Chisholm Drive")
        self.assertEqual(winston_hills["postcode"], "2153")

    def test_current_wa_priority_centre_names_and_addresses_are_publicly_resolved(self) -> None:
        places = {place["place_id"]: place for place in self.places}

        bunbury = places["place-au-wa-bunbury-centrepoint"]
        self.assertEqual(bunbury["name"], "Centuria Bunbury Centrepoint")
        self.assertIn("Bunbury Centrepoint", bunbury["aliases"])
        self.assertEqual(bunbury["address"], "60 Blair Street")
        self.assertEqual(bunbury["postcode"], "6230")

        livingston = places["place-au-wa-livingston-marketplace"]
        self.assertEqual(livingston["name"], "Livingston Marketplace")
        self.assertEqual(livingston["address"], "Corner Ranford and Nicholson Roads")
        self.assertEqual(livingston["postcode"], "6155")

        maddington = places["place-au-wa-maddington-centro-shopping-centre"]
        self.assertEqual(maddington["name"], "Maddington Central")
        self.assertIn("Maddington Centro Shopping Centre", maddington["aliases"])
        self.assertEqual(maddington["address"], "Corner Burslem Drive and Attfield Street")
        self.assertEqual(maddington["postcode"], "6109")

    def test_current_plumpton_and_dandenong_names_preserve_stable_ids(self) -> None:
        places = {place["place_id"]: place for place in self.places}

        plumpton = places["place-au-nsw-plumpton-marketplace"]
        self.assertEqual(plumpton["name"], "HomeCo Plumpton Marketplace")
        self.assertIn("Plumpton Marketplace", plumpton["aliases"])
        self.assertEqual(plumpton["address"], "260 Jersey Road")
        self.assertEqual(plumpton["postcode"], "2761")

        dandenong = places["place-au-vic-dandenong-square"]
        self.assertEqual(dandenong["name"], "Dandenong Square")
        self.assertIn("Dandenong Plaza", dandenong["aliases"])
        self.assertEqual(dandenong["address"], "Corner McCrae and Walker Streets")
        self.assertEqual(dandenong["postcode"], "3175")

    def test_northam_mitcham_and_bridge_mall_use_current_place_types(self) -> None:
        places = {place["place_id"]: place for place in self.places}

        northam = places["place-au-wa-northam-boulevard-shopping-centre"]
        self.assertEqual(northam["name"], "Northam Boulevard")
        self.assertEqual(northam["address"], "171 Fitzgerald Street East")
        self.assertEqual(northam["postcode"], "6401")

        mitcham = places["place-au-sa-mitcham-shopping-centre"]
        self.assertEqual(mitcham["name"], "Mitcham Square")
        self.assertIn("Mitcham Shopping Centre", mitcham["aliases"])
        self.assertEqual(mitcham["address"], "119 Belair Road")
        self.assertEqual(mitcham["postcode"], "5062")

        bridge_mall = places["place-au-vic-ballarat-bridge-mall"]
        self.assertEqual(bridge_mall["name"], "Bridge Mall")
        self.assertEqual(bridge_mall["location_setting"], "High Street")
        self.assertEqual(bridge_mall["place_type"], "High Street Corridor")
        self.assertEqual(bridge_mall["postcode"], "3350")
        memberships = [
            row for row in self.memberships
            if row["place_id"] == "place-au-vic-ballarat-bridge-mall"
        ]
        self.assertEqual(len(memberships), 2)
        self.assertTrue(all(row["location_setting"] == "High Street" for row in memberships))

    def test_current_lismore_kingaroy_and_sa_priority_names_preserve_stable_ids(self) -> None:
        places = {place["place_id"]: place for place in self.places}

        lismore = places["place-au-nsw-lismore-shopping-centre"]
        self.assertEqual(lismore["name"], "Lismore Square")
        self.assertIn("Lismore Shopping Centre", lismore["aliases"])
        self.assertEqual(lismore["address"], "Corner Brewster and Uralba Streets")
        self.assertEqual(lismore["postcode"], "2480")

        kingaroy = places["place-au-qld-kingaroy-plaza"]
        self.assertEqual(kingaroy["name"], "Kingaroy Mall")
        self.assertIn("Kingaroy Shoppingworld", kingaroy["aliases"])
        self.assertEqual(kingaroy["address"], "Corner Youngman and Alford Streets")
        self.assertEqual(kingaroy["postcode"], "4610")

        brickworks = places["place-au-sa-brickworks-marketplace"]
        self.assertEqual(brickworks["address"], "38 South Road")
        self.assertEqual(brickworks["postcode"], "5031")

        westland = places["place-au-sa-whyalla-westland-shopping-centre"]
        self.assertEqual(westland["name"], "Westland Whyalla")
        self.assertIn("Westland Shopping Centre", westland["aliases"])
        self.assertEqual(westland["address"], "McDouall Stuart Avenue")
        self.assertEqual(westland["postcode"], "5608")

        northcote = places["place-au-vic-northcote-plaza"]
        self.assertEqual(northcote["address"], "25 Separation Street")
        self.assertEqual(northcote["postcode"], "3070")

    def test_cuba_mall_is_a_high_street_corridor_not_a_shopping_centre(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        cuba_mall = places["place-nz-wellington-cnr-cuba-mall-and-dixon-street"]
        self.assertEqual(cuba_mall["name"], "Cuba Street / Cuba Mall")
        self.assertEqual(cuba_mall["location_setting"], "High Street")
        self.assertEqual(cuba_mall["place_type"], "High Street Corridor")
        self.assertEqual(cuba_mall["address"], "83 Cuba Street")
        self.assertEqual(cuba_mall["postcode"], "6011")
        memberships = [
            row for row in self.memberships
            if row["place_id"] == "place-nz-wellington-cnr-cuba-mall-and-dixon-street"
        ]
        self.assertEqual(len(memberships), 2)
        self.assertTrue(all(row["location_setting"] == "High Street" for row in memberships))

    def test_current_charter_hall_nsw_batch_has_complete_public_addresses(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        expected = {
            "place-au-nsw-armidale-central": ("225 Beardy Street", "Armidale", "2350"),
            "place-au-nsw-carnes-hill-marketplace": (
                "Corner Cowpasture and Kurrajong Roads",
                "Horningsea Park",
                "2171",
            ),
            "place-au-nsw-chullora-marketplace": ("355 Waterloo Road", "Greenacre", "2190"),
            "place-au-nsw-highlands-marketplace": ("197 Old Hume Highway", "Mittagong", "2575"),
        }
        for place_id, (address, locality, postcode) in expected.items():
            with self.subTest(place_id=place_id):
                place = places[place_id]
                self.assertEqual(place["address"], address)
                self.assertEqual(place["locality"], locality)
                self.assertEqual(place["postcode"], postcode)
                self.assertEqual(place["location_setting"], "Shopping Centre")
                self.assertEqual(place["place_type"], "Shopping Centre")

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
