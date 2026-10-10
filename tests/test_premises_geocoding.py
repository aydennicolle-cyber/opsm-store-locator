"""Address geocoding must not silently turn a weak match into a store pin."""
import copy
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_priority_optical_networks as importer
from premises_geocoding import context, receipt_matches, rejection, without_unit


def premises():
    return dict(id="example", name="Example Optical Browns Plains", country="Australia",
                state="QLD", city="Browns Plains", postal_code="4118",
                full_address="Shop G107 123 Main Road, Browns Plains QLD 4118",
                latitude="", longitude="")


def result(**changes):
    row = dict(lat="-27.663", lon="153.040", category="place", type="house",
               addresstype="house", place_rank=30, osm_type="node", osm_id=123,
               address=dict(country_code="au", state="Queensland", postcode="4118",
                            suburb="Browns Plains", house_number="123", road="Main Road"))
    row.update(changes)
    return row


class PremisesGeocodingTests(unittest.TestCase):
    def test_country_centroid_is_rejected_even_with_locality_in_query(self):
        self.assertIn("broad", rejection(result(lat="-24.7761086", lon="134.755", category="boundary", type="administrative", addresstype="country"), premises()))

    def test_town_road_and_postcode_points_are_not_premises(self):
        for category, kind in [("place", "town"), ("highway", "residential"), ("place", "postcode")]:
            with self.subTest(kind=kind):
                self.assertTrue(rejection(result(category=category, type=kind), premises()))

    def test_numbered_address_survives_unit_and_street_abbreviation(self):
        row = premises()
        row["full_address"] = "Shop G107 123 Main Rd, Browns Plains QLD 4118"
        self.assertEqual(without_unit(row["full_address"]), "123 Main Rd, Browns Plains QLD 4118")
        self.assertEqual(rejection(result(), row), "")
        self.assertEqual(without_unit("Shop 5, Grand Plaza, Browns Plains"), "Grand Plaza, Browns Plains")

    def test_other_house_number_does_not_match_unit_number_or_substring(self):
        for number in ["12", "G107", "124"]:
            value = result()
            value["address"]["house_number"] = number
            self.assertTrue(rejection(value, premises()))

    def test_named_centre_must_exist_in_original_premises_context(self):
        value = result(category="shop", type="mall", addresstype="shop", name="Grand Plaza")
        value["address"].pop("house_number")
        self.assertTrue(rejection(value, premises()))
        row = premises()
        row["full_address"] = "Shop G107, Grand Plaza, Browns Plains QLD 4118"
        self.assertEqual(rejection(value, row), "")

    def test_same_named_suburb_in_wrong_state_or_postcode_is_rejected(self):
        for field, wrong in [("state", "Victoria"), ("postcode", "4119"), ("country_code", "nz")]:
            value = result()
            value["address"][field] = wrong
            self.assertTrue(rejection(value, premises()))

    def test_matching_business_name_does_not_override_conflicting_numbered_street(self):
        value = result(category="shop", type="optician", name="Example Optical")
        value["address"]["house_number"] = "124"
        self.assertIn("conflict", rejection(value, premises()))

    def test_state_name_and_iso_conflict_require_review(self):
        value = result()
        value["address"]["ISO3166-2-lvl4"] = "AU-VIC"
        self.assertIn("conflicting", rejection(value, premises()))

    def test_missing_postcode_requires_locality_agreement(self):
        value = result()
        value["address"].pop("postcode")
        self.assertEqual(rejection(value, premises()), "")
        value["address"].pop("suburb")
        self.assertIn("locality", rejection(value, premises()))

    def test_nz_region_macrons_and_iso_au_state(self):
        row = dict(premises(), country="New Zealand", state="Waikato", city="Te Kuiti", postal_code="3910", full_address="123 Main Rd, Te Kūiti 3910")
        value = result(lat="-38.33", lon="175.16")
        value["address"].update(country_code="nz", state="Waikato Region", suburb="Te Kūiti", postcode="3910")
        self.assertEqual(rejection(value, row), "")
        value = result()
        value["address"].pop("state")
        value["address"]["ISO3166-2-lvl4"] = "AU-QLD"
        self.assertEqual(rejection(value, premises()), "")

    def test_nonfinite_outside_country_and_missing_address_fail(self):
        for value in [result(lat="nan"), result(lon="inf"), result(lat="-5"), result(address={})]:
            self.assertTrue(rejection(value, premises()))

    @patch.object(importer.time, "sleep")
    def test_rejects_first_broad_match_but_accepts_second_premises(self, sleep):
        payload = [result(category="boundary", type="administrative"), result()]
        with patch.object(importer, "fetch_text", return_value=json.dumps(payload)) as fetch:
            receipt = importer.geocode(premises(), [])
        self.assertEqual(receipt["result"], result())
        self.assertIn("addressdetails=1", fetch.call_args.args[0])
        self.assertIn("limit=5", fetch.call_args.args[0])
        self.assertIn("countrycodes=au", fetch.call_args.args[0])
        self.assertTrue(receipt["attempts"][0]["candidates"][0]["rejection"])
        sleep.assert_called_once_with(1.05)

    @patch.object(importer.time, "sleep")
    def test_multiple_eligible_features_require_review(self, sleep):
        with patch.object(importer, "fetch_text", return_value=json.dumps([result(), result(osm_id=456, lon="153.045")])):
            with self.assertRaisesRegex(importer.GeocodingReviewRequired, "Ambiguous"):
                importer.geocode(premises(), [])

    def test_receipt_is_bound_to_context_and_point(self):
        row = premises()
        receipt = dict(context=context(row), result=result(), query=row["full_address"], observed_at="2026-10-04T12:00:00+00:00")
        cached = (row["full_address"], "-27.663", "153.040")
        self.assertTrue(receipt_matches(receipt, row, cached))
        self.assertFalse(receipt_matches(receipt, dict(row, postal_code="4000"), cached))
        self.assertFalse(receipt_matches(receipt, row, (cached[0], "-24.7761086", "134.755")))
        self.assertFalse(receipt_matches({}, row, cached))

    @patch.object(importer.time, "sleep")
    def test_unverified_cache_cannot_bypass_guard_and_old_feed_is_preserved(self, sleep):
        with tempfile.TemporaryDirectory() as directory, patch.object(importer, "ROOT", Path(directory)):
            target = Path(directory) / "retailers" / "example"
            target.mkdir(parents=True)
            row = premises()
            with (target / "stores.csv").open("w") as f:
                writer = csv.DictWriter(f, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(dict(row, latitude="-24.7761086", longitude="134.755"))
            before = (target / "stores.csv").read_bytes()
            with patch.object(importer, "fetch_text", return_value=json.dumps([result(category="boundary", type="administrative")])) as fetch:
                with self.assertRaisesRegex(importer.GeocodingReviewRequired, "source feed preserved"):
                    importer.add_coordinates("example", [row])
            self.assertEqual(before, (target / "stores.csv").read_bytes())
            self.assertEqual(row["latitude"], "")
            queue = json.loads((Path(directory) / "output/priority-geocoding-reviews/example.json").read_text())
            self.assertEqual(len(queue["unresolved"]), 1)
            self.assertTrue(queue["unresolved"][0]["legacy_cache_present"])
            self.assertEqual(fetch.call_count, 2)
            self.assertTrue(all("123" in call.args[0] for call in fetch.call_args_list))

    @patch.object(importer.time, "sleep")
    def test_verified_cache_reuses_original_date_and_only_csv_fields_are_written(self, sleep):
        with tempfile.TemporaryDirectory() as directory, patch.object(importer, "ROOT", Path(directory)):
            row = premises()
            with patch.object(importer, "fetch_text", return_value=json.dumps([result()])):
                importer.add_coordinates("example", [row])
            first_receipt = copy.deepcopy(row["_geocoding_evidence"])
            importer.write_source("example", "https://example.org", [row], "2026-10-04", "fixture")
            replacement = premises()
            with patch.object(importer, "fetch_text", side_effect=AssertionError("Should reuse evidence")):
                importer.add_coordinates("example", [replacement])
            self.assertEqual(replacement["_geocoding_evidence"], first_receipt)
            self.assertEqual(replacement["latitude"], result()["lat"])
            header = (Path(directory) / "retailers/example/stores.csv").read_text().splitlines()[0]
            self.assertNotIn("_geocoding_evidence", header)

    @patch.object(importer.time, "sleep")
    def test_request_failure_is_reviewable_and_rate_limited(self, sleep):
        with patch.object(importer, "fetch_text", side_effect=OSError("Public source unavailable")):
            with self.assertRaises(importer.GeocodingReviewRequired) as raised:
                importer.geocode(premises(), [])
        self.assertEqual(raised.exception.attempts[0]["error"], "Public source unavailable")
        sleep.assert_called_once_with(1.05)

    def test_published_source_coordinates_and_explicit_overrides_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(importer, "ROOT", Path(directory)):
            rows = [dict(premises(), latitude="-27.1", longitude="153.1"), dict(premises(), id="blackwood-5051")]
            with patch.object(importer, "fetch_text", side_effect=AssertionError("Not a geocoded source")):
                importer.add_coordinates("example", rows)
            self.assertEqual(rows[0]["latitude"], "-27.1")
            self.assertEqual((rows[1]["latitude"], rows[1]["longitude"]), importer.COORDINATE_OVERRIDES["blackwood-5051"])


if __name__ == "__main__":
    unittest.main()
