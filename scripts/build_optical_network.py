#!/usr/bin/env python3
"""Combine, classify, validate, and export the Australian optical store network."""

from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_CSV = DATA_DIR / "optical_stores.csv"
OUTPUT_GEOJSON = DATA_DIR / "optical_stores.geojson"
OUTPUT_META = DATA_DIR / "optical_stores.meta.json"
REVIEW_PATH = DATA_DIR / "classification_review.csv"
OVERRIDE_PATH = DATA_DIR / "location_overrides.csv"
AREA_OVERRIDE_PATH = DATA_DIR / "public_area_overrides.csv"
VALID_STATES = {"ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"}
FIELDS = [
    "retailer",
    "store_id",
    "name",
    "status",
    "state",
    "suburb",
    "postcode",
    "full_address",
    "phone",
    "latitude",
    "longitude",
    "official_url",
    "services",
    "audiology",
    "venue_name",
    "venue_id",
    "location_type",
    "classification_confidence",
    "classification_basis",
    "store_area_sqm",
    "area_measure",
    "area_source",
    "area_date",
    "area_confidence",
    "source_url",
    "fetched_at",
]

CENTRE_PHRASES = (
    "shopping centre",
    "shopping center",
    "shopping ctr",
    "s/c",
    "westfield",
    "marketplace",
    "town centre",
    "town center",
    "central plaza",
    "retail centre",
    "retail center",
    "city centre",
    "city center",
    "centrepoint",
    "centre point",
    "the glen",
    "pacific fair",
    "erina fair",
)
CENTRE_NAME_TERMS = (
    " centre",
    " center",
    " plaza",
    " square",
    " towers",
    " arcade",
    " galleria",
    " marketplace",
    " junction",
    " chase",
    " mall",
    " village",
    " highpoint",
    " chadstone",
    " northland",
    " southland",
    " eastland",
    " carousel",
    " carindale",
    " chermside",
    " indooroopilly",
)
OTHER_TERMS = (
    "retail park",
    "homemaker centre",
    "homemaker center",
    "airport terminal",
    "domestic terminal",
    "international terminal",
    "hospital precinct",
    "university campus",
    "business park",
)
STREET_TERMS = (
    " street",
    " st,",
    " road",
    " rd,",
    " highway",
    " hwy",
    " avenue",
    " ave,",
    " parade",
    " terrace",
    " lane",
    " drive",
    " boulevard",
)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_freshness() -> dict[str, str]:
    opsm = json.loads((ROOT / "opsm_stores.geojson").read_text(encoding="utf-8"))["metadata"]
    specsavers = json.loads(
        (ROOT / "retailers" / "specsavers" / "source_snapshot.json").read_text(encoding="utf-8")
    )
    bailey = json.loads(
        (ROOT / "retailers" / "bailey-nelson" / "source_snapshot.json").read_text(encoding="utf-8")
    )
    return {
        "OPSM": opsm["fetched_at"],
        "Specsavers": specsavers["fetched_at"],
        "Bailey Nelson": bailey["fetched_at"],
    }


def tidy(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def load_stores(freshness: dict[str, str]) -> list[dict]:
    stores = []
    for row in read_csv(ROOT / "opsm_stores.csv"):
        local_id = row.get("sap_id") or row.get("identifier")
        services = tidy(row.get("services", ""))
        stores.append(
            {
                "retailer": "OPSM",
                "store_id": f"opsm-{local_id}",
                "name": tidy(row["name"]),
                "status": "Active",
                "state": tidy(row["state"]).upper(),
                "suburb": tidy(row["city"]),
                "postcode": tidy(row["postal_code"]),
                "full_address": tidy(row["full_address"]),
                "phone": tidy(row["phone"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "official_url": "https://www.opsm.com.au/en/opsm-au/find-store",
                "services": services,
                "audiology": str("audiology" in services.lower()).lower(),
                "source_url": "https://www.opsm.com.au/en/opsm-au/find-store",
                "fetched_at": freshness["OPSM"],
            }
        )
    for retailer, folder in (("Specsavers", "specsavers"), ("Bailey Nelson", "bailey-nelson")):
        for row in read_csv(ROOT / "retailers" / folder / "stores.csv"):
            local_id = tidy(row["id"])
            stores.append(
                {
                    "retailer": retailer,
                    "store_id": f"{slug(retailer)}-{local_id}",
                    "name": tidy(row["name"]),
                    "status": tidy(row.get("status", "Active")) or "Active",
                    "state": tidy(row["state"]).upper(),
                    "suburb": tidy(row["city"]),
                    "postcode": tidy(row["postal_code"]),
                    "full_address": tidy(row["full_address"]),
                    "phone": tidy(row.get("phone", "")),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "official_url": tidy(row["official_url"]),
                    "services": tidy(row.get("services", "")),
                    "audiology": tidy(row.get("audiology", "false")).lower(),
                    "source_url": tidy(row["official_url"]),
                    "fetched_at": freshness[retailer],
                }
            )
    return stores


def cleaned_store_name(store: dict) -> str:
    name = store["name"]
    for prefix in ("OPSM ", "Bailey Nelson ", "Specsavers "):
        if name.lower().startswith(prefix.lower()):
            name = name[len(prefix) :]
    if " - " in name:
        parts = name.split(" - ")
        name = max(parts, key=lambda part: sum(term in f" {part.lower()}" for term in CENTRE_NAME_TERMS))
    return tidy(name)


def clean_venue(value: str) -> str:
    value = tidy(value)
    value = re.sub(r"^(shop|suite|level|unit)\s*[a-z0-9/ -]+,?\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^\d+[a-z]?\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\bS/C\b", "Shopping Centre", value, flags=re.IGNORECASE)
    return value.strip(" ,- ")


def venue_from_evidence(store: dict, text: str) -> str:
    name = cleaned_store_name(store)
    lowered_name = f" {name.lower()}"
    if any(term in lowered_name for term in CENTRE_NAME_TERMS) or any(
        phrase in lowered_name for phrase in CENTRE_PHRASES
    ):
        return clean_venue(name)
    for segment in store["full_address"].split(","):
        lowered = f" {segment.lower()}"
        if any(phrase in lowered for phrase in CENTRE_PHRASES) or any(
            term in lowered for term in CENTRE_NAME_TERMS
        ):
            return clean_venue(segment)
    named_centres = ("Highpoint", "Chadstone", "Northland", "Southland", "Eastland")
    for centre in named_centres:
        if centre.lower() in text:
            return centre
    return ""


def venue_identifier(state: str, venue_name: str) -> str:
    if not venue_name:
        return ""
    value = venue_name.lower().replace("&", " and ")
    value = re.sub(r"\b(shopping|centre|center|s/c|mall)\b", " ", value)
    tokens = sorted(set(re.findall(r"[a-z0-9]+", value)))
    return slug(f"{state} {' '.join(tokens)}") if tokens else ""


def classify(store: dict) -> dict:
    text = f" {store['name']} {store['full_address']} ".lower()
    if any(term in text for term in OTHER_TERMS):
        return {
            "venue_name": "",
            "venue_id": "",
            "location_type": "Other",
            "classification_confidence": "High",
            "classification_basis": "Official name/address contains a non-centre commercial venue term",
        }
    explicit = [phrase for phrase in CENTRE_PHRASES if phrase in text]
    named = [term.strip() for term in CENTRE_NAME_TERMS if term in text]
    shop_format = bool(re.search(r"\b(shop|level)\s*[a-z0-9]", text))
    if explicit or named or shop_format:
        venue_name = venue_from_evidence(store, text)
        confidence = "High" if explicit or named else "Medium"
        basis = "Official name/address contains shopping-centre evidence"
        if shop_format and not (explicit or named):
            basis = "Official address uses a shop/level format; venue name requires review"
        return {
            "venue_name": venue_name,
            "venue_id": venue_identifier(store["state"], venue_name),
            "location_type": "Shopping Centre",
            "classification_confidence": confidence,
            "classification_basis": basis,
        }
    has_street = any(term in text for term in STREET_TERMS)
    numbered = bool(re.search(r"\b\d+[a-z]?[- /]?\d*\s+[a-z]", store["full_address"].lower()))
    corner = bool(re.search(r"\b(cnr|corner)\b", text))
    if has_street and (numbered or corner):
        return {
            "venue_name": "",
            "venue_id": "",
            "location_type": "Main Street / Street-front",
            "classification_confidence": "Medium",
            "classification_basis": "Official address is a numbered or corner street address without centre evidence",
        }
    if has_street:
        return {
            "venue_name": "",
            "venue_id": "",
            "location_type": "Main Street / Street-front",
            "classification_confidence": "Low",
            "classification_basis": "Official address contains street evidence but needs review",
        }
    return {
        "venue_name": "",
        "venue_id": "",
        "location_type": "Unclassified",
        "classification_confidence": "Low",
        "classification_basis": "Insufficient official venue or street evidence",
    }


def load_overrides() -> dict[tuple[str, str], dict]:
    overrides = {}
    for row in read_csv(OVERRIDE_PATH):
        overrides[(row["retailer"], row["store_id"])] = {
            key: tidy(row[key])
            for key in (
                "venue_name",
                "venue_id",
                "location_type",
                "classification_confidence",
                "classification_basis",
            )
        }
    return overrides


def load_area_overrides() -> dict[tuple[str, str], dict]:
    overrides = {}
    for row in read_csv(AREA_OVERRIDE_PATH):
        key = (tidy(row.get("retailer", "")), tidy(row.get("store_id", "")))
        if not all(key):
            continue
        area = tidy(row.get("store_area_sqm", ""))
        if area:
            numeric_area = float(area)
            if numeric_area <= 0:
                raise ValueError(f"Invalid store area for {key[0]} {key[1]}")
            area = f"{numeric_area:g}"
        measure = tidy(row.get("area_measure", "")).upper()
        if measure and measure not in {"NLA", "GLA", "GFA", "ESTIMATED FOOTPRINT"}:
            raise ValueError(f"Invalid area measure for {key[0]} {key[1]}: {measure}")
        overrides[key] = {
            "store_area_sqm": area,
            "area_measure": measure,
            "area_source": tidy(row.get("area_source", "")),
            "area_date": tidy(row.get("area_date", "")),
            "area_confidence": tidy(row.get("area_confidence", "")),
        }
    return overrides


def validate(stores: list[dict]) -> None:
    ids = [store["store_id"] for store in stores]
    if len(ids) != len(set(ids)):
        duplicates = [item for item, count in Counter(ids).items() if count > 1]
        raise ValueError(f"Duplicate store IDs: {duplicates[:10]}")
    expected = {"OPSM": 335, "Specsavers": 399, "Bailey Nelson": 68}
    counts = Counter(store["retailer"] for store in stores)
    if dict(counts) != expected:
        raise ValueError(f"Unexpected retailer counts: {dict(counts)}")
    for store in stores:
        if store["state"] not in VALID_STATES:
            raise ValueError(f"Invalid state for {store['store_id']}: {store['state']}")
        if not (-44.5 <= store["latitude"] <= -9.0 and 112.0 <= store["longitude"] <= 154.5):
            raise ValueError(f"Invalid coordinates for {store['store_id']}")
        if not store["source_url"] or not store["fetched_at"]:
            raise ValueError(f"Missing source metadata for {store['store_id']}")


def network_summary(stores: list[dict]) -> dict:
    venues: dict[str, set[str]] = defaultdict(set)
    venue_names = {}
    for store in stores:
        if store["venue_id"]:
            venues[store["venue_id"]].add(store["retailer"])
            venue_names[store["venue_id"]] = store["venue_name"]
    return {
        "total": len(stores),
        "by_retailer": dict(sorted(Counter(store["retailer"] for store in stores).items())),
        "by_state": dict(sorted(Counter(store["state"] for store in stores).items())),
        "by_location_type": dict(sorted(Counter(store["location_type"] for store in stores).items())),
        "multi_brand_venues": [
            {"venue_id": venue_id, "venue_name": venue_names[venue_id], "retailers": sorted(retailers)}
            for venue_id, retailers in sorted(venues.items())
            if len(retailers) > 1
        ],
        "single_brand_venue_count": sum(1 for retailers in venues.values() if len(retailers) == 1),
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    freshness = read_freshness()
    stores = load_stores(freshness)
    overrides = load_overrides()
    area_overrides = load_area_overrides()
    for store in stores:
        store.update(classify(store))
        store.update(
            {
                "store_area_sqm": "",
                "area_measure": "",
                "area_source": "",
                "area_date": "",
                "area_confidence": "Unknown",
            }
        )
        override = overrides.get((store["retailer"], store["store_id"]))
        if override:
            store.update(override)
        area_override = area_overrides.get((store["retailer"], store["store_id"]))
        if area_override:
            store.update(area_override)
    stores.sort(key=lambda item: (item["state"], item["suburb"], item["retailer"], item["name"]))
    validate(stores)

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: store.get(field, "") for field in FIELDS} for store in stores)

    features = []
    for store in stores:
        properties = {field: store.get(field, "") for field in FIELDS if field not in {"latitude", "longitude"}}
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [store["longitude"], store["latitude"]]},
                "properties": properties,
            }
        )
    summary = network_summary(stores)
    metadata = {
        "name": "Australian Optical Retail Network",
        "store_count": len(stores),
        "source_freshness": freshness,
        "retailer_counts": summary["by_retailer"],
        "classification_types": ["Shopping Centre", "Main Street / Street-front", "Other", "Unclassified"],
    }
    OUTPUT_GEOJSON.write_text(
        json.dumps({"type": "FeatureCollection", "metadata": metadata, "features": features}, indent=2) + "\n",
        encoding="utf-8",
    )
    OUTPUT_META.write_text(json.dumps({**metadata, "network_summary": summary}, indent=2) + "\n", encoding="utf-8")

    review = [
        store
        for store in stores
        if store["classification_confidence"] == "Low"
        or store["location_type"] == "Unclassified"
        or (store["location_type"] == "Shopping Centre" and not store["venue_id"])
    ]
    with REVIEW_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: store.get(field, "") for field in FIELDS} for store in review)

    print(f"Wrote {len(stores)} stores to {OUTPUT_CSV}")
    print(f"Retailers: {summary['by_retailer']}")
    print(f"Location types: {summary['by_location_type']}")
    print(f"Review queue: {len(review)} stores")
    print(f"Multi-brand reviewed venues: {len(summary['multi_brand_venues'])}")


if __name__ == "__main__":
    main()
