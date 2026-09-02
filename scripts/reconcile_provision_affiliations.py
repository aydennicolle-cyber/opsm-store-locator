#!/usr/bin/env python3
"""Reconcile official ProVision practices without treating affiliation as a retailer brand."""

from __future__ import annotations

import csv
import math
import re
import unicodedata
from difflib import SequenceMatcher
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROVISION = ROOT / "retailers" / "provision" / "stores.csv"
OUTPUT = DATA / "provision_identity_remaps.csv"
REVIEW = DATA / "provision_identity_review.csv"
TODAY = date.today().isoformat()
FIELDS = ["source_store_id", "canonical_store_id", "reason", "source_url", "verified_at"]
REVIEW_FIELDS = [
    "provision_store_id", "provision_name", "candidate_store_id", "candidate_name",
    "postcode", "distance_m", "name_similarity", "review_status", "reason",
]


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def normalise(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    value = value.lower().replace("&", " and ")
    return " ".join(re.findall(r"[a-z0-9]+", value))


def normalise_name(value: str) -> str:
    value = normalise(value)
    prefixes = (
        "george and matilda ", "eyecare plus ", "optical superstore ", "1001 optometry ",
        "eyeq optometrists ", "laubman and pank ", "opsm ", "specsavers ",
        "bailey nelson ", "oscar wylee ",
    )
    for prefix in prefixes:
        if value.startswith(prefix):
            value = value[len(prefix):]
    tokens = [
        token for token in value.split()
        if token not in {"pty", "ltd", "limited", "optometrist", "optometrists", "optometry"}
    ]
    return " ".join(tokens)


def phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits[-8:] if len(digits) >= 8 else ""


def address_key(value: str) -> str:
    words = normalise(value).split()
    ignored = {"australia", "australian", "capital", "territory", "new", "south", "wales",
               "queensland", "victoria", "tasmania"}
    return " ".join(word for word in words if word not in ignored)


def distance_metres(left: dict, right: dict) -> float:
    try:
        lat1, lon1 = math.radians(float(left["latitude"])), math.radians(float(left["longitude"]))
        lat2, lon2 = math.radians(float(right["latitude"])), math.radians(float(right["longitude"]))
    except (KeyError, TypeError, ValueError):
        return float("inf")
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def raw_named_targets() -> list[dict]:
    result = []
    for retailer, folder in (
        ("1001 Optometry", "1001-optometry"),
        ("EyeQ Optometrists", "eyeq-optometrists"),
        ("Laubman & Pank", "laubman-and-pank"),
    ):
        for row in read_csv(ROOT / "retailers" / folder / "stores.csv"):
            result.append({**row, "retailer": retailer, "store_id": f"{slug(retailer)}-{row['id']}"})
    return result


def raw_independent_targets() -> list[dict]:
    manual_sources = {
        row["source_store_id"] for row in read_csv(DATA / "store_identity_remaps.csv")
    }
    result = []
    for row in read_csv(ROOT / "retailers" / "independent-other" / "stores.csv"):
        store_id = f"independent-other-optical-{row['id']}"
        if store_id not in manual_sources:
            result.append({**row, "retailer": "Independent / Other optical", "store_id": store_id})
    return result


def match_reason(provision: dict, candidate: dict) -> tuple[str, float, float]:
    if provision.get("postal_code") != candidate.get("postcode", candidate.get("postal_code")):
        return "", 0.0, float("inf")
    similarity = SequenceMatcher(None, normalise_name(provision["name"]), normalise_name(candidate["name"])).ratio()
    distance = distance_metres(provision, candidate)
    same_phone = bool(phone(provision.get("phone", "")) and phone(provision.get("phone", "")) == phone(candidate.get("phone", "")))
    left_address = address_key(provision.get("full_address", ""))
    right_address = address_key(candidate.get("full_address", ""))
    same_address = bool(left_address and right_address and (left_address == right_address or left_address in right_address or right_address in left_address))
    same_name = bool(normalise_name(provision["name"]) and normalise_name(provision["name"]) == normalise_name(candidate["name"]))
    if same_phone:
        return "Official ProVision practice and canonical store share postcode and phone", similarity, distance
    if same_address and similarity >= 0.55:
        return "Official ProVision practice and canonical store share address and a consistent business name", similarity, distance
    if same_name and distance <= 1000:
        return "Official ProVision practice and canonical store share name and postcode with corroborating coordinates", similarity, distance
    if similarity >= 0.92 and distance <= 250:
        return "Official ProVision practice and canonical store share postcode, near-identical name and corroborating coordinates", similarity, distance
    return "", similarity, distance


def main() -> None:
    provision_rows = read_csv(PROVISION)
    published = [
        row for row in read_csv(DATA / "optical_stores.csv")
        if "provision" not in row.get("affiliations", "").split("|")
    ]
    candidates_by_id = {
        row["store_id"]: row
        for row in published + raw_independent_targets() + raw_named_targets()
    }
    existing = list(candidates_by_id.values())
    by_postcode: dict[str, list[dict]] = {}
    for row in existing:
        postcode = row.get("postcode", row.get("postal_code", ""))
        by_postcode.setdefault(postcode, []).append(row)

    remaps = []
    reviews = []
    used_candidates = set()
    for practice in provision_rows:
        provision_id = f"independent-other-optical-provision-{practice['id']}"
        scored = []
        for candidate in by_postcode.get(practice["postal_code"], []):
            if candidate.get("store_id") == provision_id:
                continue
            reason, similarity, distance = match_reason(practice, candidate)
            named_candidate = candidate.get("retailer") != "Independent / Other optical"
            if named_candidate and reason and not (
                "share postcode and phone" in reason or "share address" in reason
            ):
                reason = ""
            if reason:
                scored.append((reason, similarity, distance, candidate))
            elif similarity >= 0.72 and distance <= 1000:
                reviews.append({
                    "provision_store_id": provision_id, "provision_name": practice["name"],
                    "candidate_store_id": candidate["store_id"], "candidate_name": candidate["name"],
                    "postcode": practice["postal_code"], "distance_m": round(distance),
                    "name_similarity": round(similarity, 3), "review_status": "Pending",
                    "reason": "Possible same practice; insufficient evidence for automatic identity merge",
                })
        scored.sort(key=lambda item: (-item[1], item[2], item[3]["store_id"]))
        if not scored:
            continue
        reason, _, _, candidate = scored[0]
        if candidate["store_id"] in used_candidates:
            reviews.append({
                "provision_store_id": provision_id, "provision_name": practice["name"],
                "candidate_store_id": candidate["store_id"], "candidate_name": candidate["name"],
                "postcode": practice["postal_code"], "distance_m": round(distance_metres(practice, candidate)),
                "name_similarity": round(SequenceMatcher(None, normalise_name(practice["name"]), normalise_name(candidate["name"])).ratio(), 3),
                "review_status": "Pending", "reason": "Multiple ProVision records match one canonical store",
            })
            continue
        used_candidates.add(candidate["store_id"])
        named = candidate.get("retailer") != "Independent / Other optical"
        if named:
            source_id, canonical_id = provision_id, candidate["store_id"]
        else:
            source_id, canonical_id = candidate["store_id"], provision_id
        remaps.append({
            "source_store_id": source_id, "canonical_store_id": canonical_id, "reason": reason,
            "source_url": practice["official_url"], "verified_at": TODAY,
        })

    remaps.sort(key=lambda row: row["source_store_id"])
    reviews.sort(key=lambda row: (row["postcode"], row["provision_name"], row["candidate_name"]))
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(remaps)
    with REVIEW.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(reviews)
    print(f"ProVision reconciliation: {len(remaps)} accepted identity matches, {len(reviews)} review candidates")


if __name__ == "__main__":
    main()
