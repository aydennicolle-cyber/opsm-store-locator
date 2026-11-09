#!/usr/bin/env python3
"""Fail when private leasing fields appear in public artifacts or browser requests."""

from __future__ import annotations

import csv
import re
import argparse
from pathlib import Path
try:
    from . import public_directory_schema as directory_schema
except ImportError:
    import public_directory_schema as directory_schema


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_FIELDS = {
    "asking_rent",
    "base_rent",
    "outgoings",
    "incentive",
    "lease_expiry",
    "option_notice_date",
    "negotiation_notes",
    "sales_performance",
    "turnover",
    "private_contact",
    "inspection_notes",
    "gross_margin",
    "occupancy_cost",
    "lease_terms",
    "private_email",
    "private_phone",
    "committed_fy31",
    "bn_row",
    "supplier_status",
    "revenue_group",
    "revenue_rank",
    "cohort_membership",
    "higher_revenue_group",
    "lower_revenue_group",
    "prior_source_store_code",
    "full_period_trading",
    "commercial_memo",
    "bn_sources",
    "current_bn_stores",
    "source_capture_file",
    "research_tier",
    "commercial_priority",
    "target_ids",
}
ALLOWED_REMOTE_REQUESTS = {
    "https://overpass-api.de/api/interpreter",
}


def walk(value: object, path: Path) -> None:
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            private = PRIVATE_FIELDS.intersection(key.lower() for key in current)
            if private:
                raise ValueError(f"Private fields in {path}: {sorted(private)}")
            if current.get("document_type") == "location_news":
                try:
                    from .location_news_schema import document as news_document
                except ImportError:
                    from location_news_schema import document as news_document
                news_document(current)
            if "schema_version" in current and "captures" in current and "places" in current:
                directory_schema.document(current)
                continue
            elif "records" in current and "format_scope" in current:
                directory_schema.capture(current)
                continue
            elif current.get("public_directory_evidence") or ("directory_records" in current and "coverage" in current):
                directory_schema.validate_generated_place(current)
            elif {"source_id", "store_id", "observed_at"} <= current.keys() and current.get("identity_review"):
                directory_schema.identity_review(current["identity_review"])
            elif {"source_id", "scope_status", "categories", "listing_status"} <= current.keys():
                validator = directory_schema.generated_observation if "features" in current else directory_schema.generated_record
                validator(current)
            if "identity_sources" in current:
                directory_schema.array(directory_schema.identity_source)(current["identity_sources"])
                if current.get("identity_reviewed_at") is not None:
                    directory_schema.iso_date(current["identity_reviewed_at"])
            if "sources" in current and "reviewed_at" in current and "coordinate_source_url" in current:
                directory_schema.array(directory_schema.identity_source)(current["sources"])
                directory_schema.iso_date(current["reviewed_at"])
            if "coordinate_source_url" in current and current["coordinate_source_url"]:
                directory_schema.source_url(current["coordinate_source_url"])
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
        elif isinstance(current, str):
            directory_schema.public_text(current)


def artifact_paths(root=ROOT, packaged=False):
    """Discover at scan time; include source captures, all GeoJSON and retailers."""
    if packaged:
        return sorted(p for p in root.rglob("*") if p.is_file())
    return sorted({
        *[p for folder in ("data", "retailers", "assets") for p in (root / folder).rglob("*") if p.is_file()],
        *[root / name for name in ("index.html", "opsm_stores.csv", "opsm_stores.geojson") if (root / name).exists()],
    })


def scan_structured(root=ROOT, packaged=False) -> tuple[int, int]:
    json_count = csv_count = 0
    for path in artifact_paths(root, packaged):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Symlink or external file in public artifacts: {path}")
        if path.suffix in {".json", ".geojson"}:
            try:
                value = directory_schema.decode_json(path.read_text(encoding="utf-8"))
                if path.name == "public_directory_captures.json":
                    directory_schema.document(value)
                elif path.name in {"location_news.json", "location_news_records.json"}:
                    try:
                        from .location_news_schema import document as news_document
                    except ImportError:
                        from location_news_schema import document as news_document
                    news_document(value)
                    walk(value, path)
                else:
                    walk(value, path)
            except ValueError as error:
                raise ValueError(f"{path}: {error}") from error
            json_count += 1
        elif path.suffix == ".csv":
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                private = PRIVATE_FIELDS.intersection(value.strip().lower() for value in (reader.fieldnames or []))
                if private:
                    raise ValueError(f"Private CSV fields in {path}: {sorted(private)}")
                for row in reader:
                    walk(row, path)
            csv_count += 1
        elif path.suffix in {".html", ".txt", ".md", ".js", ".css", ".svg"}:
            source = path.read_text(encoding="utf-8")
            directory_schema.public_text(source)
            # Catch serialized fields in reports and scripts as well as JSON.
            for field in PRIVATE_FIELDS:
                if re.search(rf'''["']{re.escape(field)}["']\s*:''', source, re.I):
                    raise ValueError(f"Private serialized field in {path}: {field}")
    return json_count, csv_count


def scan_browser_requests(root=ROOT) -> None:
    source = "\n".join(p.read_text(encoding="utf-8") for p in artifact_paths(root)
                       if p.suffix in {".js", ".html"})
    if re.search(r"(?:higher|lower)-revenue group", source, re.I):
        raise ValueError("Commercial cohort labels must stay in the private workspace")
    urls = set(re.findall(r"fetch\(\s*[`\"'](https://[^`\"'${]+)", source))
    unexpected = urls - ALLOWED_REMOTE_REQUESTS
    if unexpected:
        raise ValueError(f"Unexpected remote browser requests: {sorted(unexpected)}")
    if re.search(r"fetch\(\s*[`\"']/__local__/", source):
        raise ValueError("Private local review endpoints must not be loaded by the public browser")
    for term in PRIVATE_FIELDS:
        if re.search(rf"[?&]{re.escape(term)}=", source, flags=re.IGNORECASE):
            raise ValueError(f"Private field may enter a share URL or request: {term}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, help="Scan the exact prepared website and enforce its file manifest")
    args = parser.parse_args()
    root = args.site if args.site else ROOT
    if args.site:
        try:
            from .package_public_site import validate_bundle
        except ImportError:
            from package_public_site import validate_bundle
        validate_bundle(root)
    json_count, csv_count = scan_structured(root, packaged=bool(args.site))
    scan_browser_requests(root)
    print(f"Privacy scan passed: {json_count} JSON/GeoJSON and {csv_count} CSV artifacts plus public text/browser files checked")


if __name__ == "__main__":
    main()
