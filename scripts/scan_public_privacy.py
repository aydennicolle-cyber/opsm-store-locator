#!/usr/bin/env python3
"""Fail when private leasing fields appear in public artifacts or browser requests."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


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
}
PUBLIC_JSON = list((ROOT / "data").rglob("*.json")) + [ROOT / "opsm_stores.geojson"]
PUBLIC_CSV = list((ROOT / "data").rglob("*.csv")) + [ROOT / "opsm_stores.csv"]
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
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def scan_structured() -> None:
    for path in PUBLIC_JSON:
        if path.exists():
            walk(json.loads(path.read_text(encoding="utf-8")), path)
    for path in PUBLIC_CSV:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
        private = PRIVATE_FIELDS.intersection(value.strip().lower() for value in header)
        if private:
            raise ValueError(f"Private CSV fields in {path}: {sorted(private)}")


def scan_browser_requests() -> None:
    source = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
    urls = set(re.findall(r"fetch\(\s*[`\"'](https://[^`\"'${]+)", source))
    unexpected = urls - ALLOWED_REMOTE_REQUESTS
    if unexpected:
        raise ValueError(f"Unexpected remote browser requests: {sorted(unexpected)}")
    for term in PRIVATE_FIELDS:
        if re.search(rf"[?&]{re.escape(term)}=", source, flags=re.IGNORECASE):
            raise ValueError(f"Private field may enter a share URL or request: {term}")


def main() -> None:
    scan_structured()
    scan_browser_requests()
    print(f"Privacy scan passed: {len(PUBLIC_JSON)} JSON/GeoJSON and {len(PUBLIC_CSV)} CSV artifacts checked")


if __name__ == "__main__":
    main()
