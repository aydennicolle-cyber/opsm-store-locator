#!/usr/bin/env python3
"""Reconcile incidental independent points to new official network records."""

from __future__ import annotations

import csv
import math
import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORES = ROOT / "data" / "optical_stores.csv"
REMAPS = ROOT / "data" / "store_identity_remaps.csv"
REVIEWS = ROOT / "data" / "priority_network_identity_review.csv"
NETWORKS = {
    "Bupa Optical", "Chemist Warehouse Optometry", "Dresden Vision", "Optical Warehouse",
    "The Optical Company", "Optical by National Pharmacies", "Matthews Eyecare",
}
REMAP_FIELDS = ["source_store_id", "canonical_store_id", "reason", "source_url", "verified_at"]
REVIEW_FIELDS = [
    "source_store_id", "source_name", "canonical_store_id", "canonical_name", "retailer",
    "distance_km", "name_similarity", "postcode_match", "phone_match", "review_status", "reason",
]


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalise(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\b(?:optical|optometrist|optometrists|optometry|eyecare|eye care|vision|the|and|hearing)\b", " ", value.lower())
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits[-8:] if len(digits) >= 8 else ""


def haversine(left: dict, right: dict) -> float:
    radius = 6371.0088
    lat1, lat2 = math.radians(float(left["latitude"])), math.radians(float(right["latitude"]))
    dlat = lat2 - lat1
    dlon = math.radians(float(right["longitude"]) - float(left["longitude"]))
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def similarity(left: str, right: str) -> float:
    a, b = normalise(left), normalise(right)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.95
    return SequenceMatcher(None, a, b).ratio()


def main() -> None:
    stores = read_csv(STORES)
    independents = [row for row in stores if row["retailer"] == "Independent / Other optical"]
    official = [row for row in stores if row["retailer"] in NETWORKS]
    existing = read_csv(REMAPS)
    existing_sources = {row["source_store_id"] for row in existing}
    accepted: list[dict] = []
    reviews: list[dict] = []
    used_pairs: set[tuple[str, str]] = set()

    for source in independents:
        possible = []
        for canonical in official:
            if source["country"] != canonical["country"]:
                continue
            distance = haversine(source, canonical)
            if distance > 2:
                continue
            name_score = similarity(source["name"], canonical["name"])
            postcode_match = bool(source["postcode"] and source["postcode"] == canonical["postcode"])
            phone_match = bool(phone(source["phone"]) and phone(source["phone"]) == phone(canonical["phone"]))
            address_score = similarity(source["full_address"], canonical["full_address"])
            score = (3 if phone_match else 0) + (2 if postcode_match else 0) + name_score + address_score + max(0, 1 - distance)
            possible.append((score, distance, name_score, address_score, postcode_match, phone_match, canonical))
        if not possible:
            continue
        score, distance, name_score, address_score, postcode_match, phone_match, canonical = max(possible, key=lambda item: item[0])
        reason = ""
        if phone_match and (postcode_match or distance <= 1):
            reason = "Incidental public record matches the official network store phone and geography"
        elif postcode_match and distance <= 0.1 and (name_score >= 0.35 or address_score >= 0.55):
            reason = "Incidental public record matches the official network store postcode, address/name and coordinates"
        elif postcode_match and distance <= 1 and name_score >= 0.82:
            reason = "Incidental public record matches the official network store name and postcode with corroborating coordinates"
        elif name_score >= 0.9 and distance <= 0.5:
            reason = "Incidental public record uses the official network identity at the same mapped location"
        pair = (source["store_id"], canonical["store_id"])
        if reason and source["store_id"] not in existing_sources and pair not in used_pairs:
            accepted.append({
                "source_store_id": source["store_id"], "canonical_store_id": canonical["store_id"],
                "reason": reason, "source_url": source["source_url"], "verified_at": date.today().isoformat(),
            })
            used_pairs.add(pair)
        elif (name_score >= 0.55 and distance <= 1) or (postcode_match and address_score >= 0.5 and distance <= 0.5):
            reviews.append({
                "source_store_id": source["store_id"], "source_name": source["name"],
                "canonical_store_id": canonical["store_id"], "canonical_name": canonical["name"],
                "retailer": canonical["retailer"], "distance_km": f"{distance:.3f}",
                "name_similarity": f"{name_score:.3f}", "postcode_match": str(postcode_match).lower(),
                "phone_match": str(phone_match).lower(), "review_status": "Pending",
                "reason": "Possible identity overlap; evidence did not meet automatic merge threshold",
            })

    all_remaps = existing + accepted
    with REMAPS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REMAP_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(all_remaps)
    with REVIEWS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(reviews, key=lambda row: (row["retailer"], row["source_name"])))
    print(f"Priority network reconciliation: {len(accepted)} accepted matches, {len(reviews)} review candidates")


if __name__ == "__main__":
    main()
