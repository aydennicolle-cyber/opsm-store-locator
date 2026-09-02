#!/usr/bin/env python3
"""Account for every current and removed Independent/Other discovery record."""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
QUEUE = DATA / "discovery_candidates.csv"
CURRENT = ROOT / "retailers" / "independent-other" / "stores.csv"
PREVIOUS = DATA / "optical_stores.csv"
FIELDS = [
    "candidate_id", "entity_type", "proposed_name", "country", "state", "locality",
    "source_name", "source_url", "discovered_at", "review_status", "disposition",
    "canonical_id", "reviewed_at", "evidence_notes",
]
MAJOR = re.compile(r"\b(?:opsm|specsavers|bailey[\s&-]*(?:and[\s-]*)?nelson|oscar[\s-]*wylee)\b", re.I)
NON_COMPARABLE = re.compile(r"\b(?:sunglass(?:es)?\s+(?:hut|style|shack)|eyewear\s+glasses\s+repair|ophthalmolog|eye\s+surgery|laser\s+eye)\b", re.I)


def rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normal_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def nearby_duplicate(old: dict, current: list[dict]) -> dict | None:
    try:
        latitude, longitude = float(old["latitude"]), float(old["longitude"])
    except ValueError:
        return None
    return next(
        (
            item for item in current
            if normal_name(item["name"]) == normal_name(old["name"])
            and abs(float(item["latitude"]) - latitude) <= 0.00045
            and abs(float(item["longitude"]) - longitude) <= 0.00055
        ),
        None,
    )


def main() -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    queue = {row["candidate_id"]: row for row in rows(QUEUE)}
    current = rows(CURRENT)
    previous = [row for row in rows(PREVIOUS) if row["retailer"] == "Independent / Other optical"]
    current_ids = {row["id"] for row in current}

    for item in current:
        candidate_id = f"independent-{item['id']}"
        queue.setdefault(candidate_id, {
            "candidate_id": candidate_id,
            "entity_type": "store",
            "proposed_name": item["name"],
            "country": item["country"],
            "state": item["state"],
            "locality": item["city"],
            "source_name": "OpenStreetMap shop=optician discovery",
            "source_url": item["source_url"],
            "discovered_at": now,
            "review_status": "Pending",
            "disposition": "",
            "canonical_id": "",
            "reviewed_at": "",
            "evidence_notes": "Comparable storefront, active status, address and physical format require source-backed review",
        })

    for item in previous:
        local_id = item["store_id"].removeprefix("independent-other-optical-")
        if local_id in current_ids:
            continue
        candidate_id = f"historical-{local_id}"
        disposition = ""
        canonical_id = ""
        notes = "No longer returned by the latest OSM query; investigate possible deletion, closure, remap or missed store"
        duplicate = nearby_duplicate(item, current)
        if MAJOR.search(item["name"]):
            disposition, notes = "Duplicate of named network", "Excluded from Independent/Other after normalized major-brand matching"
        elif NON_COMPARABLE.search(item["name"]):
            disposition, notes = "Non-comparable business", "Excluded by explicit non-comparable retail rule"
        elif duplicate:
            disposition = "Duplicate of canonical store"
            canonical_id = f"independent-other-optical-{duplicate['id']}"
            notes = "Duplicate OSM geometry within the same physical storefront"
        resolved = bool(disposition)
        queue[candidate_id] = {
            "candidate_id": candidate_id,
            "entity_type": "store",
            "proposed_name": item["name"],
            "country": item["country"],
            "state": item["state"],
            "locality": item["suburb"],
            "source_name": "Historical OpenStreetMap shop=optician snapshot",
            "source_url": item["source_url"],
            "discovered_at": now,
            "review_status": "Resolved" if resolved else "Pending",
            "disposition": disposition,
            "canonical_id": canonical_id,
            "reviewed_at": now if resolved else "",
            "evidence_notes": notes,
        }

    with QUEUE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(queue.values(), key=lambda row: row["candidate_id"]))
    pending = sum(row["review_status"] == "Pending" for row in queue.values())
    print(f"Discovery queue contains {len(queue)} candidates; {pending} pending review")


if __name__ == "__main__":
    main()
