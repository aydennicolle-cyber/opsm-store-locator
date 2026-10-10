"""Incremental source admission must not refresh unrelated historical rows."""
import copy
import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_optical_network as network
import build_retail_places as places


class SourceDatesTests(unittest.TestCase):
    def build_address_membership(self, centre_date, fact_date=""):
        store = dict(store_id="opsm-date-example", retailer="OPSM", name="Example Optical",
                     country="Australia", state="VIC", suburb="Melbourne", postcode="3000",
                     full_address="19 High Street", latitude="-37.81", longitude="144.96",
                     status="Active", location_type="Unclassified", venue_id="",
                     fetched_at="2026-09-01T10:00:00+00:00",
                     public_facts_verified_at=fact_date, official_url="https://example.org/store")
        # Keep this eligible for automatic address matching after a premises review.
        if fact_date:
            store["location_type"] = "Shopping Centre"
        override = dict(location_setting="Shopping Centre", canonical_name="Example Centre",
                        place_type="Shopping Centre", official_url="https://example.org/centre",
                        source_date=centre_date, confidence="High", evidence_basis="Centre address")
        centre = places.create_place_from_override(store, override)
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            directory = Path(directory)
            (directory / "discovery").mkdir()
            centre_file = directory / "centres.json"
            centre_file.write_text(json.dumps({"centres": []}))
            stack.enter_context(patch.object(places, "DATA", directory))
            stack.enter_context(patch.object(places, "CENTRES_PATH", centre_file))
            for name in ("MEMBERSHIPS_PATH", "REMAPS_PATH", "EXCEPTIONS_PATH", "PLACES_PATH"):
                stack.enter_context(patch.object(places, name, directory / name))
            stack.enter_context(patch.object(places, "read_csv",
                side_effect=lambda path: [copy.deepcopy(store)] if path == places.STORES_PATH else []))
            stack.enter_context(patch.object(places, "add_broad_osm_centres", return_value=[]))
            stack.enter_context(patch.object(places, "add_official_retail_places",
                side_effect=lambda rows: rows.append(copy.deepcopy(centre))))
            for name in ("build_place_tenants", "build_development_signals", "build_lookalikes"):
                stack.enter_context(patch.object(places, name))
            with redirect_stdout(io.StringIO()):
                places.main()
            with places.MEMBERSHIPS_PATH.open() as handle:
                return list(csv.DictReader(handle))[0]

    def test_centre_refresh_cannot_refresh_an_unreviewed_tenant(self):
        before = self.build_address_membership("2026-09-01")
        after = self.build_address_membership("2026-10-04")
        self.assertEqual(before["review_status"], "Accepted")
        self.assertEqual(before["verified_at"], "2026-09-01")
        self.assertEqual(after, before)

    def test_retailer_premises_review_can_advance_its_own_mapping_date(self):
        row = self.build_address_membership("2026-10-04", "2026-10-02")
        self.assertEqual(row["review_status"], "Accepted")
        self.assertEqual(row["verified_at"], "2026-10-02")

    def test_incremental_row_keeps_its_date_and_legacy_rows_keep_snapshot_date(self):
        base = dict(name="Example optical", state="QLD", city="Brisbane",
                    full_address="1 Example Street, Brisbane QLD 4000",
                    latitude="-27.47", longitude="153.02", official_url="https://example.org/")
        rows = [dict(base, id="old"), dict(base, id="blank", fetched_at="  "),
                dict(base, id="new", fetched_at="2026-10-02T10:00:00+00:00")]
        source = network.ROOT / "retailers" / "optical-superstore" / "stores.csv"
        with patch.object(network, "read_csv", side_effect=lambda path: rows if path == source else []), \
             patch.object(network, "read_reviewed_rows", return_value=[]), \
             patch.object(network, "identity_remaps", return_value={}), \
             patch.object(network, "publication_exclusions", return_value={}):
            stores = network.load_stores({"Optical Superstore Australia": "2026-09-02T12:00:00+00:00"})
        self.assertEqual({r["store_id"]: r["fetched_at"] for r in stores}, {
            "optical-superstore-old": "2026-09-02T12:00:00+00:00",
            "optical-superstore-blank": "2026-09-02T12:00:00+00:00",
            "optical-superstore-new": "2026-10-02T10:00:00+00:00",
        })
        self.assertTrue(all(r["retailer"] == "Optical Superstore" for r in stores))


if __name__ == "__main__":
    unittest.main()
