"""Synthetic-only adversarial tests across admission, generated output and packaging."""
import copy
import json
from pathlib import Path
import re
import tempfile
import unittest

from scripts import public_directory_evidence as evidence
from scripts import public_directory_schema as schema
from scripts import package_public_site as packaging
from scripts import scan_public_privacy as privacy
from scripts.retail_directory_overlay import apply_captures

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    row = dict(source_id="publisher:001", name="Synthetic shop",
               source_url="https://example.org/directory", observed_at="2020-02-29",
               scope_basis="Synthetic official directory", scope_status="included",
               listing_status="listed", categories=["Services"], source_date="2019-11")
    capture = dict(place_id="synthetic", records=[row], source_urls=["https://example.org/directory"],
                   source_total=1, directory_complete=True, format_scope="canonical centre",
                   scope="Synthetic property", capture_method="All source records",
                   limitations="Synthetic only", absence_reviews=[])
    payload = dict(schema_version=1, places=[], captures=[capture])
    base = dict(features=[], places=[dict(place_id="synthetic", name="Synthetic",
                                        format="Shopping Centre", features={})])
    return payload, capture, row, base


class DirectoryBoundaryTests(unittest.TestCase):
    def assert_rejected(self, payload, base):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            (data / evidence.FILE).write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                evidence.load(data)
        with self.assertRaises(ValueError):
            apply_captures(base, payload["captures"])
        with self.assertRaises(ValueError):
            privacy.walk(payload, Path("synthetic-capture.json"))

    def test_reported_exploit_and_each_independent_failure(self):
        invalid = dict(commercial_memo="SYNTHETIC CONFIDENTIAL",
                       source_id="private-research-123", observed_at="not-a-date",
                       source_url="https://192.168.1.5/internal")
        for changes in [invalid, *[{k: v} for k, v in invalid.items()]]:
            with self.subTest(changes=changes):
                payload, _, row, base = fixture()
                row.update(changes)
                self.assert_rejected(payload, base)

    def test_closed_nested_objects_even_in_held_records_and_history(self):
        for branch in ("record", "native_source_id", "source_native_ids", "history",
                       "previous_record", "category_sources", "absence_reviews",
                       "anonymous_counts", "additional_samples", "hours"):
            with self.subTest(branch=branch):
                payload, capture, row, base = fixture()
                row["scope_status"] = "held"
                extra = {"unexpected_export_field": "SYNTHETIC ONLY"}
                if branch == "record":
                    row.update(extra)
                elif branch in {"source_native_ids", "native_source_id"}:
                    row[branch] = extra
                elif branch in {"history", "previous_record"}:
                    entry = dict(observed_at="2019-01-01", basis="Synthetic history")
                    entry.update(extra if branch == "history" else {"previous_record": extra})
                    row["verification_history"] = [entry]
                elif branch == "category_sources":
                    row[branch] = [{"url": "https://example.org/category", **extra}]
                elif branch == "absence_reviews":
                    capture[branch] = [{**review(), **extra}]
                elif branch == "anonymous_counts":
                    capture[branch] = extra
                else:
                    capture["anonymous_counts"] = {branch: [extra] if branch == "additional_samples" else extra}
                self.assert_rejected(payload, base)

    def test_root_place_and_identity_source_are_closed(self):
        for branch in ("root", "place", "source"):
            payload, _, _, _ = fixture()
            place = identity()
            payload["places"] = [place]
            target = payload if branch == "root" else place if branch == "place" else place["sources"][0]
            target["unexpected_export_field"] = "SYNTHETIC ONLY"
            with self.assertRaises(ValueError):
                schema.document(payload)

    def test_urls_reject_non_public_addresses_and_ambiguous_hosts(self):
        hosts = ["192.168.1.5", "10.0.0.1", "172.16.0.1", "169.254.169.254",
                 "127.0.0.2", "0.0.0.0", "100.64.0.1", "[::1]", "[fc00::1]",
                 "[fe80::1]", "[::ffff:192.168.1.5]", "localhost", "LOCALHOST.",
                 "service.localhost", "server.internal", "server.local", "server",
                 "2130706433", "0177.0.0.1", "0x7f000001", "127.1"]
        urls = [f"https://{host}/directory" for host in hosts]
        urls += ["http://example.org/directory", "https://user:secret@example.org/",
                 "https://example.org:8443/", "https://example.org\\@192.168.1.5/",
                 "https://example.org/\ninternal"]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                schema.source_url(url)
        for url in ["https://example.org/Home/Public", "https://example.org:443/directory",
                    "https://8.8.8.8/directory", "https://[2606:4700:4700::1111]/directory"]:
            self.assertEqual(schema.source_url(url), url)

    def test_invalid_dates_counts_types_and_nested_urls_fail(self):
        for changes in [
            {"observed_at": "2026-02-30"}, {"observed_at": 20261020},
            {"source_date": "2025-13"}, {"source_checked_at": "unknown"},
            {"verification_history": [{"observed_at": "not-a-date"}]},
            {"category_sources": [{"url": "https://10.0.0.1/source"}]},
            {"additional_source_urls": ["https://[::1]/source"]},
            {"categories": [{"commercial_memo": "SYNTHETIC ONLY"}]},
            {"source_ids": ["private-research-123"]},
        ]:
            payload, _, row, base = fixture()
            row.update(changes)
            self.assert_rejected(payload, base)
        for changes in [{"directory_complete": "false"}, {"source_total": True},
                        {"source_record_count": -1}, {"anonymous_record_count": True},
                        {"records": {}}, {"source_urls": []}]:
            payload, capture, _, base = fixture()
            capture.update(changes)
            self.assert_rejected(payload, base)

    def test_public_native_identifiers_historical_dates_and_projection_are_lossless(self):
        payload, capture, row, base = fixture()
        row.update(native_source_id={"page_id": "00123", "toggle_id": "0"},
                   raw_source_id=123, source_native_ids={"table_id": "001", "row_id": None,
                                                        "map_shape_ids": ["a", 3]},
                   source_updated_at=1751146720664, frontage_imagery_date="2018-10",
                   previous_source_ids=["publisher:old"], source_categories=[""],
                   verification_history=[dict(observed_at="2019-01-01", previous_record={
                       "source_id": "publisher:old", "source_url": "https://example.org/old"})])
        original = copy.deepcopy(payload)
        self.assertEqual(schema.document(payload), payload)
        result = apply_captures(base, [capture])["places"][0]
        self.assertEqual(result["directory_records"][0], row)
        self.assertEqual({k: v for k, v in result["observations"][0].items() if k != "features"}, row)
        result["directory_records"][0]["source_native_ids"]["map_shape_ids"].append("new")
        self.assertEqual(payload, original, "generated fields must not alias input objects")

    def test_review_does_not_become_publication_date_and_all_identity_sources_survive(self):
        payload, _, _, _ = fixture()
        place = identity()
        payload["places"] = [place]
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            (data / evidence.FILE).write_text(json.dumps(payload))
            places = []
            evidence.add_places(places, data)
            self.assertEqual(places[0]["sources"], place["sources"])
            self.assertEqual(places[0]["reviewed_at"], "2026-10-20")
            self.assertEqual(places[0]["coordinate_source_url"], place["coordinate_source_url"])
            self.assertIsNone(places[0]["source_date"])
            place["sources"][0]["source_date"] = "2018-10"
            (data / evidence.FILE).write_text(json.dumps(payload))
            places = []
            evidence.add_places(places, data)
            self.assertEqual(places[0]["source_date"], "2018-10")
            self.assertEqual(places[0]["sources"][0]["observed_at"], "2020-02-29")

    def test_canonical_type_controls_absence_and_missing_names_stay_unknown(self):
        _, capture, _, base = fixture()
        for actual_format in ("High Street", "Retail Precinct", None):
            base["places"][0]["format"] = actual_format
            result = apply_captures(base, [capture])["places"][0] if actual_format else None
            if result:
                self.assertFalse(result["coverage"]["absence_eligible"])
                self.assertFalse(result["absent_features"])
            capture["absence_reviews"] = [review()]
            with self.assertRaises(ValueError):
                apply_captures(base, [capture])
            capture["absence_reviews"] = []
        base["places"][0]["format"] = "Shopping Centre"
        base["places"][0]["place_type"] = "High Street Corridor"
        capture["absence_reviews"] = [review()]
        with self.assertRaises(ValueError):
            apply_captures(base, [capture])
        base["places"][0]["place_type"] = "Shopping Centre"
        capture["absence_reviews"] = []
        for complete in (True, False):
            capture["directory_complete"] = complete
            result = apply_captures(base, [capture])["places"][0]
            self.assertFalse(result["absent_features"])
        capture["absence_reviews"] = [review()]
        with self.assertRaises(ValueError):
            apply_captures(base, [capture])

    def test_generated_hidden_branches_are_scanned(self):
        _, capture, _, base = fixture()
        for changes in [
            {"commercial_memo": "SYNTHETIC CONFIDENTIAL"},
            {"unexpected_export_field": "SYNTHETIC ONLY"},
            {"source_id": "private-research-123"},
            {"observed_at": "not-a-date"},
            {"source_url": "https://192.168.1.5/internal"},
        ]:
            for branch in ("directory_records", "observations"):
                output = apply_captures(base, [capture])
                output["places"][0][branch][0].update(changes)
                with self.assertRaises(ValueError):
                    privacy.walk(output, Path("synthetic-generated.json"))


def review():
    return dict(feature_id="brand:missing", label="Missing", kind="Retailer", basis="Synthetic full review",
                source_url="https://example.org/directory", observed_at="2020-02-29")


def identity():
    return dict(place_id="identity", name="Synthetic market", country="Australia", state="ACT",
                locality="Kingston", format="Shopping Centre", address="Synthetic public address",
                sources=[dict(url="https://example.org/identity", observed_at="2020-02-29"),
                         dict(url="https://example.org/history", observed_at="2019-01-01")],
                reviewed_at="2026-10-20", scope="Named property only", latitude=-35.3, longitude=149.1,
                coordinate_source_url="https://www.openstreetmap.org/way/123")


class PublicPackagingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "source"
        self.output = Path(temporary.name) / "site"
        for name in packaging.approved_files():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            content = "{}" if path.suffix in {".json", ".geojson"} else "name\nSynthetic\n" if path.suffix == ".csv" else ""
            path.write_text(content)
        payload, _, _, _ = fixture()
        (self.root / "data" / evidence.FILE).write_text(json.dumps(payload))
        (self.root / "data/location_news.json").write_text(json.dumps({
            "schema_version": 1, "document_type": "location_news", "events": [], "checks": []
        }))

    def test_news_cannot_bypass_schema_by_removing_its_marker(self):
        (self.root / "data/location_news.json").write_text('{"events":[],"unexpected_notes":"synthetic"}')
        with self.assertRaises(ValueError):
            packaging.package(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_only_manifest_files_are_packaged_and_output_is_scanned(self):
        extra = self.root / "data/unapproved-research.txt"
        extra.write_text("Synthetic unapproved source")
        packaging.package(self.root, self.output)
        self.assertFalse((self.output / extra.relative_to(self.root)).exists())
        packaging.validate_bundle(self.output)
        self.assertTrue((self.output / "data" / evidence.FILE).exists())
        with self.assertRaises(FileExistsError):
            packaging.package(self.root, self.output)
        (self.output / "data/unexpected.txt").write_text("Synthetic extra")
        with self.assertRaises(ValueError):
            packaging.validate_bundle(self.output)

    def test_hidden_source_capture_blocks_packaging(self):
        payload, _, row, _ = fixture()
        row["scope_status"] = "held"
        row["commercial_memo"] = "SYNTHETIC CONFIDENTIAL"
        (self.root / "data" / evidence.FILE).write_text(json.dumps(payload))
        with self.assertRaises(ValueError):
            packaging.package(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_capture_cannot_bypass_scan_by_removing_schema_markers(self):
        (self.root / "data" / evidence.FILE).write_text("{}")
        with self.assertRaises(ValueError):
            packaging.package(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_duplicate_json_key_cannot_hide_an_unapproved_raw_record(self):
        path = self.root / "data" / evidence.FILE
        payload, _, _, _ = fixture()
        raw = json.dumps(payload)
        raw = raw.replace('"captures":', '"captures":[{"commercial_memo":"SYNTHETIC CONFIDENTIAL"}],"captures":', 1)
        path.write_text(raw)
        with self.assertRaises(ValueError):
            evidence.load(path.parent)
        with self.assertRaises(ValueError):
            packaging.package(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_scan_all_structured_and_text_outputs_including_geojson_and_csv_values(self):
        packaging.package(self.root, self.output)
        for filename, content in [
            ("data/optical_stores.geojson", '{"nested":{"commercial_memo":"SYNTHETIC CONFIDENTIAL"}}'),
            ("opsm_stores.csv", 'source_id\nprivate-research-123\n'),
            ("data/destination_profiles.html", '<p>{"commercial_memo":"SYNTHETIC CONFIDENTIAL"}</p>'),
        ]:
            path = self.output / filename
            original = path.read_text()
            with self.subTest(filename=filename):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    privacy.scan_structured(self.output, packaged=True)
                path.write_text(original)

    def test_symlinks_never_enter_bundle(self):
        path = self.root / "data" / evidence.FILE
        target = self.root / "synthetic-outside.json"
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaises(ValueError):
            packaging.package(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_runtime_data_and_logos_are_in_explicit_manifest(self):
        files = packaging.approved_files()
        app = (ROOT / "assets/app.js").read_text()
        references = set(re.findall(r"""['"](data/[a-z0-9_]+\.(?:json|geojson|csv|html))""", app))
        registry = json.loads((ROOT / "data/retailer_registry.json").read_text())
        def logos(value):
            if isinstance(value, dict):
                if isinstance(value.get("logo"), str) and value["logo"].startswith("assets/"):
                    references.add(value["logo"])
                for child in value.values():
                    logos(child)
            elif isinstance(value, list):
                for child in value:
                    logos(child)
        logos(registry)
        self.assertFalse(references - files)
        workflow = (ROOT / ".github/workflows/pages.yml").read_text()
        self.assertNotIn("cp -R assets data retailers", workflow)
        self.assertLess(workflow.index("scan_public_privacy.py --site"), workflow.index("actions/upload-pages-artifact"))


if __name__ == "__main__":
    unittest.main()
