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

    def test_salamander_deepwater_and_crown_memberships_follow_current_public_evidence(self) -> None:
        places = {place["place_id"]: place for place in self.places}

        salamander = places["place-au-nsw-salamander-shopping-centre"]
        self.assertEqual(salamander["name"], "Salamander Bay Square")
        self.assertEqual(salamander["address"], "2 Town Centre Circuit")
        self.assertNotIn("place-au-nsw-town-centre-circuit", places)
        salamander_memberships = [
            row for row in self.memberships
            if row["place_id"] == "place-au-nsw-salamander-shopping-centre"
        ]
        self.assertEqual(
            {row["store_id"] for row in salamander_memberships},
            {"opsm-1375", "specsavers-3563"},
        )

        deepwater = places["place-au-nsw-deepwater-plaza-centre"]
        self.assertEqual(deepwater["name"], "Deepwater Plaza")
        self.assertEqual(deepwater["postcode"], "2256")
        deepwater_memberships = [
            row for row in self.memberships
            if row["place_id"] == "place-au-nsw-deepwater-plaza-centre"
        ]
        self.assertEqual(
            {row["store_id"] for row in deepwater_memberships},
            {"opsm-1311", "specsavers-3538"},
        )
        self.assertTrue(all(row["location_setting"] == "Shopping Centre" for row in deepwater_memberships))

        crown = places["place-au-nsw-crown-st-mall"]
        self.assertEqual(crown["name"], "Crown Street Mall")
        self.assertEqual(crown["location_setting"], "High Street")
        self.assertEqual(crown["place_type"], "High Street Corridor")
        crown_memberships = [
            row for row in self.memberships
            if row["place_id"] == "place-au-nsw-crown-st-mall"
        ]
        self.assertEqual({row["store_id"] for row in crown_memberships}, {"specsavers-3456"})
        self.assertTrue(all(row["location_setting"] == "High Street" for row in crown_memberships))

        rockdale = places["place-au-nsw-rockdale-plaza-drive"]
        self.assertEqual(rockdale["name"], "Rockdale Plaza")
        self.assertEqual(rockdale["address"], "1 Rockdale Plaza Drive")
        self.assertEqual(rockdale["postcode"], "2216")

    def test_lake_haven_riverside_glendale_and_grafton_use_current_public_records(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        expected = {
            "place-au-nsw-glendale-stockland-shopping-centre": (
                "Glendale City Centre", "387 Lake Road", "2285"
            ),
            "place-au-nsw-grafton-shoppingworld": (
                "Grafton Shoppingworld", "52-74 Fitzroy Street", "2460"
            ),
            "place-au-nsw-lake-haven-shopping-centre": (
                "Lake Haven Centre", "Corner Lake Haven Drive and Goobarabah Avenue", "2263"
            ),
            "place-au-nsw-riverside-plaza-queanbeyan": (
                "Riverside Plaza", "131 Monaro Street", "2620"
            ),
        }
        for place_id, (name, address, postcode) in expected.items():
            with self.subTest(place_id=place_id):
                place = places[place_id]
                self.assertEqual(place["name"], name)
                self.assertEqual(place["address"], address)
                self.assertEqual(place["postcode"], postcode)
                self.assertEqual(place["location_setting"], "Shopping Centre")

        memberships = {row["store_id"]: row for row in self.memberships}
        self.assertEqual(
            memberships["opsm-1320"]["place_id"],
            "place-au-nsw-lake-haven-shopping-centre",
        )
        self.assertEqual(
            memberships["opsm-1384"]["place_id"],
            "place-au-nsw-riverside-plaza-queanbeyan",
        )
        self.assertEqual(memberships["opsm-1320"]["location_setting"], "Shopping Centre")
        self.assertEqual(memberships["opsm-1384"]["location_setting"], "Shopping Centre")

        for place_id, store_ids in {
            "place-au-nsw-lake-haven-shopping-centre": {"opsm-1320", "specsavers-3511"},
            "place-au-nsw-riverside-plaza-queanbeyan": {"opsm-1384", "specsavers-3574"},
        }.items():
            with self.subTest(place_id=place_id):
                self.assertEqual(
                    {row["store_id"] for row in self.memberships if row["place_id"] == place_id},
                    store_ids,
                )

    def test_hyperdome_and_sunshine_plaza_duplicates_are_consolidated(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        self.assertNotIn("place-au-qld-hyperdome-loganholme", places)
        self.assertNotIn("place-au-qld-maroochydore-sunshine-plaza", places)

        hyperdome = places["place-au-qld-logan-hyperdome"]
        self.assertEqual(hyperdome["name"], "Hyperdome")
        self.assertEqual(hyperdome["address"], "Corner Pacific Highway and Bryants Road")
        self.assertEqual(hyperdome["postcode"], "4129")

        sunshine = places["place-au-qld-sunshine-plaza"]
        self.assertEqual(sunshine["name"], "Sunshine Plaza")
        self.assertEqual(sunshine["address"], "154-164 Horton Parade")
        self.assertEqual(sunshine["postcode"], "4558")

        expected_members = {
            "place-au-qld-logan-hyperdome": {"opsm-1562", "oscar-wylee-27", "specsavers-3302"},
            "place-au-qld-sunshine-plaza": {"opsm-1263", "oscar-wylee-51", "specsavers-3201"},
        }
        for place_id, store_ids in expected_members.items():
            with self.subTest(place_id=place_id):
                rows = [row for row in self.memberships if row["place_id"] == place_id]
                self.assertEqual({row["store_id"] for row in rows}, store_ids)
                self.assertTrue(all(row["location_setting"] == "Shopping Centre" for row in rows))
                self.assertTrue(all(row["mapping_confidence"] == "High" for row in rows))

        remaps = {row["previous_place_id"]: row["canonical_place_id"] for row in read_csv("place_id_remaps.csv")}
        self.assertEqual(
            remaps["place-au-qld-hyperdome-loganholme"],
            "place-au-qld-logan-hyperdome",
        )
        self.assertEqual(
            remaps["place-au-qld-maroochydore-sunshine-plaza"],
            "place-au-qld-sunshine-plaza",
        )

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

    def test_current_charter_hall_sydney_and_hunter_batch_has_canonical_names_and_addresses(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        expected = {
            "place-au-nsw-bonnyrigg-plaza": ("Bonnyrigg Plaza", "100 Bonnyrigg Avenue", "Bonnyrigg", "2177"),
            "place-au-nsw-bondi-junction-eastgate": (
                "Eastgate Bondi Junction",
                "71/91 Spring Street",
                "Bondi Junction",
                "2022",
            ),
            "place-au-nsw-bass-hill-plaza": ("Bass Hill Plaza", "753 Hume Highway", "Bass Hill", "2197"),
            "place-au-nsw-morisset-square": ("Morisset Square", "35 Yambo Street", "Morisset", "2264"),
        }
        for place_id, (name, address, locality, postcode) in expected.items():
            with self.subTest(place_id=place_id):
                place = places[place_id]
                self.assertEqual(place["name"], name)
                self.assertEqual(place["address"], address)
                self.assertEqual(place["locality"], locality)
                self.assertEqual(place["postcode"], postcode)
                self.assertEqual(place["location_setting"], "Shopping Centre")
                self.assertEqual(place["place_type"], "Shopping Centre")

        self.assertIn(
            "Bondi Junction Eastgate",
            places["place-au-nsw-bondi-junction-eastgate"]["aliases"],
        )

    def test_current_pacific_casula_richmond_and_grove_names_preserve_stable_ids(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        expected = {
            "place-au-nsw-pacific-square-shopping-centre": (
                "Pacific Square",
                "737 Anzac Parade",
                "Maroubra",
                "2035",
            ),
            "place-au-nsw-casula-mall": ("Casula Mall", "1 Ingham Drive", "Casula", "2170"),
            "place-au-nsw-richmond-marketplace": (
                "Richmond Marketplace",
                "78 March Street",
                "Richmond",
                "2753",
            ),
            "place-au-nsw-grove-square": (
                "Grove Square - The Hills",
                "375-383 Windsor Road",
                "Baulkham Hills",
                "2153",
            ),
        }
        for place_id, (name, address, locality, postcode) in expected.items():
            with self.subTest(place_id=place_id):
                place = places[place_id]
                self.assertEqual(place["name"], name)
                self.assertEqual(place["address"], address)
                self.assertEqual(place["locality"], locality)
                self.assertEqual(place["postcode"], postcode)
                self.assertEqual(place["location_setting"], "Shopping Centre")

        self.assertIn(
            "Stockland Baulkham Hills Shopping Centre",
            places["place-au-nsw-grove-square"]["aliases"],
        )

    def test_current_homeco_north_rocks_and_lidcombe_names_replace_stale_labels(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        expected = {
            "place-au-nsw-glenmore-park-town-centre": (
                "HomeCo Glenmore Park Town Centre",
                "1 Town Terrace",
                "Glenmore Park",
                "2745",
            ),
            "place-au-nsw-menai-marketplace-shopping-centre": (
                "HomeCo Menai Marketplace",
                "152-194 Allison Crescent",
                "Menai",
                "2234",
            ),
            "place-au-nsw-north-rocks-shopping-centre": (
                "North Rocks Shopping Centre",
                "328-336 North Rocks Road",
                "North Rocks",
                "2151",
            ),
            "place-au-nsw-lidcombe-shopping-centre": (
                "Lidcombe Shopping Centre",
                "92 Parramatta Road",
                "Lidcombe",
                "2141",
            ),
        }
        for place_id, (name, address, locality, postcode) in expected.items():
            with self.subTest(place_id=place_id):
                place = places[place_id]
                self.assertEqual(place["name"], name)
                self.assertEqual(place["address"], address)
                self.assertEqual(place["locality"], locality)
                self.assertEqual(place["postcode"], postcode)
                self.assertEqual(place["location_setting"], "Shopping Centre")

        self.assertIn(
            "Westfield North Rocks",
            places["place-au-nsw-north-rocks-shopping-centre"]["aliases"],
        )
        self.assertIn(
            "Lidcombe Power Centre",
            places["place-au-nsw-lidcombe-shopping-centre"]["aliases"],
        )

    def test_current_tweed_warrawong_and_orana_names_preserve_stable_ids(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        expected = {
            "place-au-nsw-tweed-mall": (
                "Tweed Mall",
                "Corner Wharf and Bay Streets",
                "Tweed Heads",
                "2485",
            ),
            "place-au-nsw-warrawong-plaza-shopping-centre": (
                "Warrawong Plaza",
                "Corner King Street and Northcote Drive",
                "Warrawong",
                "2502",
            ),
            "place-au-nsw-orana-mall-marketplace": (
                "Orana Mall",
                "Corner Wheelers Lane and Mitchell Highway",
                "Dubbo",
                "2830",
            ),
        }
        for place_id, (name, address, locality, postcode) in expected.items():
            with self.subTest(place_id=place_id):
                place = places[place_id]
                self.assertEqual(place["name"], name)
                self.assertEqual(place["address"], address)
                self.assertEqual(place["locality"], locality)
                self.assertEqual(place["postcode"], postcode)
                self.assertEqual(place["location_setting"], "Shopping Centre")

        self.assertIn(
            "Warrawong Plaza Shopping Centre",
            places["place-au-nsw-warrawong-plaza-shopping-centre"]["aliases"],
        )
        self.assertIn(
            "Orana Mall Marketplace",
            places["place-au-nsw-orana-mall-marketplace"]["aliases"],
        )

    def test_current_bathurst_carlingford_cessnock_and_stanhope_names_are_canonical(self) -> None:
        places = {place["place_id"]: place for place in self.places}
        expected = {
            "place-au-nsw-bathurst-city-centre": (
                "Bathurst City Centre",
                "210 Howick Street",
                "Bathurst",
                "2795",
            ),
            "place-au-nsw-carlingford-court": (
                "Carlingford Court",
                "Corner Pennant Hills Road and Carlingford Road",
                "Carlingford",
                "2118",
            ),
            "place-au-nsw-cessnock-plaza-shopping-centre": (
                "Cessnock Village",
                "1 Keene Street",
                "Cessnock",
                "2325",
            ),
            "place-au-nsw-stanhope-village-shopping-centre": (
                "Stanhope Village",
                "2 Sentry Drive",
                "Stanhope Gardens",
                "2768",
            ),
        }
        for place_id, (name, address, locality, postcode) in expected.items():
            with self.subTest(place_id=place_id):
                place = places[place_id]
                self.assertEqual(place["name"], name)
                self.assertEqual(place["address"], address)
                self.assertEqual(place["locality"], locality)
                self.assertEqual(place["postcode"], postcode)
                self.assertEqual(place["location_setting"], "Shopping Centre")

        self.assertIn(
            "Cessnock Plaza Shopping Centre",
            places["place-au-nsw-cessnock-plaza-shopping-centre"]["aliases"],
        )
        self.assertIn(
            "Stanhope Village Shopping Centre",
            places["place-au-nsw-stanhope-village-shopping-centre"]["aliases"],
        )

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
