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
CANONICAL_MEMBERSHIP_PATH = DATA_DIR / "store_place_memberships.csv"
PLACE_REMAP_PATH = DATA_DIR / "place_id_remaps.csv"
STORE_PLACE_OVERRIDE_PATH = DATA_DIR / "store_place_overrides.csv"
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
    "optical",
    "optometry",
    "optometrist",
    "optometrists",
    "eyecare",
    "eye",
    "care",
    "vision",
    "hearing",
    "health",
    "medical",
    "clinic",
    "spectacles",
    "eyewear",
    "street",
    "road",
    "avenue",
    "drive",
    "boulevard",
    "highway",
    "lane",
    "parade",
}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_place_remaps() -> dict[str, str]:
    """Load legacy/source place IDs and resolve every entry to its final ID."""

    direct = {}
    for row in read_csv(PLACE_REMAP_PATH):
        previous = row.get("previous_place_id", "").strip()
        canonical = row.get("canonical_place_id", "").strip()
        # Generated remap files intentionally include canonical self-entries so
        # callers can perform one-step lookups.  They are terminal identities,
        # not graph edges.
        if previous and canonical and previous != canonical:
            direct[previous] = canonical

    def resolve(place_id: str) -> str:
        visited = set()
        while place_id in direct:
            if place_id in visited:
                raise ValueError(f"Place-ID remap cycle detected at {place_id}")
            visited.add(place_id)
            place_id = direct[place_id]
        return place_id

    return {place_id: resolve(place_id) for place_id in direct}


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


def contextual_name_tokens(store: dict, centre: dict) -> set[str]:
    """Return locality/region tokens that cannot prove a tenancy relationship.

    A store and a nearby centre will commonly share the suburb name (for example,
    ``OPSM Hobart`` near a Hobart retail place).  Those tokens are useful for
    discovery but are not evidence that the store is inside that place.
    """

    values = (
        store.get("suburb", ""),
        store.get("state", ""),
        store.get("country", ""),
        centre.get("suburb", ""),
        centre.get("state", ""),
        centre.get("country", ""),
    )
    return {
        token
        for value in values
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2
    }


def explicit_place_name_overlap(store: dict, centre: dict) -> bool:
    """Identify a distinctive venue name stated by the official store record."""

    context = contextual_name_tokens(store, centre)
    store_tokens = name_tokens(store["name"]) - context
    centre_tokens = name_tokens(centre["venue_name"]) - context
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
    canonical_memberships = {
        row["store_id"]: row
        for row in read_csv(CANONICAL_MEMBERSHIP_PATH)
        if row.get("review_status") == "Accepted" and row.get("place_id", "").strip()
    }
    reviewed_noncentre_store_ids = {
        row["store_id"].strip()
        for row in read_csv(STORE_PLACE_OVERRIDE_PATH)
        if row.get("store_id", "").strip()
        and row.get("location_setting", "").strip() in {"High Street", "Other"}
    }
    place_remaps = load_place_remaps()
    centres = build_known_centres(stores, registry)
    rows = []

    for store in stores:
        if store["store_id"] in reviewed_noncentre_store_ids:
            continue
        accepted_membership = canonical_memberships.get(store["store_id"])
        accepted_place_id = (
            accepted_membership.get("place_id", "").strip()
            if accepted_membership
            else ""
        )
        candidates = []
        for centre in centres:
            if store["state"] != centre["state"] or store["postcode"] != centre["postcode"]:
                continue
            if store["venue_id"] == centre["venue_id"]:
                continue
            # Source systems regularly use different venue IDs for the same
            # property.  Once both IDs resolve to the same canonical place this
            # is not a duplicate-classification exception and must not return to
            # the consultant review queue.
            current_place_id = accepted_place_id or place_remaps.get(
                store["venue_id"], store["venue_id"]
            )
            candidate_place_id = place_remaps.get(
                centre["venue_id"], centre["venue_id"]
            )
            if current_place_id and current_place_id == candidate_place_id:
                continue
            distance = haversine_metres(store, centre)
            official_address_match = bool(
                centre.get("street_address")
                and normalise_address(centre["street_address"]) in normalise_address(store["full_address"])
            )
            overlapping_name = explicit_place_name_overlap(store, centre)
            if official_address_match:
                priority = "High"
                evidence = "Store address matches a verified official centre address"
            elif distance <= 125 and overlapping_name:
                priority = "High"
                evidence = (
                    "Official store name explicitly matches a distinctive canonical place name; "
                    "coordinates corroborate the identity"
                )
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
                        if accepted_place_id
                        and accepted_membership.get("location_setting") == "Shopping Centre"
                        and priority == "High"
                        else (
                            "Adjacent centre check"
                            if accepted_place_id
                            and accepted_membership.get("location_setting") == "Shopping Centre"
                            else "Possible missed centre"
                        )
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
        elif (
            store["location_type"] == "Shopping Centre"
            and not store["venue_id"]
            and not accepted_membership
        ):
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
        for reason in (
            "Possible missed centre",
            "Missing venue name",
            "Possible duplicate centre ID",
            "Adjacent centre check",
        )
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
