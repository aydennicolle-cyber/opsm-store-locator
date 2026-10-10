"""Admission checks for independently reviewed public optometry storefronts.

External supplier exports remain discovery evidence outside the public dataset.
Only the curated, source-backed rows in this module's CSV enter the network.
"""
from __future__ import annotations

import csv
import math
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
STORES_PATH = ROOT / "retailers" / "reviewed-independents" / "stores.csv"
ID_PREFIX = "independent-other-optical-reviewed-"
SOURCE_ID = "reviewed-independent-practices"
SOURCE_LABEL = "Reviewed independent public practices"
SETTINGS = {"High Street", "Shopping Centre", "Other", "Uncertain"}
REQUIRED = {
    "id", "name", "country", "state", "full_address",
    "latitude", "longitude", "services", "status",
    "business_type", "location_setting", "identity_reviewed", "coordinates_reviewed",
    "identity_evidence_url", "coordinate_evidence_url", "status_evidence_url",
    "verified_at", "evidence_notes",
}


def public_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password


def validate_rows(rows: list[dict]) -> None:
    seen = set()
    addresses = set()
    for row in rows:
        key = row.get("id", "")
        if any(not str(row.get(field, "")).strip() for field in REQUIRED):
            raise ValueError(f"Reviewed independent lacks required evidence: {key}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key) or key in seen:
            raise ValueError(f"Invalid or duplicate reviewed independent ID: {key}")
        seen.add(key)
        if row["country"] not in {"Australia", "New Zealand"}:
            raise ValueError(f"Reviewed independent outside AU/NZ: {key}")
        if row["status"] not in {"Active", "Opening Soon", "Unknown", "Temporarily Closed", "Closed"} or row["business_type"] not in {"Permanent retail optometry", "Prescription eyewear retail", "Contact lens retail", "Sunglasses retail"}:
            raise ValueError(f"Reviewed optical retail type and an explicit trading status are required: {key}")
        if row["identity_reviewed"] != "true" or row["coordinates_reviewed"] != "true":
            raise ValueError(f"Unreviewed identity/coordinates cannot enter the network: {key}")
        if row["location_setting"] not in SETTINGS:
            raise ValueError(f"Invalid reviewed independent setting: {key}")
        if row["location_setting"] != "Uncertain" and not public_url(row.get("setting_evidence_url", "")):
            raise ValueError(f"Location setting lacks public evidence: {key}")
        # A physical retailer can be evidenced by a public authority or centre
        # without an owned website. Keep that missing fact separate from the
        # mandatory identity, coordinate and trading-status evidence.
        if row.get("official_url") and not public_url(row["official_url"]):
            raise ValueError(f"Reviewed independent has invalid official_url: {key}")
        for field in ("identity_evidence_url", "coordinate_evidence_url", "status_evidence_url"):
            if not public_url(row[field]):
                raise ValueError(f"Reviewed independent lacks public {field}: {key}")
        try:
            verified = date.fromisoformat(row["verified_at"])
        except ValueError as exc:
            raise ValueError(f"Invalid independent review date: {key}") from exc
        if verified > date.today():
            raise ValueError(f"Independent review date is in the future: {key}")
        if (row.get("postal_code") and not re.fullmatch(r"\d{4}", row["postal_code"])) or len(row["full_address"]) < 10 or row["full_address"] in {"Australia", "New Zealand"}:
            raise ValueError(f"Reviewed retailer needs an evidenced premises address; supplied postcodes must be valid: {key}")
        lat, lon = float(row["latitude"]), float(row["longitude"])
        bounds = (-44.5, -9, 112, 154.5) if row["country"] == "Australia" else (-48, -33.5, 165, 179.5)
        if not math.isfinite(lat) or not math.isfinite(lon) or not (bounds[0] <= lat <= bounds[1] and bounds[2] <= lon <= bounds[3]):
            raise ValueError(f"Invalid reviewed independent coordinates: {key}")
        address = (row["country"], re.sub(r"\W+", "", row["full_address"].lower()))
        if address in addresses:
            raise ValueError(f"Two reviewed independents share an address; reconcile before admission: {key}")
        addresses.add(address)


def read_reviewed_rows(path: Path = STORES_PATH) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    validate_rows(rows)
    return rows


def classifications(rows: list[dict]) -> dict[str, dict]:
    types = {"High Street": "Main Street / Street-front", "Shopping Centre": "Shopping Centre", "Other": "Other", "Uncertain": "Unclassified"}
    return {
        ID_PREFIX + row["id"]: {
            "venue_name": "", "venue_id": "",
            "location_type": types[row["location_setting"]],
            "classification_confidence": "Low" if row["location_setting"] == "Uncertain" else "High",
            "classification_basis": row["evidence_notes"],
        }
        for row in rows
    }
