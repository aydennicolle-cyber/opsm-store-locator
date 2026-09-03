#!/usr/bin/env python3
"""Find plausible duplicate optical-store identities without merging by proximity."""

from __future__ import annotations

import csv
import math
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORES_PATH = ROOT / "data" / "optical_stores.csv"
OUTPUT_PATH = ROOT / "data" / "store_identity_review.csv"
DECISIONS_PATH = ROOT / "data" / "store_identity_decisions.csv"
FIELDS = [
    "candidate_a_id", "candidate_a_name", "candidate_b_id", "candidate_b_name",
    "distance_m", "name_similarity", "phone_match", "address_match", "priority",
    "review_status", "reason",
]


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def reviewed_decisions(store_ids: set[str]) -> set[tuple[str, str]]:
    decisions = set()
    for row in read_csv(DECISIONS_PATH):
        first = (row.get("candidate_a_id") or "").strip()
        second = (row.get("candidate_b_id") or "").strip()
        outcome = (row.get("outcome") or "").strip()
        evidence_url = (row.get("evidence_url") or "").strip()
        verified_at = (row.get("verified_at") or "").strip()
        key = tuple(sorted((first, second)))
        if (
            not first or not second or first == second or key in decisions
            or first not in store_ids or second not in store_ids
            or outcome not in {"Distinct"}
            or not evidence_url.startswith(("https://", "http://"))
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified_at)
        ):
            raise ValueError(f"Invalid store identity decision: {row}")
        decisions.add(key)
    return decisions


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("&", " and ")
    return " ".join(
        token for token in re.findall(r"[a-z0-9]+", value)
        if token not in {"pty", "ltd", "limited", "the"}
    )


def normalized_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits[-8:] if len(digits) >= 8 else ""


def normalized_address(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", (value or "").lower())
    ignored = {
        "australia", "new", "south", "wales", "queensland", "victoria", "tasmania",
        "western", "northern", "territory", "capital", "zealand",
    }
    return "".join(token for token in tokens if token not in ignored)


def distance_metres(left: dict, right: dict) -> float:
    radius = 6_371_008.8
    lat1, lon1 = math.radians(float(left["latitude"])), math.radians(float(left["longitude"]))
    lat2, lon2 = math.radians(float(right["latitude"])), math.radians(float(right["longitude"]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def main() -> None:
    stores = read_csv(STORES_PATH)
    decisions = reviewed_decisions({store["store_id"] for store in stores})
    reviews = []
    for index, left in enumerate(stores):
        for right in stores[index + 1:]:
            if left["country"] != right["country"]:
                continue
            same_retailer = left["retailer"] == right["retailer"]
            # Cross-brand comparisons are useful only when one side is a
            # discovery/independent record. Same-retailer comparisons must stay
            # in scope because official locators can publish relocations twice.
            if not same_retailer and "Independent / Other optical" not in {left["retailer"], right["retailer"]}:
                continue
            distance = distance_metres(left, right)
            same_postcode = bool(left.get("postcode") and left.get("postcode") == right.get("postcode"))
            same_phone = bool(
                normalized_phone(left["phone"])
                and normalized_phone(left["phone"]) == normalized_phone(right["phone"])
            )
            if distance > 250 and not (same_retailer and same_phone and same_postcode):
                continue
            left_name, right_name = normalized(left["name"]), normalized(right["name"])
            similarity = SequenceMatcher(None, left_name, right_name).ratio()
            phone_match = same_phone
            left_address, right_address = normalized_address(left["full_address"]), normalized_address(right["full_address"])
            address_match = bool(
                len(left_address) >= 12 and len(right_address) >= 12
                and (left_address == right_address or left_address in right_address or right_address in left_address)
            )
            exact_or_contained_name = bool(
                min(len(left_name), len(right_name)) >= 6
                and (left_name == right_name or left_name in right_name or right_name in left_name)
            )
            both_independent = left["retailer"] == right["retailer"] == "Independent / Other optical"
            priority = ""
            reason = ""
            if phone_match and (distance <= 250 or (same_retailer and same_postcode)):
                priority = "High"
                reason = "Matching public phone and local market; identity needs reconciliation"
            elif address_match and (exact_or_contained_name or similarity >= 0.72):
                priority = "High"
                reason = "Matching meaningful address plus consistent name; identity needs reconciliation"
            elif exact_or_contained_name and distance <= 125 and (both_independent or similarity >= 0.82):
                priority = "High"
                reason = "Same or contained business name within 125 m; corroborating evidence required"
            elif similarity >= 0.82 and distance <= 100:
                priority = "Medium"
                reason = "Highly similar business name within 100 m; proximity is only a review signal"
            if not priority:
                continue
            if tuple(sorted((left["store_id"], right["store_id"]))) in decisions:
                continue
            reviews.append({
                "candidate_a_id": left["store_id"], "candidate_a_name": left["name"],
                "candidate_b_id": right["store_id"], "candidate_b_name": right["name"],
                "distance_m": f"{distance:.1f}", "name_similarity": f"{similarity:.3f}",
                "phone_match": str(phone_match).lower(), "address_match": str(address_match).lower(),
                "priority": priority, "review_status": "Pending", "reason": reason,
            })
    reviews.sort(key=lambda row: (0 if row["priority"] == "High" else 1, float(row["distance_m"])))
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(reviews)
    counts = {priority: sum(row["priority"] == priority for row in reviews) for priority in ("High", "Medium")}
    print(f"Wrote {len(reviews)} store identity review candidates to {OUTPUT_PATH}: {counts}")


if __name__ == "__main__":
    main()
