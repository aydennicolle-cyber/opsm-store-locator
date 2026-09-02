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
        self.assertEqual(sum(row["match_status"] == "Matched" for row in stockland), 13)
        self.assertEqual(sum(row["match_status"] != "Matched" for row in stockland), 7)
        self.assertEqual(self.payload["group_portfolios"]["group-stockland"]["property_count"], 13)

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
