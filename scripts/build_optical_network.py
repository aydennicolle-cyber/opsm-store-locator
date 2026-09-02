#!/usr/bin/env python3
"""Combine, classify, validate, and export the AU/NZ optical store network."""

from __future__ import annotations

import csv
import html
import json
import os
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
CENTRE_REGISTRY_PATH = DATA_DIR / "shopping_centres.csv"
CENTRE_MEMBERSHIP_PATH = DATA_DIR / "centre_store_memberships.csv"
RETAILER_REGISTRY_PATH = DATA_DIR / "retailer_registry.json"
IDENTITY_REMAPS_PATH = DATA_DIR / "store_identity_remaps.csv"
PROVISION_REMAPS_PATH = DATA_DIR / "provision_identity_remaps.csv"
VALID_STATES = {"ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"}
VALID_NZ_REGIONS = {
    "Auckland",
    "Bay of Plenty",
    "Canterbury",
    "Gisborne",
    "Hawke's Bay",
    "Manawatu-Whanganui",
    "Marlborough",
    "Nelson",
    "Northland",
    "Otago",
    "Southland",
    "Taranaki",
    "Tasman",
    "Waikato",
    "Wellington",
    "West Coast",
}
FIELDS = [
    "retailer",
    "store_id",
    "affiliations",
    "name",
    "status",
    "country",
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
    "shp ctr",
    "s/c",
    "westfield",
    "marketplace",
    "market place",
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
    " forum",
    " shoppingtown",
    " shoppingworld",
    " hypermarket",
    " hyperdome",
    " stockland",
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
    " place",
    " pl,",
    " walk",
)
AMBIGUOUS_NAME_TERMS = {" towers", " junction", " indooroopilly"}


def centre_evidence_segments(store: dict) -> list[str]:
    locality_values = {
        tidy(store.get("suburb", "")).lower(),
        tidy(store.get("state", "")).lower(),
        tidy(store.get("postcode", "")).lower(),
        tidy(store.get("country", "")).lower(),
    }
    segments = []
    for segment in store.get("full_address", "").split(","):
        cleaned = tidy(segment)
        lowered = cleaned.lower()
        if not cleaned or lowered in locality_values:
            continue
        # "Queen Street Mall" and "Centre Dandenong Road" are street names,
        # not evidence that the tenancy is inside a shopping centre.
        if re.search(r"\b(?:street|st|road|rd|avenue|ave|drive|dr|parade|pde|highway|hwy)\s+mall\b", lowered):
            continue
        if re.search(r"\bcentre\s+[a-z' -]+\s+(?:road|rd|street|st|avenue|ave|drive|dr)\b", lowered):
            continue
        segments.append(lowered)
    return segments


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def retailer_registry() -> list[dict]:
    payload = json.loads(RETAILER_REGISTRY_PATH.read_text(encoding="utf-8"))
    retailers = payload.get("retailers", [])
    names = [item.get("name", "") for item in retailers]
    if not retailers or any(not name for name in names) or len(names) != len(set(names)):
        raise ValueError("Retailer registry must contain unique, named retailer entries")
    return retailers


def identity_remaps() -> dict[str, str]:
    remaps = {}
    for path in (IDENTITY_REMAPS_PATH, PROVISION_REMAPS_PATH):
        for row in read_csv(path):
            source = tidy(row.get("source_store_id", ""))
            canonical = tidy(row.get("canonical_store_id", ""))
            if not source or not canonical or source == canonical or source in remaps:
                raise ValueError(f"Invalid store identity remap: {row}")
            remaps[source] = canonical
    return remaps


def read_freshness() -> dict[str, str]:
    opsm = json.loads((ROOT / "opsm_stores.geojson").read_text(encoding="utf-8"))["metadata"]
    specsavers = json.loads(
        (ROOT / "retailers" / "specsavers" / "source_snapshot.json").read_text(encoding="utf-8")
    )
    bailey = json.loads(
        (ROOT / "retailers" / "bailey-nelson" / "source_snapshot.json").read_text(encoding="utf-8")
    )
    oscar_wylee = json.loads(
        (ROOT / "retailers" / "oscar-wylee" / "source_snapshot.json").read_text(encoding="utf-8")
    )
    freshness = {
        "OPSM Australia": opsm["fetched_at"],
        "Specsavers Australia": specsavers["fetched_at"],
        "Bailey Nelson Australia": bailey["fetched_at"],
        "Oscar Wylee Australia": oscar_wylee["fetched_at"],
        "Specsavers New Zealand": json.loads(
            (ROOT / "retailers" / "specsavers-nz" / "source_snapshot.json").read_text(encoding="utf-8")
        )["fetched_at"],
        "Oscar Wylee New Zealand": json.loads(
            (ROOT / "retailers" / "oscar-wylee-nz" / "source_snapshot.json").read_text(encoding="utf-8")
        )["fetched_at"],
        "OPSM New Zealand": json.loads(
            (ROOT / "retailers" / "opsm-nz" / "source_snapshot.json").read_text(encoding="utf-8")
        )["fetched_at"],
        "Bailey Nelson New Zealand": json.loads(
            (ROOT / "retailers" / "bailey-nelson-nz" / "source_snapshot.json").read_text(encoding="utf-8")
        )["fetched_at"],
        "Independent / Other optical": json.loads(
            (ROOT / "retailers" / "independent-other" / "source_snapshot.json").read_text(encoding="utf-8")
        )["fetched_at"],
    }
    for retailer, folder, label in (
        ("George & Matilda", "george-and-matilda", "George & Matilda Australia"),
        ("Eyecare Plus", "eyecare-plus", "Eyecare Plus Australia"),
        ("Optical Superstore", "optical-superstore", "Optical Superstore Australia"),
        ("1001 Optometry", "1001-optometry", "1001 Optometry Australia"),
        ("EyeQ Optometrists", "eyeq-optometrists", "EyeQ Optometrists Australia"),
        ("Laubman & Pank", "laubman-and-pank", "Laubman & Pank Australia"),
        ("ProVision", "provision", "ProVision Australia"),
    ):
        snapshot = json.loads(
            (ROOT / "retailers" / folder / "source_snapshot.json").read_text(encoding="utf-8")
        )
        freshness[label] = snapshot["fetched_at"]
    return freshness


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
                "affiliations": "",
                "name": tidy(row["name"]),
                "status": "Active",
                "country": "Australia",
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
                "fetched_at": freshness["OPSM Australia"],
            }
        )
    for retailer, folder, source_key, id_country in (
        ("Specsavers", "specsavers", "Specsavers Australia", ""),
        ("Bailey Nelson", "bailey-nelson", "Bailey Nelson Australia", ""),
        ("Oscar Wylee", "oscar-wylee", "Oscar Wylee Australia", ""),
        ("Specsavers", "specsavers-nz", "Specsavers New Zealand", "nz-"),
        ("Oscar Wylee", "oscar-wylee-nz", "Oscar Wylee New Zealand", "nz-"),
        ("Bailey Nelson", "bailey-nelson-nz", "Bailey Nelson New Zealand", "nz-"),
        (
            "Independent / Other optical",
            "independent-other",
            "Independent / Other optical",
            "",
        ),
        ("George & Matilda", "george-and-matilda", "George & Matilda Australia", ""),
        ("Eyecare Plus", "eyecare-plus", "Eyecare Plus Australia", ""),
        ("Optical Superstore", "optical-superstore", "Optical Superstore Australia", ""),
        ("1001 Optometry", "1001-optometry", "1001 Optometry Australia", ""),
        ("EyeQ Optometrists", "eyeq-optometrists", "EyeQ Optometrists Australia", ""),
        ("Laubman & Pank", "laubman-and-pank", "Laubman & Pank Australia", ""),
        ("Independent / Other optical", "provision", "ProVision Australia", "provision-"),
    ):
        for row in read_csv(ROOT / "retailers" / folder / "stores.csv"):
            local_id = tidy(row["id"])
            country = tidy(row.get("country", "")) or "Australia"
            stores.append(
                {
                    "retailer": retailer,
                    "store_id": f"{slug(retailer)}-{id_country}{local_id}",
                    "affiliations": "provision" if folder == "provision" else "",
                    "name": tidy(row["name"]),
                    "status": tidy(row.get("status", "Active")) or "Active",
                    "country": country,
                    "state": tidy(row["state"]).upper() if country == "Australia" else tidy(row["state"]),
                    "suburb": tidy(row["city"]),
                    "postcode": tidy(row["postal_code"]),
                    "full_address": tidy(row["full_address"]),
                    "phone": tidy(row.get("phone", "")),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "official_url": tidy(row["official_url"]),
                    "services": tidy(row.get("services", "")),
                    "audiology": tidy(row.get("audiology", "false")).lower(),
                    "source_url": tidy(row.get("source_url", "")) or tidy(row["official_url"]),
                    "fetched_at": freshness[source_key],
                }
            )
    for row in read_csv(ROOT / "retailers" / "opsm-nz" / "stores.csv"):
        local_id = row.get("sap_id") or row.get("identifier")
        services = tidy(row.get("services", ""))
        stores.append(
            {
                "retailer": "OPSM",
                "store_id": f"opsm-nz-{local_id}",
                "affiliations": "",
                "name": tidy(row["name"]),
                "status": tidy(row.get("status", "Active")) or "Active",
                "country": "New Zealand",
                "state": tidy(row["state"]),
                "suburb": tidy(row["city"]),
                "postcode": tidy(row["postal_code"]),
                "full_address": tidy(row["full_address"]),
                "phone": tidy(row.get("phone", "")),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "official_url": tidy(row["official_url"]),
                "services": services,
                "audiology": tidy(row.get("audiology", "false")).lower(),
                "source_url": tidy(row["official_url"]),
                "fetched_at": freshness["OPSM New Zealand"],
            }
        )
    remaps = identity_remaps()
    by_id = {store["store_id"]: store for store in stores}
    missing = [
        (source, canonical) for source, canonical in remaps.items()
        if source not in by_id or canonical not in by_id
    ]
    if missing:
        raise ValueError(f"Store identity remap refers to missing source/canonical store: {missing[:5]}")
    for source, canonical in remaps.items():
        source_affiliations = {
            item for item in by_id[source].get("affiliations", "").split("|") if item
        }
        canonical_affiliations = {
            item for item in by_id[canonical].get("affiliations", "").split("|") if item
        }
        by_id[canonical]["affiliations"] = "|".join(sorted(source_affiliations | canonical_affiliations))
    return [store for store in stores if store["store_id"] not in remaps]


def cleaned_store_name(store: dict) -> str:
    name = store["name"]
    for prefix in (
        "OPSM ", "Bailey Nelson ", "Specsavers ", "Oscar Wylee ",
        "George & Matilda ", "Eyecare Plus ", "Optical Superstore ",
        "1001 Optometry ", "EyeQ Optometrists ", "Laubman & Pank ",
    ):
        if name.lower().startswith(prefix.lower()):
            name = name[len(prefix) :]
    if " - " in name:
        parts = name.split(" - ")
        name = max(parts, key=lambda part: sum(term in f" {part.lower()}" for term in CENTRE_NAME_TERMS))
    return tidy(name)


def clean_venue(value: str) -> str:
    value = tidy(value)
    unit_code = r"(?:[a-z]*\d+[a-z]*|[a-z])(?:[./-](?:[a-z]*\d+[a-z]*|\d+[a-z]*))*"
    unit_prefix = re.compile(
        rf"^(?:shop|suite|level|unit)\s*(?:no\.?\s*)?{unit_code}"
        rf"(?:\s*(?:,|&)\s*{unit_code})*\s*(?:\([^)]*\))?\s*,?\s*",
        flags=re.IGNORECASE,
    )
    for _ in range(2):
        cleaned = unit_prefix.sub("", value, count=1)
        if cleaned == value:
            break
        value = cleaned
    value = re.sub(
        rf"\s+(?:shop|suite|level|unit)\s*(?:no\.?\s*)?{unit_code}\s*$",
        "",
        value,
        flags=re.IGNORECASE,
    )
    leading_code = re.match(rf"^{unit_code}\s+(.+)$", value, flags=re.IGNORECASE)
    if leading_code:
        remainder = leading_code.group(1)
        lowered = f" {remainder.lower()}"
        if any(phrase in lowered for phrase in CENTRE_PHRASES) or any(
            term in lowered for term in CENTRE_NAME_TERMS
        ):
            value = remainder
    value = re.sub(r"^\d+[a-z]?\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\bS/C\b", "Shopping Centre", value, flags=re.IGNORECASE)
    value = re.sub(r"\bShp\s+Ctr\b", "Shopping Centre", value, flags=re.IGNORECASE)
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
    value = re.sub(r"\bstocklands\b", "stockland", value)
    value = re.sub(r"\b(?:level|lvl)\s*[a-z0-9./-]+\b", " ", value)
    value = re.sub(r"\b(?:shop|suite|unit)\s*[a-z0-9./-]+\b", " ", value)
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
    evidence_segments = centre_evidence_segments(store)
    name_text = f" {store['name'].lower()} "
    additional_network = store["retailer"] in {
        "George & Matilda", "Eyecare Plus", "Optical Superstore", "1001 Optometry",
        "EyeQ Optometrists", "Laubman & Pank",
    } or "provision" in store.get("affiliations", "").split("|")
    if additional_network:
        explicit = [
            phrase for phrase in CENTRE_PHRASES
            if phrase in name_text or any(phrase in segment for segment in evidence_segments)
        ]
        named = [
            term.strip() for term in CENTRE_NAME_TERMS
            if any(term in f" {segment}" for segment in evidence_segments)
            or (term not in AMBIGUOUS_NAME_TERMS and term in name_text)
        ]
    else:
        # Preserve the established classifier for the previously audited core
        # networks; the stricter segment logic applies to newly added sources.
        explicit = [phrase for phrase in CENTRE_PHRASES if phrase in text]
        named = [term.strip() for term in CENTRE_NAME_TERMS if term in text]
    shop_format = bool(re.search(r"\b(shop|level)\s*[a-z0-9]", text))
    if explicit or named or (shop_format and not additional_network):
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
            "classification_basis": (
                "Official address is a numbered or corner street address without named centre evidence"
                if not shop_format
                else "Official address has a shop/unit within a numbered street address but no named centre evidence"
            ),
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


def load_centre_memberships() -> dict[tuple[str, str], dict]:
    centres = {row["venue_id"]: row for row in read_csv(CENTRE_REGISTRY_PATH)}
    memberships = {}
    for row in read_csv(CENTRE_MEMBERSHIP_PATH):
        venue_id = tidy(row["venue_id"])
        if venue_id not in centres:
            raise ValueError(f"Unknown centre membership venue ID: {venue_id}")
        key = (tidy(row["retailer"]), tidy(row["store_id"]))
        if key in memberships:
            raise ValueError(f"Duplicate centre membership: {key[0]} {key[1]}")
        centre = centres[venue_id]
        memberships[key] = {
            "venue_name": tidy(centre["venue_name"]),
            "venue_id": venue_id,
            "location_type": "Shopping Centre",
            "classification_confidence": tidy(row.get("confidence", "")) or "High",
            "classification_basis": tidy(row["classification_basis"]),
        }
    return memberships


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
    counts = Counter(store["retailer"] for store in stores)
    registry = retailer_registry()
    required_retailers = {item["name"] for item in registry}
    if set(counts) != required_retailers or any(counts[retailer] == 0 for retailer in required_retailers):
        raise ValueError(f"Missing required retailer scope: {dict(counts)}")
    source_counts = Counter()
    for item in registry:
        for folder in item.get("source_folders", []):
            source_counts[item["name"]] += len(read_csv(ROOT / "retailers" / folder / "stores.csv"))
    source_counts["Independent / Other optical"] += len(
        read_csv(ROOT / "retailers" / "provision" / "stores.csv")
    )
    for source_store_id in identity_remaps():
        matched = next(
            (item for item in registry if source_store_id.startswith(f"{item['slug']}-")),
            None,
        )
        if not matched:
            raise ValueError(f"Cannot resolve remapped source retailer: {source_store_id}")
        source_counts[matched["name"]] -= 1
    if counts != source_counts:
        raise ValueError(f"Combined counts do not reconcile to source files: combined={dict(counts)} source={dict(source_counts)}")
    history_paths = sorted((DATA_DIR / "history").glob("*.json"))
    if (OUTPUT_CSV.exists() or history_paths) and os.environ.get("ALLOW_NETWORK_REDUCTION") != "1":
        # Compare with the latest generated network when one exists. An older
        # archived snapshot may pre-date a separately reviewed source-scope
        # correction; it should not block every later no-change rebuild.
        if OUTPUT_CSV.exists():
            prior_rows = read_csv(OUTPUT_CSV)
            prior_by_id = {store["store_id"]: store for store in prior_rows}
            prior_scopes = Counter(
                (store["retailer"], store.get("country", "Australia"))
                for store in prior_rows
            )
            for source_store_id in identity_remaps():
                previous = prior_by_id.get(source_store_id)
                if previous:
                    prior_scopes[(previous["retailer"], previous.get("country", "Australia"))] -= 1
            baseline_label = "latest generated network"
        else:
            previous = json.loads(history_paths[-1].read_text(encoding="utf-8")).get("stores", {})
            prior_scopes = Counter(
                (store["retailer"], store.get("country", "Australia")) for store in previous.values()
            )
            baseline_label = "latest archived network"
        current_scopes = Counter((store["retailer"], store["country"]) for store in stores)
        reductions = {
            f"{retailer} / {country}": (prior_count, current_scopes[(retailer, country)])
            for (retailer, country), prior_count in prior_scopes.items()
            if current_scopes[(retailer, country)] < prior_count * 0.95
        }
        if reductions:
            raise ValueError(
                f"Unexplained network reduction from the {baseline_label} exceeds 5%: {reductions}. "
                "Review the source result and set ALLOW_NETWORK_REDUCTION=1 only after explicit approval."
            )
    for store in stores:
        if store["country"] not in {"Australia", "New Zealand"}:
            raise ValueError(f"Invalid country for {store['store_id']}: {store['country']}")
        if store["country"] == "Australia":
            if store["state"] not in VALID_STATES:
                raise ValueError(f"Invalid state for {store['store_id']}: {store['state']}")
            if not (-44.5 <= store["latitude"] <= -9.0 and 112.0 <= store["longitude"] <= 154.5):
                raise ValueError(f"Invalid coordinates for {store['store_id']}")
        else:
            if store["state"] not in VALID_NZ_REGIONS:
                raise ValueError(f"Invalid region for {store['store_id']}: {store['state']}")
            if not (-48.0 <= store["latitude"] <= -33.5 and 165.0 <= store["longitude"] <= 179.5):
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
        "by_country": dict(sorted(Counter(store["country"] for store in stores).items())),
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
    centre_memberships = load_centre_memberships()
    overrides = load_overrides()
    area_overrides = load_area_overrides()
    matched_memberships = set()
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
        membership_key = (store["retailer"], store["store_id"])
        membership = centre_memberships.get(membership_key)
        if membership:
            store.update(membership)
            matched_memberships.add(membership_key)
        override = overrides.get((store["retailer"], store["store_id"]))
        if override:
            store.update(override)
        area_override = area_overrides.get((store["retailer"], store["store_id"]))
        if area_override:
            store.update(area_override)
    unmatched_memberships = set(centre_memberships) - matched_memberships
    if unmatched_memberships:
        first = sorted(unmatched_memberships)[0]
        raise ValueError(f"Centre membership store not found: {first[0]} {first[1]}")
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
        "name": "Australia and New Zealand Optical Retail Network",
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
