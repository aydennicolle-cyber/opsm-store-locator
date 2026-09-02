#!/usr/bin/env python3
"""Refresh bounded official locators for additional Australian optical networks.

The saved snapshots deliberately omit email addresses, opening hours and other
unneeded contact data. They retain official source IDs so later refreshes do not
create false openings or closures.
"""

from __future__ import annotations

import csv
import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "OpticalLeasingIntelligence/1.0 (bounded public locator refresh)"
CSV_FIELDS = [
    "id", "name", "status", "country", "state", "city", "postal_code",
    "full_address", "phone", "latitude", "longitude", "official_url",
    "services", "audiology", "source_url",
]
GEORGE_MATILDA_COORDINATE_CORRECTIONS = {
    # The official locator currently places this ACT practice in Western
    # Australia. The replacement point is the mapped Tuggeranong Square address.
    "17216": {
        "latitude": -35.41995,
        "longitude": 149.070052,
        "evidence_url": "https://www.realcommercial.com.au/leased/property-tuggeranong-square-ground-level-310-anketell-street-tuggeranong-act-2900-5435150",
        "reason": "Official locator coordinate conflicts with the official ACT address; mapped property address used.",
    }
}


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def tidy(value: object) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def write_source(
    folder: str,
    source_url: str,
    records: list[dict],
    fetched_at: str,
    coordinate_corrections: list[dict] | None = None,
) -> None:
    target = ROOT / "retailers" / folder
    target.mkdir(parents=True, exist_ok=True)
    records.sort(key=lambda row: (row["state"], row["city"], row["name"], row["id"]))
    with (target / "stores.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in CSV_FIELDS} for row in records)
    snapshot = {
        "source_url": source_url,
        "fetched_at": fetched_at,
        "store_count": len(records),
        "scope": "Australia",
        "method": "Bounded official public store locator",
        "retained_fields": CSV_FIELDS,
        "excluded_fields": ["email", "opening_hours"],
        "source_ids": [row["id"] for row in records],
        "coordinate_corrections": coordinate_corrections or [],
    }
    (target / "source_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


class StoreDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.payload = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("data-stores") and not self.payload:
            self.payload = values["data-stores"] or ""


def george_and_matilda(fetched_at: str) -> tuple[str, list[dict]]:
    source_url = "https://georgeandmatilda.com.au/find-a-store/"
    parser = StoreDataParser()
    parser.feed(fetch_text(source_url))
    if not parser.payload:
        raise RuntimeError("George & Matilda locator did not expose data-stores")
    payload = json.loads(html.unescape(parser.payload))
    records = []
    for item in payload:
        address = tidy(item.get("address"))
        locality = ""
        parts = [part.strip() for part in address.split(",") if part.strip()]
        state = tidy(item.get("state")).upper()
        postcode = tidy(item.get("postcode"))
        if state in parts:
            state_index = parts.index(state)
            if state_index:
                locality = parts[state_index - 1]
        records.append({
            "id": tidy(item.get("id")),
            "name": tidy(item.get("title")),
            "status": "Active",
            "country": "Australia",
            "state": state,
            "city": locality,
            "postal_code": postcode,
            "full_address": address,
            "phone": tidy(item.get("phone")),
            "latitude": item.get("lat"),
            "longitude": item.get("lng"),
            "official_url": tidy(item.get("url")) or source_url,
            "services": "",
            "audiology": "false",
            "source_url": source_url,
        })
    corrections = []
    for record in records:
        correction = GEORGE_MATILDA_COORDINATE_CORRECTIONS.get(record["id"])
        if correction:
            record["latitude"] = correction["latitude"]
            record["longitude"] = correction["longitude"]
            corrections.append({"source_id": record["id"], **correction})
    return source_url, records, corrections


def wp_store_locator(source_url: str) -> list[dict]:
    base = urllib.parse.urlsplit(source_url)
    endpoint = f"{base.scheme}://{base.netloc}/wp-admin/admin-ajax.php"
    query = urllib.parse.urlencode({
        "action": "store_search",
        "lat": "-25.2744",
        "lng": "133.7751",
        "max_results": "500",
        "search_radius": "5000",
        "autoload": "1",
    })
    payload = json.loads(fetch_text(f"{endpoint}?{query}"))
    if isinstance(payload, dict):
        payload = payload.get("stores") or payload.get("results") or []
    records = []
    for item in payload:
        address_parts = [
            tidy(item.get("address")), tidy(item.get("address2")), tidy(item.get("city")),
            tidy(item.get("state")), tidy(item.get("zip")),
        ]
        full_address = ", ".join(part for part in address_parts if part)
        records.append({
            "id": tidy(item.get("id")) or slug(f"{item.get('store')} {full_address}"),
            "name": tidy(item.get("store")),
            "status": "Active",
            "country": "Australia",
            "state": tidy(item.get("state")).upper(),
            "city": tidy(item.get("city")),
            "postal_code": tidy(item.get("zip")),
            "full_address": full_address,
            "phone": tidy(item.get("phone")),
            "latitude": item.get("lat"),
            "longitude": item.get("lng"),
            "official_url": tidy(item.get("permalink")) or source_url,
            "services": "",
            "audiology": "false",
            "source_url": source_url,
        })
    return records


def validate(label: str, records: list[dict]) -> None:
    if not records:
        raise RuntimeError(f"{label}: official locator returned no records")
    ids = [row["id"] for row in records]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{label}: duplicate official source IDs")
    for row in records:
        if row["state"] not in {"ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"}:
            raise RuntimeError(f"{label}: invalid state for {row['id']}: {row['state']}")
        latitude, longitude = float(row["latitude"]), float(row["longitude"])
        if not (-44.5 <= latitude <= -9.0 and 112.0 <= longitude <= 154.5):
            raise RuntimeError(f"{label}: invalid coordinates for {row['id']}")
        if not row["name"] or not row["full_address"] or not row["postal_code"]:
            raise RuntimeError(f"{label}: incomplete record {row['id']}")


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat()
    gm_url, gm_records, gm_corrections = george_and_matilda(fetched_at)
    sources = [
        ("George & Matilda", "george-and-matilda", gm_url, gm_records, gm_corrections),
        (
            "Eyecare Plus", "eyecare-plus", "https://www.eyecareplus.com.au/find-optometrist/",
            wp_store_locator("https://www.eyecareplus.com.au/find-optometrist/"), [],
        ),
        (
            "Optical Superstore", "optical-superstore",
            "https://opticalsuperstore.com.au/find-your-nearest-store/",
            wp_store_locator("https://opticalsuperstore.com.au/find-your-nearest-store/"), [],
        ),
    ]
    for label, folder, source_url, records, coordinate_corrections in sources:
        validate(label, records)
        write_source(folder, source_url, records, fetched_at, coordinate_corrections)
        print(f"{label}: wrote {len(records)} official locations")


if __name__ == "__main__":
    main()
