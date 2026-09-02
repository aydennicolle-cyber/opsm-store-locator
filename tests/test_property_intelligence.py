#!/usr/bin/env python3
"""Acceptance tests for public property and leasing intelligence."""

from __future__ import annotations

import csv
import json
import unittest
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class PropertyIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads((DATA / "property_intelligence.json").read_text(encoding="utf-8"))
        cls.places = json.loads((DATA / "retail_places.json").read_text(encoding="utf-8"))["places"]
        cls.groups = cls.payload["groups"]
        cls.relationships = cls.payload["relationships"]

    def test_seed_groups_exist_without_implied_relationships(self) -> None:
        names = {group["canonical_name"] for group in self.groups}
        expected = {
            "Scentre Group", "Vicinity Centres", "GPT Group", "Dexus", "QIC Real Estate", "Stockland",
            "Mirvac", "ISPT", "Region Group", "Charter Hall", "MA Financial", "IP Generation", "RetPro",
            "Haben", "Kiwi Property", "Stride Property", "Investore Property", "Oyster Property Group",
            "Precinct Properties", "CBRE", "Colliers", "JLL", "Cushman & Wakefield", "Knight Frank",
            "Savills", "Bayleys",
        }
        self.assertTrue(expected.issubset(names))
        self.assertEqual(len({group["group_id"] for group in self.groups}), len(self.groups))
        self.assertTrue(all("aliases" in group for group in self.groups))

    def test_relationships_are_referentially_sound_and_evidenced(self) -> None:
        place_ids = {place["place_id"] for place in self.places}
        group_ids = {group["group_id"] for group in self.groups}
        relationship_ids = [row["relationship_id"] for row in self.relationships]
        self.assertEqual(len(relationship_ids), len(set(relationship_ids)))
        for relationship in self.relationships:
            self.assertIn(relationship["place_id"], place_ids)
            self.assertIn(relationship["group_id"], group_ids)
            self.assertTrue(relationship["source_url"].startswith("http"))
            self.assertRegex(relationship["last_verified_at"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertIn(relationship["confidence"], {"High", "Medium", "Low"})
            self.assertIn(relationship["derived_from"], {"curated_relationship", "official_domain_rule", "official_portfolio_asset"})

    def test_active_known_ownership_never_exceeds_100_percent(self) -> None:
        totals = defaultdict(float)
        for row in self.relationships:
            if row["status"] == "ACTIVE" and row["role"] in {"OWNER", "CO_OWNER"}:
                totals[row["place_id"]] += float(row.get("ownership_percentage") or 0)
        self.assertTrue(all(total <= 100 for total in totals.values()))

    def test_domain_derivation_is_explicit_and_not_proximity_based(self) -> None:
        generated = [row for row in self.relationships if row["derived_from"] == "official_domain_rule"]
        self.assertTrue(all("domain" in row["derived_from"] for row in generated))
        self.assertNotIn("proximity", json.dumps(self.relationships).lower())

    def test_official_portfolios_are_bounded_and_unmatched_assets_are_reviewed(self) -> None:
        assets = self.payload["portfolio_assets"]
        scentre = [row for row in assets if row["group_id"] == "group-scentre"]
        self.assertEqual(len(scentre), 42)
        self.assertTrue(all(row["match_status"] == "Matched" for row in scentre))
        self.assertEqual(self.payload["group_portfolios"]["group-scentre"]["property_count"], 42)
        north_rocks = "place-au-nsw-north-rocks-shopping-centre"
        self.assertFalse(any(row["group_id"] == "group-scentre" and row["place_id"] == north_rocks for row in self.relationships))
        unmatched = [row for row in assets if row["match_status"] != "Matched"]
        review_ids = {row["review_id"] for row in self.payload["review_items"]}
        self.assertTrue(unmatched)
        self.assertTrue(all(f"review-portfolio-{row['portfolio_asset_id']}" in review_ids for row in unmatched))

        haben = [row for row in assets if row["group_id"] == "group-haben"]
        self.assertEqual(len(haben), 13)
        self.assertTrue(all(row["match_status"] == "Matched" for row in haben))
        self.assertEqual(self.payload["group_portfolios"]["group-haben"]["property_count"], 13)

        stockland = [row for row in assets if row["group_id"] == "group-stockland"]
        self.assertEqual(len(stockland), 20)
        self.assertEqual(sum(row["match_status"] == "Matched" for row in stockland), 15)
        self.assertEqual(sum(row["match_status"] != "Matched" for row in stockland), 5)
        self.assertEqual(self.payload["group_portfolios"]["group-stockland"]["property_count"], 15)

    def test_centre_class_inference_uses_two_official_measures(self) -> None:
        inferred = [
            summary["centre_class_evidence"]
            for summary in self.payload["property_summaries"].values()
            if summary["centre_class_method"] == "Inferred"
            and summary["centre_class_evidence"]["public_note"].startswith("Scale inferred from official portfolio GLA")
        ]
        self.assertGreaterEqual(len(inferred), 40)
        self.assertTrue(all("GLA" in item["public_note"] and "tenant count" in item["public_note"] for item in inferred))

    def test_official_portfolio_metrics_reach_property_summaries(self) -> None:
        highpoint = self.payload["property_summaries"]["place-au-vic-highpoint-shopping-centre"]
        self.assertEqual(highpoint["gla_sqm"], 149600)
        self.assertEqual(highpoint["tenancy_count"], 420)
        belconnen = self.payload["property_summaries"]["place-au-act-westfield-belconnen"]
        self.assertEqual(belconnen["annual_visits"], 10_800_000)
        self.assertTrue(belconnen["source_url"].startswith("https://"))
        bankstown = self.payload["property_summaries"]["place-au-nsw-bankstown-central"]
        self.assertEqual(bankstown["centre_class"], "Regional")
        self.assertEqual(bankstown["gla_sqm"], 78575)
        self.assertEqual(set(bankstown["owner_names"]), {"JY Group", "Vicinity Centres"})
        self.assertEqual(bankstown["leasing_arrangement"], "In-house")
        oxley = self.payload["property_summaries"]["place-au-qld-the-station-oxley"]
        self.assertEqual(oxley["centre_class"], "Neighbourhood")
        self.assertIn("Haben", oxley["manager_names"])

        ocean_keys = self.payload["property_summaries"]["place-au-wa-clarkson-ocean-keys-shopping-centre"]
        self.assertEqual(ocean_keys["centre_class"], "Sub-regional")
        self.assertEqual(ocean_keys["owner_names"], ["Dexus Wholesale Shopping Centre Fund"])
        self.assertIn("Dexus", ocean_keys["manager_names"])
        self.assertEqual(ocean_keys["leasing_arrangement"], "In-house")

        royal_randwick = self.payload["property_summaries"]["place-au-nsw-royal-randwick-shopping-centre"]
        self.assertEqual(royal_randwick["centre_class"], "Neighbourhood")
        self.assertEqual(royal_randwick["owner_names"], ["Dexus Wholesale Shopping Centre Fund"])
        self.assertIn("Dexus", royal_randwick["manager_names"])

        westfield_liverpool = self.payload["property_summaries"]["place-au-nsw-westfield-liverpool"]
        self.assertEqual(westfield_liverpool["centre_class"], "Regional")
        self.assertEqual(
            set(westfield_liverpool["owner_names"]),
            {"Scentre Group", "Dexus Wholesale Shopping Centre Fund"},
        )

        indooroopilly = self.payload["property_summaries"]["place-au-qld-indooroopilly"]
        self.assertEqual(
            set(indooroopilly["owner_names"]),
            {"Dexus Wholesale Shopping Centre Fund", "Dexus Wholesale Property Fund"},
        )
        indooroopilly_owner_total = sum(
            float(row.get("ownership_percentage") or 0)
            for row in self.relationships
            if row["place_id"] == "place-au-qld-indooroopilly"
            and row["status"] == "ACTIVE"
            and row["role"] in {"OWNER", "CO_OWNER"}
        )
        self.assertEqual(indooroopilly_owner_total, 50)

        point_cook = self.payload["property_summaries"]["place-au-vic-point-cook-town-centre"]
        self.assertEqual(point_cook["centre_class"], "Sub-regional")
        self.assertEqual(point_cook["owner_names"], ["Stockland"])
        self.assertEqual(point_cook["leasing_arrangement"], "In-house")

        wendouree = self.payload["property_summaries"]["place-au-vic-wendouree-stockland"]
        self.assertEqual(wendouree["centre_class"], "Sub-regional")
        self.assertEqual(wendouree["owner_names"], ["Stockland"])

        baldivis = self.payload["property_summaries"]["place-au-wa-stockland-baldivis"]
        self.assertEqual(baldivis["centre_class"], "Sub-regional")
        self.assertEqual(baldivis["owner_names"], ["Stockland"])

        harrisdale = self.payload["property_summaries"]["place-au-wa-harrisdale-stockland-shopping-centre"]
        self.assertEqual(harrisdale["centre_class"], "Neighbourhood")
        self.assertEqual(harrisdale["owner_names"], ["Stockland"])

    def test_current_gpt_portfolio_relationships_and_classes(self) -> None:
        expected = {
            "place-au-nsw-charlestown-square": ("Super Regional", {"GPT Group"}, {"GPT Group"}),
            "place-au-nsw-dapto-mall": ("Sub-regional", {"UniSuper"}, {"GPT Group"}),
            "place-au-nsw-macarthur-square": (
                "Regional",
                {"GPT Wholesale Shopping Centre Fund", "Australian Prime Property Fund Retail"},
                {"GPT Group"},
            ),
            "place-au-nsw-rouse-hill-town-centre": (
                "Regional",
                {"GPT Group", "GPT Wholesale Shopping Centre Fund"},
                {"GPT Group"},
            ),
            "place-au-nsw-marrickville-metro": ("Sub-regional", {"UniSuper"}, {"GPT Group"}),
            "place-au-vic-chirnside-park-shopping-centre": (
                "Sub-regional", {"GPT Wholesale Shopping Centre Fund"}, {"GPT Group"}
            ),
            "place-au-vic-keysborough-parkmore-shopping-centre": (
                "Sub-regional", {"GPT Wholesale Shopping Centre Fund"}, {"GPT Group"}
            ),
            "place-au-wa-belmont-forum": ("Sub-regional", {"GPT Group", "Perron Group"}, {"GPT Group"}),
            "place-au-wa-cockburn-gateway-shopping-centre": (
                "Regional", {"GPT Group", "Perron Group"}, {"GPT Group"}
            ),
            "place-au-wa-karrinyup-shopping-centre": ("Super Regional", {"UniSuper"}, {"GPT Group"}),
        }
        for place_id, (centre_class, owners, managers) in expected.items():
            with self.subTest(place_id=place_id):
                summary = self.payload["property_summaries"][place_id]
                self.assertEqual(summary["centre_class"], centre_class)
                self.assertEqual(set(summary["owner_names"]), owners)
                self.assertEqual(set(summary["manager_names"]), managers)
                self.assertEqual(summary["leasing_arrangement"], "In-house")

    def test_current_region_portfolio_matches_have_explicit_classes_and_leasing(self) -> None:
        region_assets = [
            row for row in self.payload["portfolio_assets"]
            if row["group_id"] == "group-region"
        ]
        self.assertEqual(len(region_assets), 24)
        self.assertTrue(all(row["match_status"] == "Matched" for row in region_assets))
        self.assertEqual(self.payload["group_portfolios"]["group-region"]["property_count"], 24)

        expected_classes = {
            "place-au-act-cooleman-court": "Neighbourhood",
            "place-au-nsw-lavington-square": "Sub-regional",
            "place-au-nsw-marketown-shopping-centre": "Sub-regional",
            "place-au-nsw-raymond-terrace-marketplace": "Sub-regional",
            "place-au-unknown-jimboomba-shopping-centre": "Neighbourhood",
            "place-au-vic-lilydale-marketplace": "Sub-regional",
            "place-au-wa-kwinana-marketplace": "Sub-regional",
            "place-au-wa-warnbro-centre": "Sub-regional",
        }
        for place_id, centre_class in expected_classes.items():
            with self.subTest(place_id=place_id):
                summary = self.payload["property_summaries"][place_id]
                self.assertEqual(summary["centre_class"], centre_class)
                self.assertEqual(summary["owner_names"], ["Region Group"])
                self.assertIn("Region Group", summary["manager_names"])
                self.assertEqual(summary["leasing_arrangement"], "In-house")

    def test_current_retail_first_portfolio_is_filterable_and_classed(self) -> None:
        retail_first_assets = [
            row for row in self.payload["portfolio_assets"]
            if row["group_id"] == "group-retail-first"
        ]
        self.assertEqual(len(retail_first_assets), 16)
        self.assertTrue(all(row["match_status"] == "Matched" for row in retail_first_assets))
        self.assertEqual(self.payload["group_portfolios"]["group-retail-first"]["property_count"], 16)
        self.assertEqual(self.payload["group_portfolios"]["group-yfg-shopping-centres"]["property_count"], 6)

        expected_classes = {
            "place-au-qld-australia-fair-shopping-centre": "Regional",
            "place-au-qld-brookside-shopping-centre": "Sub-regional",
            "place-au-qld-cannon-hill-kmart-plaza": "Neighbourhood",
            "place-au-qld-capalaba-park-shopping-centre": "Sub-regional",
            "place-au-qld-mt-ommaney-centre": "Regional",
            "place-au-qld-strathpine-centre": "Sub-regional",
            "place-au-qld-toowong-village": "CBD / Mixed-use",
        }
        for place_id, centre_class in expected_classes.items():
            with self.subTest(place_id=place_id):
                summary = self.payload["property_summaries"][place_id]
                self.assertEqual(summary["centre_class"], centre_class)
                self.assertIn("Retail First", summary["manager_names"])
                self.assertEqual(summary["leasing_arrangement"], "In-house")

        yfg_owned = {
            "place-au-qld-australia-fair-shopping-centre",
            "place-au-qld-brookside-shopping-centre",
            "place-au-qld-25-fairfield-gardens-shopping-centre",
            "place-au-qld-mt-ommaney-centre",
            "place-au-qld-strathpine-centre",
            "place-au-qld-toowong-village",
        }
        for place_id in yfg_owned:
            self.assertIn("YFG Shopping Centres", self.payload["property_summaries"][place_id]["owner_names"])

    def test_priority_nsw_centres_keep_distinct_property_roles(self) -> None:
        rhodes_id = "place-au-nsw-rhodes-waterside-shopping-centre"
        narellan_id = "place-au-nsw-narellan-town-centre"
        tweed_id = "place-au-nsw-tweed-city-shopping-centre"

        rhodes = self.payload["property_summaries"][rhodes_id]
        self.assertEqual(rhodes["centre_class"], "Regional")
        self.assertEqual(set(rhodes["owner_names"]), {"Mirvac", "Perron Group"})
        self.assertEqual(rhodes["manager_names"], ["Mirvac"])
        self.assertEqual(rhodes["leasing_arrangement"], "In-house")
        self.assertEqual(rhodes["gla_sqm"], 35239)

        narellan = self.payload["property_summaries"][narellan_id]
        self.assertEqual(narellan["centre_class"], "Regional")
        self.assertEqual(set(narellan["owner_names"]), {"Vitocco Enterprises", "Greenfields"})
        self.assertEqual(narellan["manager_names"], ["Dart West Retail"])
        self.assertEqual(narellan["tenancy_count"], 220)

        tweed = self.payload["property_summaries"][tweed_id]
        self.assertEqual(tweed["centre_class"], "Sub-regional")
        self.assertEqual(tweed["manager_names"], ["Lendlease"])
        self.assertEqual(tweed["leasing_arrangement"], "External agency")
        tweed_roles = {
            (row["group_id"], row["role"])
            for row in self.relationships
            if row["place_id"] == tweed_id
        }
        self.assertIn(("group-lendlease", "OPERATOR"), tweed_roles)
        self.assertIn(("group-one-retail", "EXTERNAL_LEASING_AGENT"), tweed_roles)

    def test_current_fawkner_portfolio_batch_is_filterable_and_classed(self) -> None:
        assets = [
            row for row in self.payload["portfolio_assets"]
            if row["group_id"] == "group-fawkner"
        ]
        self.assertEqual(len(assets), 12)
        self.assertTrue(all(row["match_status"] == "Matched" for row in assets))
        self.assertEqual(self.payload["group_portfolios"]["group-fawkner"]["property_count"], 12)

        expected = {
            "place-au-qld-cairns-shopping-centre": ("Regional", 51972, 172),
            "place-au-wa-midland-gate-shopping-centre": ("Regional", 68964, 203),
            "place-au-qld-townsville-willows-shopping-centre": ("Sub-regional", 44507, 149),
            "place-au-wa-mirrabooka-square-shopping-centre": ("Sub-regional", 42555, 139),
            "place-au-nsw-figtree-grove-shopping-centre": ("Sub-regional", 21984, 90),
            "place-au-nsw-settlement-city-shopping-centre": ("Sub-regional", 19554, 70),
        }
        for place_id, (centre_class, gla_sqm, tenancy_count) in expected.items():
            with self.subTest(place_id=place_id):
                summary = self.payload["property_summaries"][place_id]
                self.assertEqual(summary["centre_class"], centre_class)
                self.assertIn("Fawkner Property", summary["manager_names"])
                self.assertEqual(summary["leasing_arrangement"], "In-house")
                self.assertEqual(summary["gla_sqm"], gla_sqm)
                self.assertEqual(summary["tenancy_count"], tenancy_count)

        orange = self.payload["property_summaries"]["place-au-nsw-orange-central-square"]
        self.assertEqual(orange["centre_class"], "CBD / Mixed-use")
        self.assertEqual(orange["owner_names"], ["Charter Hall Retail REIT"])
        self.assertEqual(orange["manager_names"], ["Charter Hall"])
        self.assertEqual(orange["leasing_arrangement"], "In-house")

    def test_current_mirvac_portfolio_batch_preserves_current_co_owners(self) -> None:
        assets = [
            row for row in self.payload["portfolio_assets"]
            if row["group_id"] == "group-mirvac"
        ]
        self.assertEqual(len(assets), 6)
        self.assertTrue(all(row["match_status"] == "Matched" for row in assets))
        self.assertEqual(self.payload["group_portfolios"]["group-mirvac"]["property_count"], 6)

        expected = {
            "place-au-nsw-broadway-shopping-centre": (
                "Regional", {"Mirvac", "Perron Group"}, 53011, 149
            ),
            "place-au-qld-kawana-shoppingworld": (
                "Sub-regional", {"Mirvac", "IFM Investors"}, 45656, 141
            ),
            "place-au-qld-orion-springfield-central": (
                "Regional", {"Mirvac"}, 73597, 186
            ),
            "place-au-nsw-greenwood-plaza": (
                "CBD / Mixed-use", {"Mirvac", "CapitaLand Integrated Commercial Trust"}, 9019, 90
            ),
            "place-au-vic-moonee-ponds-central": (
                "Sub-regional", {"Mirvac"}, 19251, 62
            ),
        }
        for place_id, (centre_class, owners, gla_sqm, tenancy_count) in expected.items():
            with self.subTest(place_id=place_id):
                summary = self.payload["property_summaries"][place_id]
                self.assertEqual(summary["centre_class"], centre_class)
                self.assertEqual(set(summary["owner_names"]), owners)
                self.assertEqual(summary["manager_names"], ["Mirvac"])
                self.assertEqual(summary["leasing_arrangement"], "In-house")
                self.assertEqual(summary["gla_sqm"], gla_sqm)
                self.assertEqual(summary["tenancy_count"], tenancy_count)

    def test_priority_independent_and_ma_financial_centres_preserve_role_evidence(self) -> None:
        top_ryde = self.payload["property_summaries"]["place-au-nsw-top-ryde-city-shopping-centre"]
        self.assertEqual(top_ryde["centre_class"], "Regional")
        self.assertEqual(
            set(top_ryde["owner_names"]),
            {"Keppel REIT", "MA-managed Top Ryde fund"},
        )
        self.assertEqual(top_ryde["manager_names"], ["MA Financial"])
        self.assertEqual(top_ryde["leasing_arrangement"], "In-house")

        noosa = self.payload["property_summaries"]["place-au-qld-noosa-civic-shopping-centre"]
        self.assertEqual(noosa["centre_class"], "Sub-regional")
        self.assertEqual(noosa["owner_names"], ["Stockwell"])
        self.assertEqual(noosa["manager_names"], ["Stockwell"])
        self.assertEqual(noosa["leasing_arrangement"], "In-house")

        st_ives = self.payload["property_summaries"]["place-au-nsw-st-ives-shopping-centre"]
        self.assertEqual(st_ives["centre_class"], "Neighbourhood")
        self.assertEqual(st_ives["owner_names"], ["St Ives Shopping Village ownership"])
        self.assertEqual(st_ives["manager_names"], [])
        self.assertEqual(st_ives["leasing_arrangement"], "Private landlord")

    def test_ifm_and_greensborough_priority_centres_keep_unknown_owners_explicit(self) -> None:
        for place_id, centre_class, gla_sqm, tenancy_count in (
            ("place-au-nsw-wagga-wagga-marketplace", "Sub-regional", 24828, 59),
            ("place-au-vic-bendigo-marketplace", "Sub-regional", 18552, 100),
        ):
            with self.subTest(place_id=place_id):
                summary = self.payload["property_summaries"][place_id]
                self.assertEqual(summary["centre_class"], centre_class)
                self.assertEqual(summary["owner_names"], [])
                self.assertEqual(summary["manager_names"], ["IFM Investors"])
                self.assertEqual(summary["leasing_arrangement"], "In-house")
                self.assertEqual(summary["gla_sqm"], gla_sqm)
                self.assertEqual(summary["tenancy_count"], tenancy_count)

        greensborough = self.payload["property_summaries"]["place-au-vic-greensborough-plaza"]
        self.assertEqual(greensborough["centre_class"], "Regional")
        self.assertEqual(greensborough["owner_names"], [])
        self.assertEqual(set(greensborough["manager_names"]), {"151 Property", "JLL"})
        self.assertEqual(greensborough["leasing_arrangement"], "External agency")
        self.assertEqual(greensborough["gla_sqm"], 70000)
        self.assertEqual(greensborough["tenancy_count"], 170)

    def test_priority_act_and_nsw_centres_use_current_owner_and_manager_evidence(self) -> None:
        expected = {
            "place-au-act-marketplace-gungahlin": {
                "centre_class": "Sub-regional",
                "owners": set(),
                "managers": {"Vinta Group"},
                "arrangement": "In-house",
                "tenancy_count": 74,
            },
            "place-au-act-south-point-shopping-centre": {
                "centre_class": "Regional",
                "owners": {"Leda Holdings"},
                "managers": {"Leda Holdings"},
                "arrangement": "In-house",
                "gla_sqm": 76987,
            },
            "place-au-nsw-ashfield-mall": {
                "centre_class": "Sub-regional",
                "owners": {"Mintus Investments 4 Pty Ltd ATF The Retail Investment Trust 8"},
                "managers": {"Mintus Pty Ltd"},
                "arrangement": "In-house",
                "annual_visits": 6400000,
            },
            "place-au-nsw-balgowlah-shopping-centre": {
                "centre_class": "Neighbourhood",
                "owners": {"Revelop"},
                "managers": {"Revelop"},
                "arrangement": "In-house",
                "gla_sqm": 12800,
            },
            "place-au-nsw-lake-macquarie-square": {
                "centre_class": "Sub-regional",
                "owners": {"Revelop"},
                "managers": {"Revelop"},
                "arrangement": "In-house",
                "gla_sqm": 24500,
            },
        }
        for place_id, values in expected.items():
            with self.subTest(place_id=place_id):
                summary = self.payload["property_summaries"][place_id]
                self.assertEqual(summary["centre_class"], values["centre_class"])
                self.assertEqual(set(summary["owner_names"]), values["owners"])
                self.assertEqual(set(summary["manager_names"]), values["managers"])
                self.assertEqual(summary["leasing_arrangement"], values["arrangement"])
                for key in ("tenancy_count", "gla_sqm", "annual_visits"):
                    if key in values:
                        self.assertEqual(summary[key], values[key])

    def test_research_queue_covers_every_unresolved_property_or_class(self) -> None:
        with (DATA / "property_research_queue.csv").open(newline="", encoding="utf-8") as handle:
            queue = list(csv.DictReader(handle))
        centre_ids = {
            place["place_id"]
            for place in json.loads((DATA / "retail_places.json").read_text(encoding="utf-8"))["places"]
            if place["place_type"] == "Shopping Centre"
        }
        unresolved = {
            place_id for place_id in centre_ids
            if self.payload["property_summaries"][place_id]["research_status"] == "Not researched"
            or self.payload["property_summaries"][place_id]["centre_class"] == "Unknown"
        }
        self.assertEqual({row["place_id"] for row in queue}, unresolved)
        self.assertTrue(all(row["priority"] in {"P1", "P2", "P3", "P4"} for row in queue))

    def test_leichhardt_and_charter_hall_batch_preserves_unknown_and_direct_owners(self) -> None:
        leichhardt = self.payload["property_summaries"]["place-au-nsw-leichhardt-marketplace"]
        self.assertEqual(leichhardt["centre_class"], "Sub-regional")
        self.assertEqual(leichhardt["owner_names"], [])
        self.assertEqual(leichhardt["manager_names"], ["JLL"])
        self.assertEqual(leichhardt["leasing_arrangement"], "External agency")

        expected = {
            "place-au-nsw-dubbo-square": ("Charter Hall Retail REIT", 12806, 37),
            "place-au-nsw-bateau-bay-square": ("Retail Partnership No.2", 29839, 71),
        }
        for place_id, (owner, gla_sqm, tenancy_count) in expected.items():
            with self.subTest(place_id=place_id):
                summary = self.payload["property_summaries"][place_id]
                self.assertEqual(summary["centre_class"], "Sub-regional")
                self.assertEqual(summary["owner_names"], [owner])
                self.assertEqual(summary["manager_names"], ["Charter Hall"])
                self.assertEqual(summary["leasing_arrangement"], "In-house")
                self.assertEqual(summary["gla_sqm"], gla_sqm)
                self.assertEqual(summary["tenancy_count"], tenancy_count)

    def test_final_pre_release_centre_batch_preserves_evidenced_roles(self) -> None:
        park_beach = self.payload["property_summaries"]["place-au-nsw-park-beach-plaza"]
        self.assertEqual(park_beach["centre_class"], "Regional")
        self.assertEqual(park_beach["owner_names"], [])
        self.assertEqual(park_beach["manager_names"], ["Bachrach Naumburger Group"])
        self.assertEqual(park_beach["leasing_arrangement"], "In-house")
        self.assertEqual(park_beach["gla_sqm"], 42662.88)
        self.assertEqual(park_beach["tenancy_count"], 120)

        warriewood = self.payload["property_summaries"]["place-au-nsw-warriewood-square"]
        self.assertEqual(warriewood["centre_class"], "Sub-regional")
        self.assertEqual(warriewood["owner_names"], ["Vicinity Centres"])
        self.assertEqual(warriewood["manager_names"], ["Vicinity Centres"])
        self.assertEqual(warriewood["leasing_arrangement"], "In-house")
        self.assertEqual(warriewood["gla_sqm"], 30000)
        self.assertEqual(warriewood["tenancy_count"], 100)

        singleton = self.payload["property_summaries"]["place-au-nsw-singleton-square"]
        self.assertEqual(singleton["centre_class"], "Sub-regional")
        self.assertEqual(singleton["owner_names"], ["Charter Hall Retail REIT"])
        self.assertEqual(singleton["manager_names"], ["Charter Hall"])
        self.assertEqual(singleton["leasing_arrangement"], "In-house")
        self.assertEqual(singleton["gla_sqm"], 20646)
        self.assertEqual(singleton["tenancy_count"], 48)

    def test_woodgrove_and_new_zealand_batch_preserves_complex_relationships(self) -> None:
        woodgrove = self.payload["property_summaries"]["place-au-vic-woodgrove-shopping-centre"]
        self.assertEqual(woodgrove["centre_class"], "Regional")
        self.assertEqual(set(woodgrove["owner_names"]), {
            "Woodgrove Property Trust",
            "ADPF1 Woodgrove Property Trust",
            "ADPF2 Woodgrove Property Trust",
            "Asia Core Woodgrove Trust",
        })
        self.assertEqual(woodgrove["manager_names"], ["Assembly Funds Management"])
        self.assertEqual(woodgrove["leasing_arrangement"], "External agency")
        self.assertEqual(woodgrove["gla_sqm"], 55000)
        self.assertEqual(woodgrove["tenancy_count"], 128)

        lynnmall = self.payload["property_summaries"]["place-nz-auckland-lynnmall-shopping-centre"]
        self.assertEqual(lynnmall["centre_class"], "Regional")
        self.assertEqual(lynnmall["owner_names"], ["Kiwi Property"])
        self.assertEqual(lynnmall["manager_names"], ["Kiwi Property"])
        self.assertEqual(lynnmall["leasing_arrangement"], "In-house")
        self.assertEqual(lynnmall["gla_sqm"], 36776)
        self.assertEqual(lynnmall["tenancy_count"], 127)

        northlands = self.payload["property_summaries"]["place-nz-canterbury-northlands-mall"]
        self.assertEqual(northlands["centre_class"], "Regional")
        self.assertEqual(northlands["owner_names"], ["Mackersy Northlands Limited Partnership"])
        self.assertEqual(northlands["manager_names"], ["Kiwi Property"])
        self.assertEqual(northlands["leasing_arrangement"], "In-house")
        self.assertEqual(northlands["tenancy_count"], 120)

    def test_current_morayfield_shepparton_and_roselands_roles_are_not_flattened(self) -> None:
        morayfield = self.payload["property_summaries"]["place-au-qld-morayfield-shopping-centre"]
        self.assertEqual(morayfield["centre_class"], "Regional")
        self.assertEqual(morayfield["owner_names"], ["Leda Holdings"])
        self.assertEqual(morayfield["manager_names"], ["Leda Holdings"])
        self.assertEqual(morayfield["leasing_arrangement"], "In-house")
        self.assertEqual(morayfield["gla_sqm"], 57000)
        self.assertEqual(morayfield["tenancy_count"], 155)

        shepparton = self.payload["property_summaries"]["place-au-vic-shepparton-marketplace"]
        self.assertEqual(shepparton["centre_class"], "Sub-regional")
        self.assertEqual(shepparton["owner_names"], [])
        self.assertEqual(shepparton["manager_names"], [])
        self.assertEqual(shepparton["leasing_arrangement"], "External agency")
        self.assertEqual(shepparton["tenancy_count"], 43)

        roselands = self.payload["property_summaries"]["place-au-nsw-roselands-shopping-centre"]
        self.assertEqual(roselands["centre_class"], "Regional")
        self.assertEqual(set(roselands["owner_names"]), {
            "HMC LML No. 4 Property Trust",
            "JY No.6 Trust",
        })
        self.assertEqual(roselands["manager_names"], ["HMC Capital"])
        self.assertEqual(roselands["leasing_arrangement"], "External agency")

    def test_current_pines_waverley_and_corio_structures_keep_leasing_roles_separate(self) -> None:
        pines = self.payload["property_summaries"]["place-au-qld-the-pines-shopping-centre"]
        self.assertEqual(pines["centre_class"], "Sub-regional")
        self.assertEqual(pines["owner_names"], ["The Pines Shopping Centre (Qld.) Pty Ltd"])
        self.assertEqual(pines["manager_names"], ["The Pines Shopping Centre (Qld.) Pty Ltd"])
        self.assertEqual(pines["leasing_arrangement"], "Private landlord")

        waverley = self.payload["property_summaries"]["place-au-vic-waverley-gardens-shopping-centre"]
        self.assertEqual(waverley["centre_class"], "Sub-regional")
        self.assertEqual(waverley["owner_names"], ["Charter Hall Convenience Retail Fund"])
        self.assertEqual(waverley["manager_names"], ["Charter Hall"])
        self.assertEqual(waverley["leasing_arrangement"], "External agency")

        corio = self.payload["property_summaries"]["place-au-vic-corio-village"]
        self.assertEqual(corio["centre_class"], "Sub-regional")
        self.assertEqual(corio["owner_names"], ["Retail Partnership No.1"])
        self.assertEqual(corio["manager_names"], ["Charter Hall"])
        self.assertEqual(corio["leasing_arrangement"], "External agency")
        self.assertEqual(corio["gla_sqm"], 33600)
        self.assertEqual(corio["tenancy_count"], 77)

    def test_current_caneland_smithfield_grove_and_coastlands_roles_are_explicit(self) -> None:
        caneland = self.payload["property_summaries"]["place-au-qld-caneland-centre"]
        self.assertEqual(caneland["centre_class"], "Regional")
        self.assertEqual(caneland["owner_names"], ["Sentinel Caneland Mackay Investment Trust"])
        self.assertEqual(caneland["manager_names"], ["Sentinel Property Group"])
        self.assertEqual(caneland["leasing_arrangement"], "In-house")
        self.assertEqual(caneland["gla_sqm"], 65864)
        self.assertEqual(caneland["tenancy_count"], 168)

        smithfield = self.payload["property_summaries"]["place-au-qld-cairns-smithfield-centre"]
        self.assertEqual(smithfield["centre_class"], "Sub-regional")
        self.assertEqual(smithfield["owner_names"], ["Smithfield Centre Trust"])
        self.assertEqual(smithfield["manager_names"], [])
        self.assertEqual(smithfield["leasing_arrangement"], "External agency")

        grove = self.payload["property_summaries"]["place-au-sa-the-grove-shopping-centre"]
        self.assertEqual(grove["centre_class"], "Sub-regional")
        self.assertEqual(grove["owner_names"], ["Challenger Golden Grove Trust"])
        self.assertEqual(grove["manager_names"], ["JLL"])
        self.assertEqual(grove["leasing_arrangement"], "External agency")
        self.assertEqual(grove["tenancy_count"], 113)

        coastlands = self.payload["property_summaries"]["place-nz-wellington-coastlands-shoppingtown"]
        self.assertEqual(coastlands["centre_class"], "Regional")
        self.assertEqual(coastlands["owner_names"], ["Coastlands Shoppingtown Ltd"])
        self.assertEqual(coastlands["manager_names"], ["Coastlands Shoppingtown Ltd"])
        self.assertEqual(coastlands["leasing_arrangement"], "Private landlord")

    def test_victoria_point_and_southgate_current_portfolios_are_explicit(self) -> None:
        victoria_point = self.payload["property_summaries"]["place-au-qld-victoria-point-shopping-centre"]
        self.assertEqual(victoria_point["centre_class"], "Sub-regional")
        self.assertEqual(victoria_point["owner_names"], ["Leda Holdings"])
        self.assertEqual(victoria_point["manager_names"], ["Leda Holdings"])
        self.assertEqual(victoria_point["leasing_arrangement"], "In-house")
        self.assertNotIn("gla_sqm", victoria_point)
        self.assertNotIn("tenancy_count", victoria_point)

        southgate = self.payload["property_summaries"]["place-au-nsw-southgate-shopping-centre"]
        self.assertEqual(southgate["centre_class"], "Sub-regional")
        self.assertEqual(southgate["owner_names"], ["IFM Real Estate Core Fund"])
        self.assertEqual(southgate["manager_names"], ["IFM Investors"])
        self.assertEqual(southgate["leasing_arrangement"], "In-house")
        self.assertEqual(southgate["gla_sqm"], 23676)

    def test_runaway_bay_and_sugarland_preserve_group_level_unknowns(self) -> None:
        runaway_bay = self.payload["property_summaries"]["place-au-qld-runaway-bay-shopping-village"]
        self.assertEqual(runaway_bay["centre_class"], "Sub-regional")
        self.assertEqual(runaway_bay["research_status"], "Partial")
        self.assertEqual(runaway_bay["owner_names"], ["Greenpool Capital"])
        self.assertEqual(runaway_bay["manager_names"], ["Greenpool Management Co Pty Ltd"])
        self.assertEqual(runaway_bay["leasing_arrangement"], "In-house")

        sugarland = self.payload["property_summaries"]["place-au-qld-sugarland-shoppingtown"]
        self.assertEqual(sugarland["centre_class"], "Sub-regional")
        self.assertEqual(sugarland["research_status"], "Partial")
        self.assertEqual(sugarland["owner_names"], ["MA Financial"])
        self.assertEqual(sugarland["manager_names"], ["RetPro"])
        self.assertEqual(sugarland["leasing_arrangement"], "In-house")
        self.assertEqual(sugarland["tenancy_count"], 62)

        groups = {group["group_id"]: group for group in self.payload["groups"]}
        self.assertEqual(groups["group-retpro"]["parent_group_id"], "group-ma-financial")
        self.assertEqual(groups["group-greenpool-management"]["parent_group_id"], "group-greenpool-capital")

    def test_casuarina_rosebud_and_winston_hills_roles_are_current_and_explicit(self) -> None:
        casuarina = self.payload["property_summaries"]["place-au-nt-casuarina-square"]
        self.assertEqual(casuarina["centre_class"], "Regional")
        self.assertEqual(casuarina["research_status"], "Verified")
        self.assertEqual(casuarina["owner_names"], ["Casuarina Investment Fund"])
        self.assertEqual(casuarina["manager_names"], ["Sentinel Property Group"])
        self.assertEqual(casuarina["leasing_arrangement"], "In-house")
        self.assertEqual(casuarina["gla_sqm"], 54328)

        rosebud = self.payload["property_summaries"]["place-au-vic-rosebud-plaza-shopping-centre"]
        self.assertEqual(rosebud["centre_class"], "Sub-regional")
        self.assertEqual(rosebud["research_status"], "Verified")
        self.assertEqual(rosebud["owner_names"], ["Arkadia"])
        self.assertEqual(rosebud["manager_names"], ["Arkadia"])
        self.assertEqual(rosebud["leasing_arrangement"], "In-house")
        self.assertEqual(rosebud["tenancy_count"], 61)

        winston_hills = self.payload["property_summaries"]["place-au-nsw-winston-hills-mall"]
        self.assertEqual(winston_hills["centre_class"], "Sub-regional")
        self.assertEqual(winston_hills["research_status"], "Partial")
        self.assertEqual(winston_hills["owner_names"], ["The Vicfam Trust & The BME Unit Trust"])
        self.assertEqual(winston_hills["manager_names"], ["TGC Retail"])
        self.assertEqual(winston_hills["leasing_arrangement"], "External agency")
        self.assertNotIn("gla_sqm", winston_hills)
        self.assertNotIn("tenancy_count", winston_hills)

    def test_current_bunbury_livingston_and_maddington_roles_are_explicit(self) -> None:
        bunbury = self.payload["property_summaries"]["place-au-wa-bunbury-centrepoint"]
        self.assertEqual(bunbury["centre_class"], "Sub-regional")
        self.assertEqual(bunbury["research_status"], "Verified")
        self.assertEqual(
            bunbury["owner_names"],
            ["Bunbury Centrepoint Shopping Centre Investment Trust"],
        )
        self.assertEqual(
            set(bunbury["manager_names"]),
            {"Centuria Capital Group", "Cygnet West"},
        )
        self.assertEqual(bunbury["leasing_arrangement"], "External agency")
        self.assertEqual(bunbury["gla_sqm"], 16813)
        self.assertEqual(bunbury["tenancy_count"], 32)

        livingston = self.payload["property_summaries"]["place-au-wa-livingston-marketplace"]
        self.assertEqual(livingston["centre_class"], "Sub-regional")
        self.assertEqual(livingston["research_status"], "Verified")
        self.assertEqual(livingston["owner_names"], ["Vicinity Centres"])
        self.assertEqual(livingston["manager_names"], ["Vicinity Centres"])
        self.assertEqual(livingston["leasing_arrangement"], "In-house")
        self.assertEqual(livingston["gla_sqm"], 15592)
        self.assertEqual(livingston["tenancy_count"], 47)
        self.assertEqual(livingston["annual_visits"], 2900000)

        maddington = self.payload["property_summaries"]["place-au-wa-maddington-centro-shopping-centre"]
        self.assertEqual(maddington["centre_class"], "Sub-regional")
        self.assertEqual(maddington["research_status"], "Partial")
        self.assertEqual(maddington["owner_names"], ["Realside Property"])
        self.assertEqual(maddington["manager_names"], ["Sirona Urban"])
        self.assertEqual(maddington["leasing_arrangement"], "In-house")
        self.assertEqual(maddington["gla_sqm"], 27661)

    def test_current_plumpton_and_dandenong_roles_preserve_known_unknowns(self) -> None:
        plumpton = self.payload["property_summaries"]["place-au-nsw-plumpton-marketplace"]
        self.assertEqual(plumpton["centre_class"], "Sub-regional")
        self.assertEqual(plumpton["research_status"], "Partial")
        self.assertEqual(plumpton["owner_names"], ["HMC Australian Retail Partnership"])
        self.assertEqual(plumpton["manager_names"], ["HMC Capital"])
        self.assertEqual(plumpton["leasing_arrangement"], "Unknown")
        self.assertEqual(plumpton["gla_sqm"], 18132)

        dandenong = self.payload["property_summaries"]["place-au-vic-dandenong-square"]
        self.assertEqual(dandenong["centre_class"], "Regional")
        self.assertEqual(dandenong["research_status"], "Verified")
        self.assertEqual(dandenong["owner_names"], ["Dandenong Plaza JV Unit Trust"])
        self.assertEqual(dandenong["manager_names"], ["JLL"])
        self.assertEqual(dandenong["leasing_arrangement"], "External agency")
        self.assertNotIn("gla_sqm", dandenong)
        self.assertNotIn("tenancy_count", dandenong)

    def test_current_northam_and_mitcham_roles_preserve_property_structures(self) -> None:
        northam = self.payload["property_summaries"]["place-au-wa-northam-boulevard-shopping-centre"]
        self.assertEqual(northam["centre_class"], "Sub-regional")
        self.assertEqual(northam["research_status"], "Verified")
        self.assertEqual(northam["owner_names"], ["Perdaman Commercial Properties"])
        self.assertEqual(northam["manager_names"], ["Perdaman Commercial Properties"])
        self.assertEqual(northam["leasing_arrangement"], "External agency")
        self.assertEqual(northam["tenancy_count"], 24)

        mitcham = self.payload["property_summaries"]["place-au-sa-mitcham-shopping-centre"]
        self.assertEqual(mitcham["centre_class"], "Sub-regional")
        self.assertEqual(mitcham["research_status"], "Partial")
        self.assertEqual(
            mitcham["owner_names"],
            ["Mitcham Shopping Centre Proprietary Limited"],
        )
        self.assertEqual(mitcham["manager_names"], ["Taplin Real Estate Group"])
        self.assertEqual(mitcham["leasing_arrangement"], "In-house")
        self.assertEqual(mitcham["tenancy_count"], 62)

    def test_bridge_mall_is_not_modelled_as_a_single_property(self) -> None:
        bridge_mall = self.payload["property_summaries"]["place-au-vic-ballarat-bridge-mall"]
        self.assertEqual(bridge_mall["research_status"], "Verified unknown")
        self.assertEqual(bridge_mall["owner_names"], [])
        self.assertEqual(bridge_mall["manager_names"], [])
        self.assertEqual(bridge_mall["leasing_arrangement"], "Unknown")

    def test_mcconaghy_centres_use_current_names_roles_and_exact_metrics(self) -> None:
        lismore = self.payload["property_summaries"]["place-au-nsw-lismore-shopping-centre"]
        self.assertEqual(lismore["research_status"], "Verified")
        self.assertEqual(lismore["centre_class"], "Sub-regional")
        self.assertEqual(lismore["owner_names"], ["McConaghy Group"])
        self.assertEqual(lismore["manager_names"], ["McConaghy Group"])
        self.assertEqual(lismore["leasing_arrangement"], "In-house")
        self.assertEqual(lismore["gla_sqm"], 29901)
        self.assertEqual(lismore["tenancy_count"], 69)

        kingaroy = self.payload["property_summaries"]["place-au-qld-kingaroy-plaza"]
        self.assertEqual(kingaroy["research_status"], "Verified")
        self.assertEqual(kingaroy["centre_class"], "Sub-regional")
        self.assertEqual(kingaroy["owner_names"], ["McConaghy Group"])
        self.assertEqual(kingaroy["manager_names"], ["McConaghy Group"])
        self.assertEqual(kingaroy["leasing_arrangement"], "In-house")
        self.assertEqual(kingaroy["gla_sqm"], 13005)
        self.assertEqual(kingaroy["tenancy_count"], 45)

    def test_current_sa_priority_roles_and_strata_unknowns_are_explicit(self) -> None:
        brickworks = self.payload["property_summaries"]["place-au-sa-brickworks-marketplace"]
        self.assertEqual(brickworks["research_status"], "Partial")
        self.assertEqual(brickworks["centre_class"], "Sub-regional")
        self.assertEqual(brickworks["owner_names"], ["Brickworks Marketplace Fund"])
        self.assertEqual(brickworks["manager_names"], ["FRP Capital"])
        self.assertEqual(brickworks["leasing_arrangement"], "In-house")
        self.assertNotIn("gla_sqm", brickworks)
        self.assertNotIn("tenancy_count", brickworks)

        westland = self.payload["property_summaries"]["place-au-sa-whyalla-westland-shopping-centre"]
        self.assertEqual(westland["research_status"], "Partial")
        self.assertEqual(westland["centre_class"], "Sub-regional")
        self.assertEqual(westland["owner_names"], ["Westlands Unit Trust"])
        self.assertEqual(westland["manager_names"], ["PPI Funds Management"])
        self.assertEqual(westland["leasing_arrangement"], "External agency")
        self.assertEqual(westland["annual_visits"], 3000000)

        northcote = self.payload["property_summaries"]["place-au-vic-northcote-plaza"]
        self.assertEqual(northcote["research_status"], "Partial")
        self.assertEqual(northcote["centre_class"], "Neighbourhood")
        self.assertEqual(northcote["owner_names"], [])
        self.assertEqual(northcote["manager_names"], [])
        self.assertEqual(northcote["leasing_arrangement"], "Unknown")

        cuba_mall = self.payload["property_summaries"]["place-nz-wellington-cnr-cuba-mall-and-dixon-street"]
        self.assertEqual(cuba_mall["research_status"], "Verified unknown")
        self.assertEqual(cuba_mall["owner_names"], [])
        self.assertEqual(cuba_mall["manager_names"], [])
        self.assertEqual(cuba_mall["leasing_arrangement"], "Unknown")

    def test_current_charter_hall_nsw_batch_has_explicit_fund_and_management_roles(self) -> None:
        expected = {
            "place-au-nsw-armidale-central": {
                "owner": "Charter Hall Retail REIT",
                "gla": None,
                "tenants": None,
            },
            "place-au-nsw-carnes-hill-marketplace": {
                "owner": "Retail Partnership No.1",
                "gla": 17899,
                "tenants": 44,
            },
            "place-au-nsw-chullora-marketplace": {
                "owner": "Charter Hall Convenience Retail Fund",
                "gla": None,
                "tenants": None,
            },
            "place-au-nsw-highlands-marketplace": {
                "owner": "Retail Partnership No.1",
                "gla": 16480,
                "tenants": 37,
            },
        }
        for place_id, expected_values in expected.items():
            with self.subTest(place_id=place_id):
                summary = self.payload["property_summaries"][place_id]
                self.assertEqual(summary["research_status"], "Verified")
                self.assertEqual(summary["centre_class"], "Sub-regional")
                self.assertEqual(summary["owner_names"], [expected_values["owner"]])
                self.assertEqual(summary["manager_names"], ["Charter Hall"])
                self.assertEqual(summary["leasing_arrangement"], "In-house")
                if expected_values["gla"] is None:
                    self.assertNotIn("gla_sqm", summary)
                else:
                    self.assertEqual(summary["gla_sqm"], expected_values["gla"])
                if expected_values["tenants"] is None:
                    self.assertNotIn("tenancy_count", summary)
                else:
                    self.assertEqual(summary["tenancy_count"], expected_values["tenants"])

    def test_current_charter_hall_sydney_and_hunter_batch_preserves_fund_and_leasing_roles(self) -> None:
        groups = {group["group_id"]: group for group in self.groups}
        rp6 = groups["group-charter-hall-rp6"]
        self.assertEqual(rp6["canonical_name"], "Retail Partnership No.6")
        self.assertEqual(rp6["parent_group_id"], "group-charter-hall")
        self.assertIn("RP6", rp6["aliases"])

        expected = {
            "place-au-nsw-bonnyrigg-plaza": {
                "owner": "Charter Hall Convenience Retail Fund",
                "class": "Sub-regional",
                "arrangement": "External agency",
                "gla": None,
            },
            "place-au-nsw-bondi-junction-eastgate": {
                "owner": "Retail Partnership No.6",
                "class": "Sub-regional",
                "arrangement": "External agency",
                "gla": 15046,
            },
            "place-au-nsw-bass-hill-plaza": {
                "owner": "Retail Partnership No.6",
                "class": "Sub-regional",
                "arrangement": "External agency",
                "gla": 20379,
            },
            "place-au-nsw-morisset-square": {
                "owner": "Charter Hall Retail REIT",
                "class": "Neighbourhood",
                "arrangement": "In-house",
                "gla": 7941,
            },
        }
        for place_id, expected_values in expected.items():
            with self.subTest(place_id=place_id):
                summary = self.payload["property_summaries"][place_id]
                self.assertEqual(summary["research_status"], "Verified")
                self.assertEqual(summary["centre_class"], expected_values["class"])
                self.assertEqual(summary["owner_names"], [expected_values["owner"]])
                self.assertEqual(summary["manager_names"], ["Charter Hall"])
                self.assertEqual(summary["leasing_arrangement"], expected_values["arrangement"])
                if expected_values["gla"] is None:
                    self.assertNotIn("gla_sqm", summary)
                else:
                    self.assertEqual(summary["gla_sqm"], expected_values["gla"])

        for place_id in {
            "place-au-nsw-bonnyrigg-plaza",
            "place-au-nsw-bondi-junction-eastgate",
            "place-au-nsw-bass-hill-plaza",
        }:
            self.assertIn("group-jll", self.payload["property_summaries"][place_id]["group_ids"])
        self.assertNotIn("group-jll", self.payload["property_summaries"]["place-au-nsw-morisset-square"]["group_ids"])

    def test_current_pacific_casula_richmond_and_grove_roles_are_explicit(self) -> None:
        groups = {group["group_id"]: group for group in self.groups}
        self.assertEqual(
            groups["group-dexus-wholesale-australian-property-fund"]["brand_name"],
            "DWAPF",
        )
        self.assertEqual(
            groups["group-mintus-grove-square-trust"]["parent_group_id"],
            "group-mintus",
        )

        pacific = self.payload["property_summaries"]["place-au-nsw-pacific-square-shopping-centre"]
        self.assertEqual(pacific["research_status"], "Verified")
        self.assertEqual(pacific["centre_class"], "Neighbourhood")
        self.assertEqual(pacific["owner_names"], ["Retail Partnership No.6"])
        self.assertEqual(pacific["manager_names"], ["Charter Hall"])
        self.assertEqual(pacific["leasing_arrangement"], "External agency")
        self.assertEqual(pacific["gla_sqm"], 13710)
        self.assertIn("group-jll", pacific["group_ids"])

        casula = self.payload["property_summaries"]["place-au-nsw-casula-mall"]
        self.assertEqual(casula["research_status"], "Verified")
        self.assertEqual(casula["centre_class"], "Sub-regional")
        self.assertEqual(casula["owner_names"], ["Dexus Wholesale Australian Property Fund"])
        self.assertEqual(casula["manager_names"], ["Dexus"])
        self.assertEqual(casula["leasing_arrangement"], "In-house")
        self.assertEqual(casula["gla_sqm"], 20025)

        richmond = self.payload["property_summaries"]["place-au-nsw-richmond-marketplace"]
        self.assertEqual(richmond["research_status"], "Partial")
        self.assertEqual(richmond["centre_class"], "Sub-regional")
        self.assertEqual(richmond["owner_names"], [])
        self.assertEqual(richmond["manager_names"], ["IFM Investors"])
        self.assertEqual(richmond["leasing_arrangement"], "In-house")
        self.assertEqual(richmond["gla_sqm"], 18685)
        self.assertEqual(richmond["tenancy_count"], 58)

        grove = self.payload["property_summaries"]["place-au-nsw-grove-square"]
        self.assertEqual(grove["research_status"], "Verified")
        self.assertEqual(grove["centre_class"], "Sub-regional")
        self.assertEqual(
            grove["owner_names"],
            ["Mintus Investments Pty Ltd ATF The Retail Investment Trust 4"],
        )
        self.assertEqual(grove["manager_names"], ["Mintus Pty Ltd"])
        self.assertEqual(grove["leasing_arrangement"], "In-house")
        self.assertEqual(grove["tenancy_count"], 83)

    def test_current_homeco_north_rocks_and_lidcombe_batch_preserves_known_unknowns(self) -> None:
        groups = {group["group_id"]: group for group in self.groups}
        self.assertEqual(groups["group-homeco-daily-needs-reit"]["brand_name"], "HDN")
        self.assertEqual(
            groups["group-hmc-last-mile-logistics-property-trust-1"]["parent_group_id"],
            "group-hmc-capital",
        )

        glenmore = self.payload["property_summaries"]["place-au-nsw-glenmore-park-town-centre"]
        self.assertEqual(glenmore["research_status"], "Verified")
        self.assertEqual(glenmore["centre_class"], "Neighbourhood")
        self.assertEqual(glenmore["owner_names"], ["HomeCo Daily Needs REIT"])
        self.assertEqual(glenmore["manager_names"], ["HMC Capital"])
        self.assertEqual(glenmore["leasing_arrangement"], "External agency")
        self.assertEqual(glenmore["gla_sqm"], 19793)

        menai = self.payload["property_summaries"]["place-au-nsw-menai-marketplace-shopping-centre"]
        self.assertEqual(menai["research_status"], "Verified")
        self.assertEqual(menai["centre_class"], "Sub-regional")
        self.assertEqual(menai["owner_names"], ["HMC Last Mile Logistics Property Trust 1"])
        self.assertEqual(menai["manager_names"], ["HMC Capital"])
        self.assertEqual(menai["leasing_arrangement"], "External agency")
        self.assertEqual(menai["gla_sqm"], 17041)

        north_rocks = self.payload["property_summaries"]["place-au-nsw-north-rocks-shopping-centre"]
        self.assertEqual(north_rocks["research_status"], "Partial")
        self.assertEqual(north_rocks["centre_class"], "Sub-regional")
        self.assertEqual(north_rocks["owner_names"], [])
        self.assertEqual(north_rocks["manager_names"], [])
        self.assertEqual(north_rocks["leasing_arrangement"], "External agency")
        self.assertEqual(north_rocks["group_ids"], ["group-jll"])

        lidcombe = self.payload["property_summaries"]["place-au-nsw-lidcombe-shopping-centre"]
        self.assertEqual(lidcombe["research_status"], "Partial")
        self.assertEqual(lidcombe["centre_class"], "Sub-regional")
        self.assertEqual(lidcombe["owner_names"], ["Lidcombe Property Holdings Unit Trust"])
        self.assertEqual(lidcombe["manager_names"], [])
        self.assertEqual(lidcombe["leasing_arrangement"], "External agency")
        self.assertIn("group-jll", lidcombe["group_ids"])

    def test_current_tweed_warrawong_and_orana_batch_preserves_distinct_roles(self) -> None:
        groups = {group["group_id"]: group for group in self.groups}
        self.assertEqual(
            groups["group-tweed-mall-mixed-use-real-estate-fund"]["parent_group_id"],
            "group-elanor-investors",
        )
        self.assertEqual(
            groups["group-warrawong-plaza-fund"]["parent_group_id"],
            "group-elanor-investors",
        )

        tweed = self.payload["property_summaries"]["place-au-nsw-tweed-mall"]
        self.assertEqual(tweed["research_status"], "Verified")
        self.assertEqual(tweed["centre_class"], "Sub-regional")
        self.assertEqual(tweed["owner_names"], ["Tweed Mall Mixed-Use Real Estate Fund"])
        self.assertEqual(tweed["manager_names"], ["JLL"])
        self.assertEqual(tweed["leasing_arrangement"], "External agency")
        self.assertEqual(tweed["gla_sqm"], 23324)

        warrawong = self.payload["property_summaries"]["place-au-nsw-warrawong-plaza-shopping-centre"]
        self.assertEqual(warrawong["research_status"], "Partial")
        self.assertEqual(warrawong["centre_class"], "Sub-regional")
        self.assertEqual(warrawong["owner_names"], ["Warrawong Plaza Fund"])
        self.assertEqual(warrawong["manager_names"], [])
        self.assertEqual(warrawong["leasing_arrangement"], "External agency")
        self.assertIn("group-kyron-capital", warrawong["group_ids"])

        orana = self.payload["property_summaries"]["place-au-nsw-orana-mall-marketplace"]
        self.assertEqual(orana["research_status"], "Partial")
        self.assertEqual(orana["centre_class"], "Sub-regional")
        self.assertEqual(orana["owner_names"], [])
        self.assertEqual(orana["manager_names"], ["Bachrach Naumburger Group"])
        self.assertEqual(orana["leasing_arrangement"], "In-house")
        self.assertEqual(orana["gla_sqm"], 23683.41)

    def test_current_bathurst_carlingford_cessnock_and_stanhope_roles_are_explicit(self) -> None:
        groups = {group["group_id"]: group for group in self.groups}
        self.assertEqual(groups["group-jy-no8-trust"]["parent_group_id"], "group-jy-group")
        self.assertEqual(
            groups["group-hmc-lml-no5-property-trust"]["parent_group_id"],
            "group-hmc-capital",
        )
        self.assertEqual(
            groups["group-qic-active-retail-property-fund"]["parent_group_id"],
            "group-qic",
        )

        bathurst = self.payload["property_summaries"]["place-au-nsw-bathurst-city-centre"]
        self.assertEqual(bathurst["research_status"], "Verified")
        self.assertEqual(bathurst["centre_class"], "Sub-regional")
        self.assertEqual(bathurst["owner_names"], ["QIC Active Retail Property Fund"])
        self.assertEqual(bathurst["manager_names"], ["QIC Real Estate"])
        self.assertEqual(bathurst["leasing_arrangement"], "In-house")
        self.assertEqual(bathurst["gla_sqm"], 12433)
        self.assertEqual(bathurst["tenancy_count"], 40)
        self.assertEqual(bathurst["annual_visits"], 2200000)

        carlingford = self.payload["property_summaries"]["place-au-nsw-carlingford-court"]
        self.assertEqual(carlingford["research_status"], "Partial")
        self.assertEqual(carlingford["centre_class"], "Sub-regional")
        self.assertEqual(
            carlingford["owner_names"],
            ["JY No.8 Trust", "HMC LML No. 5 Property Trust"],
        )
        self.assertEqual(carlingford["manager_names"], ["Vicinity Centres"])
        self.assertEqual(carlingford["leasing_arrangement"], "Unknown")

        cessnock = self.payload["property_summaries"]["place-au-nsw-cessnock-plaza-shopping-centre"]
        self.assertEqual(cessnock["research_status"], "Partial")
        self.assertEqual(cessnock["centre_class"], "Neighbourhood")
        self.assertEqual(cessnock["owner_names"], [])
        self.assertEqual(cessnock["manager_names"], ["RetPro"])
        self.assertEqual(cessnock["leasing_arrangement"], "In-house")

        stanhope = self.payload["property_summaries"]["place-au-nsw-stanhope-village-shopping-centre"]
        self.assertEqual(stanhope["research_status"], "Verified")
        self.assertEqual(stanhope["centre_class"], "Sub-regional")
        self.assertEqual(stanhope["owner_names"], ["Revelop"])
        self.assertEqual(stanhope["manager_names"], ["Revelop"])
        self.assertEqual(stanhope["leasing_arrangement"], "In-house")
        self.assertEqual(stanhope["gla_sqm"], 19454)
        self.assertEqual(stanhope["annual_visits"], 8000000)

    def test_current_salamander_rockdale_deepwater_and_crown_roles_are_explicit(self) -> None:
        groups = {group["group_id"]: group for group in self.groups}
        self.assertEqual(
            groups["group-charter-hall-prime-retail-fund"]["parent_group_id"],
            "group-charter-hall",
        )
        self.assertEqual(groups["group-charter-hall-prime-retail-fund"]["brand_name"], "CPRF")
        self.assertEqual(groups["group-raptis-investments"]["group_type"], "PROPERTY_COMPANY")

        salamander = self.payload["property_summaries"]["place-au-nsw-salamander-shopping-centre"]
        self.assertEqual(salamander["research_status"], "Verified")
        self.assertEqual(salamander["centre_class"], "Sub-regional")
        self.assertEqual(
            salamander["owner_names"],
            ["Charter Hall Retail REIT", "Charter Hall Prime Retail Fund"],
        )
        self.assertEqual(salamander["manager_names"], ["Charter Hall"])
        self.assertEqual(salamander["leasing_arrangement"], "External agency")
        self.assertEqual(salamander["gla_sqm"], 23875)
        self.assertIn("group-jll", salamander["group_ids"])

        rockdale = self.payload["property_summaries"]["place-au-nsw-rockdale-plaza-drive"]
        self.assertEqual(rockdale["research_status"], "Verified")
        self.assertEqual(rockdale["centre_class"], "Sub-regional")
        self.assertEqual(rockdale["owner_names"], ["Charter Hall Convenience Retail Fund"])
        self.assertEqual(rockdale["manager_names"], ["Charter Hall"])
        self.assertEqual(rockdale["leasing_arrangement"], "External agency")
        self.assertEqual(rockdale["gla_sqm"], 21608)

        deepwater = self.payload["property_summaries"]["place-au-nsw-deepwater-plaza-centre"]
        self.assertEqual(deepwater["research_status"], "Verified")
        self.assertEqual(deepwater["centre_class"], "Sub-regional")
        self.assertEqual(deepwater["owner_names"], ["Raptis Investments Pty Ltd"])
        self.assertEqual(deepwater["manager_names"], ["Raptis Investments Pty Ltd"])
        self.assertEqual(deepwater["leasing_arrangement"], "In-house")

        crown = self.payload["property_summaries"]["place-au-nsw-crown-st-mall"]
        self.assertEqual(crown["research_status"], "Verified unknown")
        self.assertEqual(crown["centre_class"], "Unknown")
        self.assertEqual(crown["owner_names"], [])
        self.assertEqual(crown["manager_names"], [])
        self.assertEqual(crown["leasing_arrangement"], "Unknown")

    def test_current_lake_haven_riverside_glendale_and_grafton_roles_are_explicit(self) -> None:
        groups = {group["group_id"]: group for group in self.groups}
        self.assertEqual(groups["group-ip-generation"]["parent_group_id"], "group-ma-financial")
        self.assertEqual(groups["group-mcconaghy"]["canonical_name"], "McConaghy Group")
        self.assertEqual(
            groups["group-riverside-plaza-syndicate"]["parent_group_id"],
            "group-elanor-investors",
        )

        glendale = self.payload["property_summaries"]["place-au-nsw-glendale-stockland-shopping-centre"]
        self.assertEqual(glendale["research_status"], "Verified")
        self.assertEqual(glendale["centre_class"], "Sub-regional")
        self.assertEqual(glendale["owner_names"], ["IP Generation"])
        self.assertEqual(glendale["manager_names"], ["RetPro"])
        self.assertEqual(glendale["leasing_arrangement"], "In-house")

        grafton = self.payload["property_summaries"]["place-au-nsw-grafton-shoppingworld"]
        self.assertEqual(grafton["research_status"], "Partial")
        self.assertEqual(grafton["centre_class"], "Sub-regional")
        self.assertEqual(grafton["owner_names"], [])
        self.assertEqual(grafton["manager_names"], ["McConaghy Group"])
        self.assertEqual(grafton["leasing_arrangement"], "In-house")

        lake_haven = self.payload["property_summaries"]["place-au-nsw-lake-haven-shopping-centre"]
        self.assertEqual(lake_haven["research_status"], "Verified")
        self.assertEqual(lake_haven["centre_class"], "Sub-regional")
        self.assertEqual(lake_haven["owner_names"], ["Vicinity Centres"])
        self.assertEqual(lake_haven["manager_names"], ["Vicinity Centres"])
        self.assertEqual(lake_haven["leasing_arrangement"], "In-house")
        self.assertEqual(lake_haven["gla_sqm"], 43205)
        self.assertEqual(lake_haven["annual_visits"], 5700000)

        riverside = self.payload["property_summaries"]["place-au-nsw-riverside-plaza-queanbeyan"]
        self.assertEqual(riverside["research_status"], "Verified")
        self.assertEqual(riverside["centre_class"], "Sub-regional")
        self.assertEqual(riverside["owner_names"], ["Riverside Plaza Syndicate"])
        self.assertEqual(riverside["manager_names"], ["RetPro"])
        self.assertEqual(riverside["leasing_arrangement"], "In-house")
        self.assertEqual(riverside["gla_sqm"], 22787)

    def test_current_hyperdome_and_sunshine_plaza_property_structures_are_explicit(self) -> None:
        groups = {group["group_id"]: group for group in self.groups}
        self.assertEqual(
            groups["group-ma-hyperdome-town-centre-fund"]["parent_group_id"],
            "group-ma-financial",
        )

        hyperdome = self.payload["property_summaries"]["place-au-qld-logan-hyperdome"]
        self.assertEqual(hyperdome["research_status"], "Verified")
        self.assertEqual(hyperdome["centre_class"], "Regional")
        self.assertEqual(hyperdome["centre_class_method"], "Inferred")
        self.assertEqual(hyperdome["owner_names"], ["MA Hyperdome Town Centre Fund"])
        self.assertEqual(hyperdome["manager_names"], ["MA Financial"])
        self.assertEqual(hyperdome["leasing_arrangement"], "External agency")
        self.assertEqual(hyperdome["gla_sqm"], 72374)
        self.assertEqual(hyperdome["tenancy_count"], 180)
        self.assertEqual(hyperdome["annual_visits"], 9200000)

        hyperdome_roles = {
            (row["group_id"], row["role"])
            for row in self.relationships
            if row["place_id"] == "place-au-qld-logan-hyperdome"
        }
        self.assertTrue(
            {
                ("group-ma-hyperdome-town-centre-fund", "OWNER"),
                ("group-ma-financial", "MANAGER"),
                ("group-ma-financial", "OPERATOR"),
                ("group-qic", "LEASING_CONTROLLER"),
                ("group-qic", "EXTERNAL_LEASING_AGENT"),
            }.issubset(hyperdome_roles)
        )

        sunshine = self.payload["property_summaries"]["place-au-qld-sunshine-plaza"]
        self.assertEqual(sunshine["research_status"], "Verified")
        self.assertEqual(sunshine["centre_class"], "Super Regional")
        self.assertEqual(sunshine["centre_class_method"], "Confirmed")
        self.assertEqual(
            sunshine["owner_names"],
            ["GPT Group", "GPT Wholesale Shopping Centre Fund"],
        )
        self.assertEqual(sunshine["manager_names"], ["GPT Group"])
        self.assertEqual(sunshine["leasing_arrangement"], "In-house")
        self.assertEqual(sunshine["gla_sqm"], 106600)

        sunshine_roles = {
            (row["group_id"], row["role"])
            for row in self.relationships
            if row["place_id"] == "place-au-qld-sunshine-plaza"
        }
        self.assertTrue(
            {
                ("group-gpt", "CO_OWNER"),
                ("group-gpt-wholesale-shopping-centre-fund", "CO_OWNER"),
                ("group-gpt", "MANAGER"),
                ("group-gpt", "OPERATOR"),
                ("group-gpt", "LEASING_CONTROLLER"),
            }.issubset(sunshine_roles)
        )

    def test_current_bayside_cranbourne_elizabeth_and_galleria_profiles_are_explicit(self) -> None:
        bayside = self.payload["property_summaries"]["place-au-vic-frankston-bayside-centre"]
        self.assertEqual(bayside["research_status"], "Verified")
        self.assertEqual(bayside["centre_class"], "Regional")
        self.assertEqual(bayside["owner_names"], ["Vicinity Centres"])
        self.assertEqual(bayside["manager_names"], ["Vicinity Centres"])
        self.assertEqual(bayside["leasing_arrangement"], "In-house")
        self.assertEqual(bayside["gla_sqm"], 90435)
        self.assertEqual(bayside["annual_visits"], 11400000)

        cranbourne = self.payload["property_summaries"][
            "place-au-vic-cranbourne-park-shopping-centre-sp107"
        ]
        self.assertEqual(cranbourne["research_status"], "Verified")
        self.assertEqual(cranbourne["centre_class"], "Regional")
        self.assertEqual(cranbourne["owner_names"], ["IP Generation", "Vicinity Centres"])
        self.assertEqual(cranbourne["manager_names"], ["Vicinity Centres"])
        self.assertEqual(cranbourne["leasing_arrangement"], "In-house")
        self.assertEqual(cranbourne["gla_sqm"], 46200)
        self.assertEqual(cranbourne["annual_visits"], 6300000)

        elizabeth = self.payload["property_summaries"]["place-au-sa-elizabeth-shopping-centre"]
        self.assertEqual(elizabeth["research_status"], "Partial")
        self.assertEqual(elizabeth["centre_class"], "Regional")
        self.assertEqual(elizabeth["owner_names"], ["Vicinity Centres"])
        self.assertEqual(elizabeth["manager_names"], ["Vicinity Centres"])
        self.assertEqual(elizabeth["leasing_arrangement"], "In-house")
        self.assertEqual(elizabeth["gla_sqm"], 79981)
        self.assertEqual(elizabeth["annual_visits"], 7000000)

        galleria = self.payload["property_summaries"]["place-au-wa-morley-galleria"]
        self.assertEqual(galleria["research_status"], "Verified")
        self.assertEqual(galleria["centre_class"], "Regional")
        self.assertEqual(galleria["owner_names"], ["Vicinity Centres", "Perron Group"])
        self.assertEqual(galleria["manager_names"], ["Vicinity Centres"])
        self.assertEqual(galleria["leasing_arrangement"], "In-house")
        self.assertEqual(galleria["gla_sqm"], 75359)

        galleria_roles = {
            (row["group_id"], row["role"])
            for row in self.relationships
            if row["place_id"] == "place-au-wa-morley-galleria"
        }
        self.assertTrue(
            {
                ("group-vicinity", "CO_OWNER"),
                ("group-perron", "CO_OWNER"),
                ("group-vicinity", "MANAGER"),
                ("group-vicinity", "OPERATOR"),
                ("group-vicinity", "LEASING_CONTROLLER"),
            }.issubset(galleria_roles)
        )

    def test_current_qic_everyday_assets_and_coomera_identity_are_explicit(self) -> None:
        coomera = self.payload["property_summaries"]["place-au-qld-westfield-coomera"]
        self.assertEqual(coomera["research_status"], "Partial")
        self.assertEqual(coomera["centre_class"], "Regional")
        self.assertEqual(coomera["centre_class_method"], "Inferred")
        self.assertEqual(coomera["owner_names"], ["Scentre Group", "QIC Real Estate"])
        self.assertEqual(coomera["leasing_arrangement"], "Unknown")
        self.assertEqual(coomera["gla_sqm"], 57900)
        coomera_roles = {
            (row["group_id"], row["role"], row.get("ownership_percentage"))
            for row in self.relationships
            if row["place_id"] == "place-au-qld-westfield-coomera"
        }
        self.assertIn(("group-scentre", "CO_OWNER", 50.0), coomera_roles)
        self.assertIn(("group-qic", "CO_OWNER", 50.0), coomera_roles)

        expected = {
            "place-au-qld-big-top-shopping-centre": (
                "Neighbourhood", "Inferred", 12226, 18, 2400000
            ),
            "place-au-qld-forest-lake-shopping-centre": (
                "Sub-regional", "Inferred", 21450, 55, 4900000
            ),
            "place-au-qld-the-village-upper-mount-gravatt": (
                "Neighbourhood", "Inferred", 6887, 24, 1100000
            ),
            "place-au-nsw-pittwater-place": (
                "Neighbourhood", "Confirmed", 8135, 26, 2900000
            ),
        }
        for place_id, (centre_class, method, gla, tenancies, visits) in expected.items():
            with self.subTest(place_id=place_id):
                summary = self.payload["property_summaries"][place_id]
                self.assertEqual(summary["research_status"], "Partial")
                self.assertEqual(summary["centre_class"], centre_class)
                self.assertEqual(summary["centre_class_method"], method)
                self.assertEqual(summary["owner_names"], [])
                self.assertEqual(summary["manager_names"], ["QIC Real Estate"])
                self.assertEqual(summary["leasing_arrangement"], "In-house")
                self.assertEqual(summary["gla_sqm"], gla)
                self.assertEqual(summary["tenancy_count"], tenancies)
                self.assertEqual(summary["annual_visits"], visits)
                roles = {
                    (row["group_id"], row["role"])
                    for row in self.relationships
                    if row["place_id"] == place_id
                }
                self.assertTrue(
                    {
                        ("group-qic", "MANAGER"),
                        ("group-qic", "OPERATOR"),
                        ("group-qic", "LEASING_CONTROLLER"),
                    }.issubset(roles)
                )

        review_ids = {item["review_id"] for item in self.payload["review_items"]}
        self.assertFalse(any(review_id.startswith("review-portfolio-qic-") for review_id in review_ids))

    def test_current_stockland_baringa_and_piccadilly_profiles_are_explicit(self) -> None:
        baringa = self.payload["property_summaries"][
            "place-au-qld-stockland-baringa-shopping-centre"
        ]
        self.assertEqual(baringa["research_status"], "Verified")
        self.assertEqual(baringa["centre_class"], "Neighbourhood")
        self.assertEqual(baringa["centre_class_method"], "Confirmed")
        self.assertEqual(baringa["owner_names"], ["Stockland"])
        self.assertEqual(baringa["manager_names"], ["Stockland"])
        self.assertEqual(baringa["leasing_arrangement"], "In-house")
        self.assertEqual(baringa["gla_sqm"], 6972)
        self.assertEqual(baringa["tenancy_count"], 16)

        piccadilly = self.payload["property_summaries"][
            "place-au-nsw-stockland-piccadilly-shopping-centre"
        ]
        self.assertEqual(piccadilly["research_status"], "Verified")
        self.assertEqual(piccadilly["centre_class"], "CBD / Mixed-use")
        self.assertEqual(piccadilly["centre_class_method"], "Confirmed")
        self.assertEqual(piccadilly["owner_names"], ["Stockland"])
        self.assertEqual(piccadilly["manager_names"], ["Stockland"])
        self.assertEqual(piccadilly["leasing_arrangement"], "In-house")
        self.assertEqual(piccadilly["gla_sqm"], 2983)

        review_ids = {item["review_id"] for item in self.payload["review_items"]}
        self.assertNotIn("review-portfolio-stockland-fy26-baringa", review_ids)
        self.assertNotIn("review-portfolio-stockland-fy26-piccadilly", review_ids)

    def test_property_summaries_cover_every_place_and_unknown_is_explicit(self) -> None:
        summaries = self.payload["property_summaries"]
        self.assertEqual(set(summaries), {place["place_id"] for place in self.places})
        for summary in summaries.values():
            self.assertIn(summary["centre_class"], {
                "Super Regional", "Regional", "Sub-regional", "Neighbourhood", "CBD / Mixed-use",
                "Outlet", "Large Format", "Other", "Unknown",
            })
            self.assertIn(summary["leasing_arrangement"], {"In-house", "External agency", "Private landlord", "Unknown"})
            self.assertIn(summary["portfolio_overlap_status"], {
                "SAME_CENTRE", "LEASING_CONTROLLER_OVERLAP", "PROPERTY_GROUP_OVERLAP",
                "EXTERNAL_AGENCY_OVERLAP", "NO_KNOWN_OVERLAP", "UNKNOWN",
            })

    def test_in_centre_competition_uses_canonical_membership(self) -> None:
        for place_id, summary in self.payload["property_summaries"].items():
            for retailer in summary["competitor_context"]["by_retailer"].values():
                for store in retailer["in_centre"]:
                    self.assertEqual(store["distance_km"] >= 0, True)
                self.assertTrue(all(store["distance_km"] <= 0.25 for store in retailer["nearby_unverified"]))


if __name__ == "__main__":
    unittest.main()
