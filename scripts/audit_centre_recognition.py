#!/usr/bin/env python3
"""Create a conservative review queue for stores that may be in shopping centres."""

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
STORE_PATH = DATA_DIR / "optical_stores.csv"
CENTRE_PATH = DATA_DIR / "shopping_centres.csv"
MEMBERSHIP_PATH = DATA_DIR / "centre_store_memberships.csv"
OUTPUT_PATH = DATA_DIR / "centre_recognition_review.csv"
OUTPUT_FIELDS = [
    "priority",
    "review_reason",
    "store_id",
    "retailer",
    "name",
    "current_location_type",
    "current_venue_id",
    "full_address",
    "candidate_venue_id",
    "candidate_venue_name",
    "evidence",
    "distance_m",
    "automatic_action",
    "review_status",
]
IGNORED_NAME_TOKENS = {
    "opsm",
    "specsavers",
    "bailey",
    "nelson",
    "shopping",
    "centre",
    "center",
    "mall",
    "plaza",
    "square",
    "marketplace",
    "westfield",
    "stockland",
    "the",
    "s",
    "c",
}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def haversine_metres(first: dict, second: dict) -> float:
    lat1, lon1, lat2, lon2 = map(
        math.radians,
        (
            float(first["latitude"]),
            float(first["longitude"]),
            float(second["latitude"]),
            float(second["longitude"]),
        ),
    )
    value = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371000 * 2 * math.asin(math.sqrt(value))


def normalise_address(value: str) -> str:
    value = value.lower()
    replacements = {
        "highway": "hwy",
        "street": "st",
        "road": "rd",
        "avenue": "ave",
        "drive": "dr",
        "boulevard": "blvd",
    }
    for source, target in replacements.items():
        value = re.sub(rf"\b{source}\b", target, value)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def name_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in IGNORED_NAME_TOKENS
    }


def name_overlap(store: dict, centre: dict) -> bool:
    store_tokens = name_tokens(store["name"])
    centre_tokens = name_tokens(centre["venue_name"])
    return bool(store_tokens & centre_tokens)


def build_known_centres(stores: list[dict], registry: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for store in stores:
        if store["venue_id"]:
            grouped[store["venue_id"]].append(store)

    known = {}
    for centre in registry:
        known[centre["venue_id"]] = {
            **centre,
            "latitude": float(centre["latitude"]),
            "longitude": float(centre["longitude"]),
        }
    for venue_id, members in grouped.items():
        known.setdefault(
            venue_id,
            {
                "venue_id": venue_id,
                "venue_name": members[0]["venue_name"],
                "state": members[0]["state"],
                "suburb": members[0]["suburb"],
                "postcode": members[0]["postcode"],
                "street_address": "",
                "latitude": sum(float(item["latitude"]) for item in members) / len(members),
                "longitude": sum(float(item["longitude"]) for item in members) / len(members),
            },
        )
    return list(known.values())


def main() -> None:
    stores = read_csv(STORE_PATH)
    registry = read_csv(CENTRE_PATH)
    memberships = {
        (row["retailer"], row["store_id"], row["venue_id"])
        for row in read_csv(MEMBERSHIP_PATH)
    }
    centres = build_known_centres(stores, registry)
    rows = []

    for store in stores:
        candidates = []
        for centre in centres:
            if store["state"] != centre["state"] or store["postcode"] != centre["postcode"]:
                continue
            if store["venue_id"] == centre["venue_id"]:
                continue
            distance = haversine_metres(store, centre)
            official_address_match = bool(
                centre.get("street_address")
                and normalise_address(centre["street_address"]) in normalise_address(store["full_address"])
            )
            overlapping_name = name_overlap(store, centre)
            if official_address_match:
                priority = "High"
                evidence = "Store address matches a verified official centre address"
            elif distance <= 125 and overlapping_name:
                priority = "High"
                evidence = "Store and centre names overlap and coordinates are within 125 m"
            elif distance <= 50:
                priority = "Medium"
                evidence = "Coordinates are within 50 m of a named centre; tenancy must be confirmed"
            elif distance <= 125:
                priority = "Low"
                evidence = "Coordinates are within 125 m of a named centre; proximity is not proof"
            else:
                continue
            candidates.append((priority, distance, centre, evidence))

        if candidates:
            order = {"High": 0, "Medium": 1, "Low": 2}
            priority, distance, centre, evidence = min(
                candidates, key=lambda item: (order[item[0]], item[1])
            )
            rows.append(
                {
                    "priority": priority,
                    "review_reason": (
                        "Possible duplicate centre ID"
                        if store["location_type"] == "Shopping Centre" and store["venue_id"]
                        else "Possible missed centre"
                    ),
                    "store_id": store["store_id"],
                    "retailer": store["retailer"],
                    "name": store["name"],
                    "current_location_type": store["location_type"],
                    "current_venue_id": store["venue_id"],
                    "full_address": store["full_address"],
                    "candidate_venue_id": centre["venue_id"],
                    "candidate_venue_name": centre["venue_name"],
                    "evidence": evidence,
                    "distance_m": f"{distance:.1f}",
                    "automatic_action": "None - human review required",
                    "review_status": "Pending",
                }
            )
        elif store["location_type"] == "Shopping Centre" and not store["venue_id"]:
            rows.append(
                {
                    "priority": "High",
                    "review_reason": "Missing venue name",
                    "store_id": store["store_id"],
                    "retailer": store["retailer"],
                    "name": store["name"],
                    "current_location_type": store["location_type"],
                    "current_venue_id": "",
                    "full_address": store["full_address"],
                    "candidate_venue_id": "",
                    "candidate_venue_name": "",
                    "evidence": "Official store data indicates a shopping centre but no venue was extracted",
                    "distance_m": "",
                    "automatic_action": "None - human review required",
                    "review_status": "Pending",
                }
            )

    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    rows.sort(
        key=lambda row: (
            priority_order[row["priority"]],
            float(row["distance_m"]) if row["distance_m"] else 999999,
            row["store_id"],
        )
    )
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    counts = {priority: sum(row["priority"] == priority for row in rows) for priority in priority_order}
    reasons = {
        reason: sum(row["review_reason"] == reason for row in rows)
        for reason in ("Possible missed centre", "Missing venue name", "Possible duplicate centre ID")
    }
    reviewed = sum(
        (row["retailer"], row["store_id"], row["venue_id"]) in memberships
        for row in read_csv(MEMBERSHIP_PATH)
    )
    print(f"Wrote {len(rows)} centre-recognition candidates to {OUTPUT_PATH}")
    print(f"Priorities: {counts}")
    print(f"Review reasons: {reasons}")
    print(f"Source-backed centre memberships: {reviewed}")


if __name__ == "__main__":
    main()
