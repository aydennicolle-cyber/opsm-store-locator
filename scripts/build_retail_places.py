#!/usr/bin/env python3
"""Build canonical retail places, store memberships, review exceptions and Bailey lookalikes."""

from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STORES_PATH = DATA / "optical_stores.csv"
CENTRES_PATH = DATA / "centres.json"
MARKETS_PATH = DATA / "sa2_market.geojson"
LINKS_PATH = DATA / "store_market_links.json"
OVERRIDES_PATH = DATA / "store_place_overrides.csv"
REVIEW_PATH = DATA / "centre_recognition_review.csv"
CONSOLIDATIONS_PATH = DATA / "place_consolidations.csv"
CANONICAL_OVERRIDES_PATH = DATA / "place_canonical_overrides.csv"
OFFICIAL_PLACES_PATH = DATA / "official_retail_places.csv"
OSM_DISCOVERY = (
    (DATA / "discovery" / "retail_places_osm_au.json", "Australia", "au"),
    (DATA / "discovery" / "retail_places_osm_nz.json", "New Zealand", "nz"),
)
PLACES_PATH = DATA / "retail_places.json"
MEMBERSHIPS_PATH = DATA / "store_place_memberships.csv"
REMAPS_PATH = DATA / "place_id_remaps.csv"
EXCEPTIONS_PATH = DATA / "place_review.csv"
LOOKALIKES_PATH = DATA / "lookalike_places.json"

NAMED_RETAILERS = {
    "OPSM", "Specsavers", "Bailey Nelson", "Oscar Wylee",
    "George & Matilda", "Eyecare Plus", "Optical Superstore",
    "1001 Optometry", "EyeQ Optometrists", "Laubman & Pank",
}
SOURCE_DISAGREEMENTS = {}
GENERIC_PLACE_WORDS = {
    "shopping", "centre", "center", "mall", "plaza", "marketplace", "town", "city",
    "the", "sc", "s", "c", "level", "lvl", "shop", "square",
}
DISTINCTIVE_OWNERS = {"westfield", "stockland", "eastgate", "vicinity", "homeco", "qic"}
KNOWN_DISTINCT_PLACE_PAIRS = {
    frozenset({"silverdale-mall", "silverdale-centre"}),
}
STREET_TYPES = {
    "rd": "Road", "road": "Road", "st": "Street", "street": "Street", "ave": "Avenue",
    "avenue": "Avenue", "dr": "Drive", "drive": "Drive", "hwy": "Highway", "highway": "Highway",
    "pde": "Parade", "parade": "Parade", "ln": "Lane", "lane": "Lane", "way": "Way",
    "blvd": "Boulevard", "boulevard": "Boulevard", "tce": "Terrace", "terrace": "Terrace",
    "cres": "Crescent", "crescent": "Crescent", "esplanade": "Esplanade", "mall": "Mall",
    "pl": "Place", "place": "Place", "walk": "Walk",
}
MEMBERSHIP_FIELDS = [
    "store_id", "retailer", "country", "state", "store_name", "place_id", "place_name",
    "location_setting", "mapping_confidence", "evidence_basis", "evidence_url", "verified_at",
    "previous_venue_id", "review_status", "usable_for_network",
]


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def apply_place_consolidations(places: list[dict], old_to_new: dict[str, str]) -> dict[str, str]:
    """Apply evidence-backed identity merges; never infer them from proximity."""
    by_id = {place["place_id"]: place for place in places}
    remaps: dict[str, str] = {}
    for row in read_csv(CONSOLIDATIONS_PATH):
        previous = row.get("previous_place_id", "").strip()
        canonical = row.get("canonical_place_id", "").strip()
        if not previous or not canonical or previous == canonical:
            raise ValueError(f"Invalid place consolidation: {row}")
        source, target = by_id.get(previous), by_id.get(canonical)
        if not source and target:
            # A broader refreshed store set can make the normaliser collapse an
            # already-reviewed alias before this explicit remap is applied.
            # Preserve the historical remap even though no second entity remains.
            remaps[previous] = canonical
            continue
        if source and not target:
            # The refreshed cluster may already contain every alias while
            # choosing a non-canonical generated name. Preserve the reviewed
            # canonical ID by renaming that single merged entity in place.
            source["place_id"] = canonical
            source["centre_id"] = canonical
            by_id.pop(previous)
            by_id[canonical] = source
            remaps[previous] = canonical
            continue
        if not source or not target:
            raise ValueError(f"Unknown place consolidation target: {previous} -> {canonical}")
        if source.get("country") != target.get("country") or source.get("location_setting") != target.get("location_setting"):
            raise ValueError(f"Incompatible place consolidation: {previous} -> {canonical}")
        for alias in [source.get("name", ""), *source.get("aliases", [])]:
            if alias and alias != target.get("name") and alias not in target["aliases"]:
                target["aliases"].append(alias)
        for field in ("official_url", "source_url", "source_date", "owner", "manager"):
            if not target.get(field) and source.get(field):
                target[field] = source[field]
        target["confidence"] = "High" if "High" in {target.get("confidence"), source.get("confidence")} else target.get("confidence")
        remaps[previous] = canonical
        by_id.pop(previous)
        places.remove(source)

    for previous, canonical in list(old_to_new.items()):
        while canonical in remaps:
            canonical = remaps[canonical]
        old_to_new[previous] = canonical
    old_to_new.update(remaps)
    return remaps


def apply_canonical_place_overrides(places: list[dict], old_to_new: dict[str, str]) -> None:
    """Apply evidenced current public names while preserving stable canonical IDs."""
    by_id = {place["place_id"]: place for place in places}
    for row in read_csv(CANONICAL_OVERRIDES_PATH):
        place_id = row.get("place_id", "").strip()
        place = by_id.get(place_id)
        if not place:
            current_name = clean_name(row.get("canonical_name", ""))
            expected_state = row.get("state", "").strip()
            override_names = {
                current_name,
                *(clean_name(alias) for alias in (row.get("aliases") or "").split("|") if clean_name(alias)),
            }
            candidates = [
                item for item in places
                if clean_name(item.get("name", "")) in override_names
                and (not expected_state or item.get("state") == expected_state)
            ]
            if not candidates:
                candidates = [
                    item for item in places
                    if (not expected_state or item.get("state") == expected_state)
                    and any(
                        name_tokens
                        and len(tokens(item.get("name", "")) & name_tokens)
                        / max(1, min(len(tokens(item.get("name", ""))), len(name_tokens))) >= 0.8
                        for name_tokens in (tokens(name) for name in override_names)
                    )
                ]
            if len(candidates) != 1:
                raise ValueError(f"Unknown canonical place override: {place_id}")
            place = candidates[0]
            generated_id = place["place_id"]
            place["place_id"] = place_id
            place["centre_id"] = place_id
            by_id.pop(generated_id)
            by_id[place_id] = place
            for previous, canonical in list(old_to_new.items()):
                if canonical == generated_id:
                    old_to_new[previous] = place_id
            old_to_new[generated_id] = place_id
        current_name = clean_name(row.get("canonical_name", ""))
        evidence_url = row.get("evidence_url", "").strip()
        verified_at = row.get("verified_at", "").strip()
        if not current_name or not evidence_url or not verified_at:
            raise ValueError(f"Incomplete canonical place override: {place_id}")
        previous_name = place.get("name", "")
        if previous_name and previous_name != current_name and previous_name not in place["aliases"]:
            place["aliases"].append(previous_name)
        for alias in (row.get("aliases") or "").split("|"):
            alias = clean_name(alias)
            if alias and alias != current_name and alias not in place["aliases"]:
                place["aliases"].append(alias)
        place["name"] = current_name
        place["canonical_name"] = current_name
        place["official_url"] = row.get("official_url", "").strip() or evidence_url
        place["source_url"] = evidence_url
        place["source_date"] = verified_at
        place["source_basis"] = row.get("reason", "").strip() or "Evidence-backed current canonical place name"
        setting = (row.get("location_setting") or "").strip()
        if setting:
            if setting not in {"Shopping Centre", "High Street", "Other"}:
                raise ValueError(f"Invalid canonical place location setting: {place_id} -> {setting}")
            place["location_setting"] = setting
            place["place_type"] = "High Street Corridor" if setting == "High Street" else setting
            if setting == "High Street":
                place["catchment_radius_m"] = 800
        for field in ("state", "locality", "postcode", "address"):
            value = row.get(field, "").strip()
            if value:
                place[field] = value
                if field == "locality":
                    place["suburb"] = value


def add_official_retail_places(places: list[dict]) -> None:
    """Promote public, authoritative centre records without assigning store membership."""
    by_id = {place["place_id"]: place for place in places}
    for row in read_csv(OFFICIAL_PLACES_PATH):
        place_id = row.get("place_id", "").strip()
        name = clean_name(row.get("canonical_name", ""))
        source_url = row.get("official_url", "").strip()
        verified_at = row.get("last_verified_at", "").strip()
        if not place_id or not name or not source_url or not verified_at:
            raise ValueError(f"Incomplete official retail place: {row}")
        try:
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid official retail place coordinates: {place_id}") from exc
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError(f"Out-of-range official retail place coordinates: {place_id}")
        aliases = [clean_name(item) for item in (row.get("aliases") or "").split("|") if clean_name(item)]
        existing = by_id.get(place_id)
        if existing:
            for alias in aliases:
                if alias != existing["name"] and alias not in existing["aliases"]:
                    existing["aliases"].append(alias)
            existing["official_url"] = source_url
            existing["source_url"] = source_url
            existing["source_date"] = verified_at
            existing["source_basis"] = row.get("source_basis", "").strip() or "Authoritative public retail-place record"
            existing["confidence"] = row.get("confidence", "High").strip() or "High"
            continue
        place = {
            "place_id": place_id,
            "centre_id": place_id,
            "name": name,
            "canonical_name": name,
            "aliases": aliases,
            "place_type": row.get("place_type", "Shopping Centre").strip() or "Shopping Centre",
            "location_setting": "Shopping Centre",
            "country": row.get("country", "").strip(),
            "state": row.get("state", "").strip(),
            "locality": row.get("locality", "").strip(),
            "suburb": row.get("locality", "").strip(),
            "postcode": row.get("postcode", "").strip(),
            "address": row.get("address", "").strip(),
            "latitude": latitude,
            "longitude": longitude,
            "owner": "",
            "manager": "",
            "centre_type": "",
            "gla_sqm": "",
            "annual_visits": "",
            "trade_area_population": "",
            "anchors": [],
            "tenancy_count": "",
            "redevelopment_activity": "",
            "official_url": source_url,
            "source_url": source_url,
            "coordinate_source_url": row.get("coordinate_source_url", "").strip(),
            "source_date": verified_at,
            "status": row.get("status", "Active").strip() or "Active",
            "confidence": row.get("confidence", "High").strip() or "High",
            "source_basis": row.get("source_basis", "").strip() or "Authoritative public retail-place record",
            "retailers": [],
            "optical_store_count": 0,
            "old_centre_ids": [],
        }
        places.append(place)
        by_id[place_id] = place


def slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", value))


def clean_name(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value or "")).strip(" ,-–")
    value = re.sub(r"\bS/?C\b", "Shopping Centre", value, flags=re.I)
    value = re.sub(r"\bShopping Center\b", "Shopping Centre", value, flags=re.I)
    return value


def tokens(value: str) -> set[str]:
    return {
        item for item in re.findall(r"[a-z0-9]+", slug(value).replace("-", " "))
        if item not in GENERIC_PLACE_WORDS and len(item) > 1
    }


def haversine(first: dict, second: dict) -> float:
    radius = 6371.0088
    lat1, lat2 = math.radians(float(first["latitude"])), math.radians(float(second["latitude"]))
    delta_lat = math.radians(float(second["latitude"]) - float(first["latitude"]))
    delta_lon = math.radians(float(second["longitude"]) - float(first["longitude"]))
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def country_code(country: str) -> str:
    return "nz" if country == "New Zealand" else "au"


def centre_place_id(country: str, state: str, name: str) -> str:
    return f"place-{country_code(country)}-{slug(state)}-{slug(name)}"


def corridor_place_id(country: str, state: str, locality: str, street: str) -> str:
    return f"corridor-{country_code(country)}-{slug(state)}-{slug(locality)}-{slug(street)}"


def place_name_score(name: str) -> tuple[int, int, int]:
    lowered = name.lower()
    return (
        3 * int("westfield" in lowered or "stockland" in lowered)
        + 2 * int(any(word in lowered for word in ("centre", "mall", "plaza", "marketplace")))
        - 3 * int(bool(re.search(r"\b(?:shop|level|lvl)\s*\w+", lowered)))
        - 2 * len(re.findall(r"\d", lowered)),
        -len(name.split()),
        -len(name),
    )


def should_merge(first: dict, second: dict) -> bool:
    if first.get("country") != second.get("country") or first.get("state") != second.get("state"):
        return False
    distance = haversine(first, second)
    if slug(clean_name(first["name"])) == slug(clean_name(second["name"])) and distance <= 2.0:
        return True
    if distance > 0.125:
        return False
    left, right = tokens(first["name"]), tokens(second["name"])
    if not left or not right:
        return distance <= 0.025
    owner_left, owner_right = left & DISTINCTIVE_OWNERS, right & DISTINCTIVE_OWNERS
    if owner_left and owner_right and owner_left != owner_right:
        return False
    overlap = len(left & right) / max(1, min(len(left), len(right)))
    return overlap >= 0.6 or distance <= 0.025


def cluster_centres(centres: list[dict]) -> list[list[dict]]:
    parent = list(range(len(centres)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for left in range(len(centres)):
        for right in range(left + 1, len(centres)):
            if should_merge(centres[left], centres[right]):
                union(left, right)
    grouped: dict[int, list[dict]] = defaultdict(list)
    for index, centre in enumerate(centres):
        grouped[find(index)].append(centre)
    return list(grouped.values())


def merge_centre_cluster(cluster: list[dict]) -> dict:
    preferred = max(cluster, key=lambda item: place_name_score(clean_name(item["name"])))
    name = clean_name(preferred["name"])
    place_id = centre_place_id(preferred["country"], preferred["state"], name)
    aliases = sorted({clean_name(item["name"]) for item in cluster if clean_name(item["name"]) != name})
    retailers = sorted({brand for item in cluster for brand in item.get("retailers", [])})
    def first_value(field: str):
        return next((item.get(field) for item in cluster if item.get(field) not in (None, "", [])), "")
    return {
        "place_id": place_id,
        "centre_id": place_id,
        "name": name,
        "canonical_name": name,
        "aliases": aliases,
        "place_type": "Shopping Centre",
        "location_setting": "Shopping Centre",
        "country": preferred.get("country", "Australia"),
        "state": first_value("state"),
        "locality": first_value("suburb"),
        "suburb": first_value("suburb"),
        "postcode": "",
        "address": "",
        "latitude": round(sum(float(item["latitude"]) for item in cluster) / len(cluster), 6),
        "longitude": round(sum(float(item["longitude"]) for item in cluster) / len(cluster), 6),
        "owner": first_value("owner"),
        "manager": first_value("manager"),
        "centre_type": first_value("centre_type"),
        "gla_sqm": first_value("gla_sqm"),
        "annual_visits": first_value("annual_visits"),
        "trade_area_population": first_value("trade_area_population"),
        "anchors": first_value("anchors") or [],
        "tenancy_count": first_value("tenancy_count"),
        "redevelopment_activity": first_value("redevelopment_activity"),
        "official_url": first_value("public_url"),
        "source_url": first_value("public_url"),
        "source_date": first_value("metrics_date"),
        "status": "Active",
        "confidence": "High" if any(item.get("confidence") == "High" for item in cluster) else "Medium",
        "source_basis": "Canonical centre consolidated from public store and place evidence",
        "retailers": retailers,
        "optical_store_count": sum(int(item.get("optical_store_count") or 0) for item in cluster),
        "old_centre_ids": sorted({item["centre_id"] for item in cluster}),
    }


def point_from_osm(element: dict) -> tuple[float | None, float | None]:
    point = element.get("center") or element
    try:
        return float(point["lat"]), float(point["lon"])
    except (KeyError, TypeError, ValueError):
        return None, None


def add_broad_osm_centres(places: list[dict]) -> None:
    for path, country, code in OSM_DISCOVERY:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for element in payload.get("elements", []):
            tags = element.get("tags", {})
            website = tags.get("website") or tags.get("contact:website") or ""
            name = clean_name(tags.get("name", ""))
            latitude, longitude = point_from_osm(element)
            if tags.get("shop") != "mall" or not website or not name or latitude is None:
                continue
            candidate = {"latitude": latitude, "longitude": longitude, "country": country, "state": tags.get("addr:state", "")}
            duplicate = next(
                (
                    place for place in places
                    if place["place_type"] == "Shopping Centre"
                    and place["country"] == country
                    and (
                        (
                            slug(clean_name(name)) == slug(clean_name(place["name"]))
                            and haversine(candidate, place) <= 1.0
                        )
                        or (
                            haversine(candidate, place) <= 0.2
                            and (tokens(name) & tokens(place["name"]))
                        )
                    )
                ),
                None,
            )
            if duplicate:
                if website and not duplicate.get("official_url"):
                    duplicate["official_url"] = website
                    duplicate["source_url"] = website
                if name != duplicate["name"] and name not in duplicate["aliases"]:
                    duplicate["aliases"].append(name)
                continue
            state = tags.get("addr:state", "")
            place_id = centre_place_id(country, state or "unknown", name)
            if any(place["place_id"] == place_id for place in places):
                place_id += f"-{element['type']}-{element['id']}"
            places.append(
                {
                    "place_id": place_id,
                    "centre_id": place_id,
                    "name": name,
                    "canonical_name": name,
                    "aliases": [],
                    "place_type": "Shopping Centre",
                    "location_setting": "Shopping Centre",
                    "country": country,
                    "state": state,
                    "locality": tags.get("addr:suburb") or tags.get("addr:city") or tags.get("addr:town", ""),
                    "suburb": tags.get("addr:suburb") or tags.get("addr:city") or tags.get("addr:town", ""),
                    "postcode": tags.get("addr:postcode", ""),
                    "address": " ".join(filter(None, [tags.get("addr:housenumber"), tags.get("addr:street")])),
                    "latitude": latitude,
                    "longitude": longitude,
                    "owner": tags.get("owner", ""),
                    "manager": tags.get("operator", ""),
                    "centre_type": "",
                    "gla_sqm": "",
                    "annual_visits": "",
                    "trade_area_population": "",
                    "anchors": [],
                    "tenancy_count": "",
                    "redevelopment_activity": "",
                    "official_url": website,
                    "source_url": website,
                    "source_date": payload.get("fetched_at", "")[:10],
                    "status": "Active",
                    "confidence": "Medium",
                    "source_basis": "Official website corroborates an OpenStreetMap shopping-centre feature",
                    "retailers": [],
                    "optical_store_count": 0,
                    "old_centre_ids": [],
                }
            )


def parse_street(address: str) -> str:
    matches = re.findall(
        r"\b([A-Za-zÀ-ž][A-Za-zÀ-ž' .&-]{1,55}?)\s+(Road|Rd|Street|St|Avenue|Ave|Drive|Dr|Highway|Hwy|Parade|Pde|Lane|Ln|Way|Boulevard|Blvd|Terrace|Tce|Crescent|Cres|Esplanade|Mall|Place|Pl|Walk)\b",
        str(address),
        flags=re.I,
    )
    if not matches:
        return ""
    name, street_type = matches[-1]
    name = re.sub(r"^(?:shop|unit|suite|level|lvl)\s*[\w./-]+\s*[-,]?\s*", "", name, flags=re.I)
    name = re.sub(r"^\d+[A-Za-z]?(?:\s*[-/]\s*\d+[A-Za-z]?)?\s+", "", name).strip(" ,-.")
    canonical_type = STREET_TYPES[street_type.lower()]
    return clean_name(f"{name} {canonical_type}") if name else ""


def create_place_from_override(store: dict, override: dict) -> dict:
    setting = override["location_setting"]
    name = clean_name(override["canonical_name"])
    place_id = (
        centre_place_id(store["country"], store["state"], name)
        if setting == "Shopping Centre"
        else corridor_place_id(store["country"], store["state"], store["suburb"], name)
    )
    return {
        "place_id": place_id,
        "centre_id": place_id,
        "name": name,
        "canonical_name": name,
        "aliases": [],
        "place_type": override["place_type"],
        "location_setting": setting,
        "country": store["country"],
        "state": store["state"],
        "locality": store["suburb"],
        "suburb": store["suburb"],
        "postcode": store["postcode"],
        "address": store["full_address"],
        "latitude": float(store["latitude"]),
        "longitude": float(store["longitude"]),
        "owner": override.get("owner", ""),
        "manager": override.get("manager", ""),
        "centre_type": "",
        "gla_sqm": "",
        "annual_visits": "",
        "trade_area_population": "",
        "anchors": [],
        "tenancy_count": "",
        "redevelopment_activity": "",
        "official_url": override.get("place_official_url") or override["official_url"],
        "source_url": override.get("place_official_url") or override["official_url"],
        "source_date": override["source_date"],
        "status": "Active",
        "confidence": override["confidence"],
        "source_basis": override["evidence_basis"],
        "retailers": [],
        "optical_store_count": 0,
        "old_centre_ids": [],
    }


def promote_store_named_centres(
    stores: list[dict], places: list[dict], old_to_new: dict[str, str]
) -> None:
    """Promote explicit centre names from official retailer address evidence.

    This uses named-address evidence only. Coordinates locate the resulting
    record but never establish membership by proximity.
    """
    for store in sorted(stores, key=lambda row: (row["country"], row["state"], row["suburb"], row["name"])):
        venue_id = store.get("venue_id", "").strip()
        venue_name = clean_name(store.get("venue_name", ""))
        if store.get("location_type") != "Shopping Centre" or not venue_id or not venue_name:
            continue
        if venue_id in old_to_new:
            continue
        normalized_name = slug(venue_name)
        normalized_locality = slug(store.get("suburb", ""))
        existing = next(
            (
                place for place in places
                if place.get("location_setting") == "Shopping Centre"
                and place.get("country") == store["country"]
                and place.get("state") == store["state"]
                and normalized_name in {
                    slug(place.get("name", "")),
                    *(slug(alias) for alias in place.get("aliases", [])),
                }
                and (
                    not normalized_locality
                    or not slug(place.get("locality") or place.get("suburb", ""))
                    or slug(place.get("locality") or place.get("suburb", "")) == normalized_locality
                )
            ),
            None,
        )
        if existing:
            if venue_id not in existing["old_centre_ids"]:
                existing["old_centre_ids"].append(venue_id)
            old_to_new[venue_id] = existing["place_id"]
            continue

        place_id = centre_place_id(store["country"], store["state"], venue_name)
        collision = next((place for place in places if place["place_id"] == place_id), None)
        if collision:
            place_id = centre_place_id(
                store["country"], store["state"], f"{venue_name} {store.get('suburb', '')}"
            )
        place = {
            "place_id": place_id,
            "centre_id": place_id,
            "name": venue_name,
            "canonical_name": venue_name,
            "aliases": [],
            "place_type": "Shopping Centre",
            "location_setting": "Shopping Centre",
            "country": store["country"],
            "state": store["state"],
            "locality": store.get("suburb", ""),
            "suburb": store.get("suburb", ""),
            "postcode": store.get("postcode", ""),
            "address": store.get("full_address", ""),
            "latitude": float(store["latitude"]),
            "longitude": float(store["longitude"]),
            "owner": "",
            "manager": "",
            "centre_type": "",
            "gla_sqm": "",
            "annual_visits": "",
            "trade_area_population": "",
            "anchors": [],
            "tenancy_count": "",
            "redevelopment_activity": "",
            "official_url": store.get("official_url", ""),
            "source_url": store.get("source_url") or store.get("official_url", ""),
            "source_date": store.get("fetched_at", "")[:10],
            "status": "Active",
            "confidence": "High",
            "source_basis": "Official retailer locator explicitly names this shopping centre in the store address",
            "retailers": [],
            "optical_store_count": 0,
            "old_centre_ids": [venue_id],
        }
        places.append(place)
        old_to_new[venue_id] = place_id


def main() -> None:
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stores = read_csv(STORES_PATH)
    centres_payload = json.loads(CENTRES_PATH.read_text(encoding="utf-8"))
    current_centres = centres_payload.get("centres", [])
    places = [merge_centre_cluster(cluster) for cluster in cluster_centres(current_centres)]
    place_by_id = {place["place_id"]: place for place in places}
    old_to_new = {
        old_id: place["place_id"]
        for place in places
        for old_id in place["old_centre_ids"]
    }
    overrides = {row["store_id"]: row for row in read_csv(OVERRIDES_PATH)}
    high_reviews = {
        row["store_id"]: row
        for row in read_csv(REVIEW_PATH)
        if row.get("priority") == "High" and row.get("candidate_venue_id")
    }

    for store_id, override in overrides.items():
        store = next((item for item in stores if item["store_id"] == store_id), None)
        if not store:
            raise ValueError(f"Unknown store-place override: {store_id}")
        proposed = create_place_from_override(store, override)
        existing = next(
            (
                place for place in places
                if place["location_setting"] == proposed["location_setting"]
                and place["country"] == proposed["country"]
                and frozenset({slug(clean_name(place["name"])), slug(clean_name(proposed["name"]))})
                not in KNOWN_DISTINCT_PLACE_PAIRS
                and (
                    place["place_id"] == proposed["place_id"]
                    or (
                        haversine(place, proposed) <= 0.3
                        and (tokens(place["name"]) & tokens(proposed["name"]))
                    )
                )
            ),
            None,
        )
        if existing:
            if proposed["name"] != existing["name"] and proposed["name"] not in existing["aliases"]:
                existing["aliases"].append(proposed["name"])
            if proposed["confidence"] == "High":
                existing["confidence"] = "High"
                existing["official_url"] = proposed["official_url"] or existing["official_url"]
                existing["source_url"] = proposed["source_url"] or existing["source_url"]
                existing["source_basis"] = proposed["source_basis"]
            existing["owner"] = proposed["owner"] or existing["owner"]
            existing["manager"] = proposed["manager"] or existing["manager"]
            override["place_id"] = existing["place_id"]
        else:
            places.append(proposed)
            place_by_id[proposed["place_id"]] = proposed
            override["place_id"] = proposed["place_id"]

    add_broad_osm_centres(places)
    add_official_retail_places(places)
    consolidation_remaps = apply_place_consolidations(places, old_to_new)
    apply_canonical_place_overrides(places, old_to_new)
    promote_store_named_centres(stores, places, old_to_new)
    for override in overrides.values():
        if override.get("place_id") in consolidation_remaps:
            override["place_id"] = consolidation_remaps[override["place_id"]]
    place_by_id = {place["place_id"]: place for place in places}
    preliminary = []
    exceptions = []
    for store in stores:
        named = store["retailer"] in NAMED_RETAILERS
        usable = named or (
            bool(store.get("suburb") and store.get("postcode"))
            and store.get("full_address") not in {"Australia", "New Zealand"}
        )
        setting = "Uncertain"
        place_id = ""
        confidence = "Uncertain"
        basis = "Location setting needs consultant review"
        evidence_url = store.get("official_url") or store.get("source_url", "")
        verified_at = store.get("fetched_at", "")[:10]
        override = overrides.get(store["store_id"])
        if override:
            setting = override["location_setting"]
            place_id = override["place_id"]
            confidence = override["confidence"]
            basis = override["evidence_basis"]
            evidence_url = override["official_url"]
            verified_at = override["source_date"]
        elif store["store_id"] in SOURCE_DISAGREEMENTS:
            disagreement = SOURCE_DISAGREEMENTS[store["store_id"]]
            setting, confidence, basis = "Uncertain", "Uncertain", disagreement["reason"]
            evidence_url = disagreement["url"]
            verified_at = disagreement["date"]
        elif store.get("venue_id") and store["venue_id"] in old_to_new:
            place_id = old_to_new[store["venue_id"]]
            setting = place_by_id[place_id]["location_setting"]
            confidence = "High" if store.get("classification_confidence") == "High" else "Medium"
            basis = "Canonicalised from the store's named retail-place evidence"
        elif store["store_id"] in high_reviews and high_reviews[store["store_id"]]["candidate_venue_id"] in old_to_new:
            review = high_reviews[store["store_id"]]
            place_id = old_to_new[review["candidate_venue_id"]]
            setting = place_by_id[place_id]["location_setting"]
            confidence = "Medium"
            basis = review["evidence"]
        elif store.get("location_type") == "Other":
            setting, confidence, basis = "Other", store.get("classification_confidence") or "Medium", store["classification_basis"]
        elif store.get("location_type") == "Main Street / Street-front":
            setting, confidence, basis = "High Street", "Medium", "Numbered street address without a corroborated centre match"
        elif store.get("location_type") == "Unclassified" and parse_street(store.get("full_address", "")):
            setting, confidence, basis = "High Street", "Medium", "Best-judgement street-address classification; no centre evidence found"
        elif store.get("location_type") == "Shopping Centre":
            setting, confidence, basis = "Uncertain", "Uncertain", "Store appears centre-based but no defensible canonical place match was found"

        preliminary.append(
            {
                "store": store,
                "setting": setting,
                "place_id": place_id,
                "confidence": confidence,
                "basis": basis,
                "evidence_url": evidence_url,
                "verified_at": verified_at,
                "usable": usable,
            }
        )

    corridor_groups: dict[str, list[dict]] = defaultdict(list)
    for item in preliminary:
        if item["setting"] != "High Street" or item["place_id"]:
            continue
        store = item["store"]
        street = parse_street(store.get("full_address", "")) or f"{store.get('suburb') or store.get('state')} Retail Core"
        base_id = corridor_place_id(store["country"], store["state"], store.get("suburb") or store["state"], street)
        item["street"] = street
        corridor_groups[base_id].append(item)

    for base_id, items in corridor_groups.items():
        clusters: list[list[dict]] = []
        for item in sorted(items, key=lambda value: (float(value["store"]["latitude"]), float(value["store"]["longitude"]))):
            target = next(
                (
                    cluster for cluster in clusters
                    if min(haversine(item["store"], member["store"]) for member in cluster) <= 1.0
                ),
                None,
            )
            (target if target is not None else clusters.append([]) or clusters[-1]).append(item)
        for index, cluster in enumerate(clusters, start=1):
            place_id = base_id if len(clusters) == 1 else f"{base_id}-{index}"
            if place_id in place_by_id:
                for entry in cluster:
                    entry["place_id"] = place_id
                continue
            first = cluster[0]
            stores_in_cluster = [entry["store"] for entry in cluster]
            name = first["street"]
            place = {
                "place_id": place_id,
                "centre_id": place_id,
                "name": name,
                "canonical_name": name,
                "aliases": [],
                "place_type": "High Street Corridor",
                "location_setting": "High Street",
                "country": first["store"]["country"],
                "state": first["store"]["state"],
                "locality": first["store"].get("suburb", ""),
                "suburb": first["store"].get("suburb", ""),
                "postcode": first["store"].get("postcode", ""),
                "address": name,
                "latitude": round(sum(float(store["latitude"]) for store in stores_in_cluster) / len(stores_in_cluster), 6),
                "longitude": round(sum(float(store["longitude"]) for store in stores_in_cluster) / len(stores_in_cluster), 6),
                "owner": "",
                "manager": "",
                "centre_type": "",
                "gla_sqm": "",
                "annual_visits": "",
                "trade_area_population": "",
                "anchors": [],
                "tenancy_count": "",
                "redevelopment_activity": "",
                "official_url": "",
                "source_url": first["evidence_url"],
                "source_date": first["verified_at"],
                "status": "Active",
                "confidence": "Medium",
                "source_basis": "Corridor derived from mapped street-front optical stores on the same street and locality",
                "retailers": [],
                "optical_store_count": 0,
                "old_centre_ids": [],
                "catchment_radius_m": 800,
            }
            places.append(place)
            place_by_id[place_id] = place
            for entry in cluster:
                entry["place_id"] = place_id

    memberships = []
    for item in preliminary:
        store = item["store"]
        place_id = item["place_id"]
        place = place_by_id.get(place_id)
        review_status = "Accepted" if item["confidence"] in {"High", "Medium"} and (place_id or item["setting"] == "Other") else "Needs review"
        if review_status == "Needs review" and store["retailer"] in NAMED_RETAILERS:
            exceptions.append(
                {
                    "priority": "High" if item["setting"] == "Uncertain" else "Medium",
                    "store_id": store["store_id"],
                    "retailer": store["retailer"],
                    "store_name": store["name"],
                    "country": store["country"],
                    "state": store["state"],
                    "address": store["full_address"],
                    "current_setting": item["setting"],
                    "candidate_place_id": place_id,
                    "reason": item["basis"],
                    "evidence_url": item["evidence_url"],
                    "review_status": "Pending",
                }
            )
        memberships.append(
            {
                "store_id": store["store_id"],
                "retailer": store["retailer"],
                "country": store["country"],
                "state": store["state"],
                "store_name": store["name"],
                "place_id": place_id,
                "place_name": place["name"] if place else "",
                "location_setting": item["setting"],
                "mapping_confidence": item["confidence"],
                "evidence_basis": item["basis"],
                "evidence_url": item["evidence_url"],
                "verified_at": item["verified_at"],
                "previous_venue_id": store.get("venue_id", ""),
                "review_status": review_status,
                "usable_for_network": str(item["usable"]).lower(),
            }
        )

    for place in places:
        members = [row for row in memberships if row["place_id"] == place["place_id"]]
        place["retailers"] = sorted({row["retailer"] for row in members})
        place["optical_store_count"] = len(members)
        place["has_bailey"] = any(row["retailer"] == "Bailey Nelson" for row in members)
        place["mapping_confidence"] = (
            "High" if members and all(row["mapping_confidence"] == "High" for row in members)
            else "Medium" if members or place["confidence"] == "Medium" else place["confidence"]
        )
        place["certification_status"] = "Verified" if place["confidence"] == "High" else "Best available"
        place["evidence_tier"] = "Official" if place["official_url"] else "Derived"
        place.pop("old_centre_ids", None)

    places.sort(key=lambda item: (item["country"], item["state"], item["place_type"], item["name"]))
    with MEMBERSHIPS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MEMBERSHIP_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(memberships)
    with REMAPS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["previous_place_id", "canonical_place_id", "reason"], lineterminator="\n")
        writer.writeheader()
        for previous, canonical in sorted(old_to_new.items()):
            reason = "Evidence-backed place identity consolidation" if previous in consolidation_remaps else "Canonical centre consolidation"
            writer.writerow({"previous_place_id": previous, "canonical_place_id": canonical, "reason": reason})
    with EXCEPTIONS_PATH.open("w", newline="", encoding="utf-8") as handle:
        fields = ["priority", "store_id", "retailer", "store_name", "country", "state", "address", "current_setting", "candidate_place_id", "reason", "evidence_url", "review_status"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(exceptions)

    payload = {
        "metadata": {
            "generated_at": generated_at,
            "place_count": len(places),
            "centre_count": sum(place["location_setting"] == "Shopping Centre" for place in places),
            "corridor_count": sum(place["location_setting"] == "High Street" for place in places),
            "membership_count": len(memberships),
            "named_network_review_count": len(exceptions),
            "coverage_note": "Canonical places use official public evidence where available and best-available mappings with visible confidence elsewhere.",
        },
        "places": places,
    }
    PLACES_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    build_lookalikes(places, memberships, stores, generated_at)
    print(
        f"Built {len(places)} canonical places ({payload['metadata']['centre_count']} centres, "
        f"{payload['metadata']['corridor_count']} corridors), {len(memberships)} memberships, "
        f"{len(exceptions)} named-network exceptions"
    )


def number(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def point_in_ring(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        if ((current[1] > latitude) != (previous[1] > latitude)) and (
            longitude < (previous[0] - current[0]) * (latitude - current[1]) / ((previous[1] - current[1]) or 1e-12) + current[0]
        ):
            inside = not inside
        previous = current
    return inside


def point_in_geometry(longitude: float, latitude: float, geometry: dict) -> bool:
    if geometry["type"] == "Polygon":
        return point_in_ring(longitude, latitude, geometry["coordinates"][0])
    if geometry["type"] == "MultiPolygon":
        return any(point_in_ring(longitude, latitude, polygon[0]) for polygon in geometry["coordinates"])
    return False


def market_for_point(point: dict, markets: list[dict]) -> dict | None:
    if point.get("country") != "Australia":
        return None
    longitude, latitude = float(point["longitude"]), float(point["latitude"])
    return next((feature["properties"] for feature in markets if point_in_geometry(longitude, latitude, feature["geometry"])), None)


def closeness(value: float | None, baseline: list[float]) -> float | None:
    if value is None or not baseline:
        return None
    ordered = sorted(baseline + [value])
    candidate_pct = ordered.index(value) / max(1, len(ordered) - 1) * 100
    baseline_pcts = [sorted(baseline).index(item) / max(1, len(baseline) - 1) * 100 for item in baseline]
    return max(0.0, 100.0 - abs(candidate_pct - median(baseline_pcts)) * 2)


def average_available(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return sum(present) / len(present) if present else None


def build_lookalikes(places: list[dict], memberships: list[dict], stores: list[dict], generated_at: str) -> None:
    markets = json.loads(MARKETS_PATH.read_text(encoding="utf-8")).get("features", [])
    membership_by_store = {row["store_id"]: row for row in memberships}
    stores_by_id = {row["store_id"]: row for row in stores}
    for place in places:
        place["market"] = market_for_point(place, markets)
    benchmark: dict[tuple[str, str], list[dict]] = defaultdict(list)
    bailey_benchmarks: list[dict] = []
    for membership in memberships:
        if membership["retailer"] != "Bailey Nelson" or not membership["place_id"]:
            continue
        place = next((item for item in places if item["place_id"] == membership["place_id"]), None)
        if place:
            benchmark[(place["country"], place["location_setting"])].append(place)
            bailey_benchmarks.append(
                {
                    "store_id": membership["store_id"],
                    "store_name": stores_by_id[membership["store_id"]]["name"],
                    "place_id": place["place_id"],
                    "country": place["country"],
                    "location_setting": place["location_setting"],
                    "market_features": {
                        field: number((place.get("market") or {}).get(field))
                        for field in (
                            "population_2025",
                            "population_growth_2021_2025_pct",
                            "age_45_plus_pct_2021",
                            "median_household_income_weekly_2021",
                        )
                    },
                }
            )
    bailey_stores = [stores_by_id[row["store_id"]] for row in memberships if row["retailer"] == "Bailey Nelson"]
    fields = ("population_2025", "population_growth_2021_2025_pct", "age_45_plus_pct_2021", "median_household_income_weekly_2021")
    rankings: dict[str, list[dict]] = defaultdict(list)
    for place in places:
        if place["has_bailey"] or place["location_setting"] not in {"Shopping Centre", "High Street"}:
            continue
        base = benchmark.get((place["country"], place["location_setting"]), [])
        baseline_values = {
            field: [
                number((item.get("market") or {}).get(field))
                for item in base
                if number((item.get("market") or {}).get(field)) is not None
            ]
            for field in fields
        }
        footprint = average_available([
            closeness(number((place.get("market") or {}).get(field)), baseline_values[field]) for field in fields
        ])
        nearest_bailey = min((haversine(place, store) for store in bailey_stores if store["country"] == place["country"]), default=None)
        whitespace = min(100.0, nearest_bailey * 5) if nearest_bailey is not None else None
        competitors = [brand for brand in place["retailers"] if brand != "Bailey Nelson"]
        optical_validation = min(100.0, len(set(competitors)) * 22 + int(place["optical_store_count"]) * 7) if competitors else None
        if place["location_setting"] == "Shopping Centre":
            context = average_available([
                min(100.0, number(place.get("gla_sqm")) / 1800) if number(place.get("gla_sqm")) is not None else None,
                min(100.0, number(place.get("annual_visits")) / 200000) if number(place.get("annual_visits")) is not None else None,
                min(100.0, number(place.get("tenancy_count")) / 2) if number(place.get("tenancy_count")) is not None else None,
            ])
        else:
            context = min(100.0, int(place["optical_store_count"]) * 20) if place["optical_store_count"] else None
        components = {
            "bailey_footprint_similarity": round(footprint) if footprint is not None else None,
            "bailey_whitespace": round(whitespace) if whitespace is not None else None,
            "optical_market_validation": round(optical_validation) if optical_validation is not None else None,
            "accessibility_retail_context": round(context) if context is not None else None,
        }
        weights = {"bailey_footprint_similarity": 40, "bailey_whitespace": 30, "optical_market_validation": 20, "accessibility_retail_context": 10}
        available = [key for key, value in components.items() if value is not None]
        completeness = sum(weights[key] for key in available)
        score = round(sum(components[key] * weights[key] for key in available) / completeness) if completeness else None
        key = f"{country_code(place['country'])}-{slug(place['location_setting'])}"
        rankings[key].append(
            {
                "place_id": place["place_id"],
                "name": place["name"],
                "country": place["country"],
                "state": place["state"],
                "locality": place["locality"],
                "location_setting": place["location_setting"],
                "score": score,
                "screening_completeness": completeness,
                "components": components,
                "market_features": {
                    field: number((place.get("market") or {}).get(field)) for field in fields
                },
                "nearest_bailey_km": round(nearest_bailey, 1) if nearest_bailey is not None else None,
                "optical_store_count": place["optical_store_count"],
                "retailers": place["retailers"],
                "evidence_url": place["official_url"] or place["source_url"],
            }
        )
    for rows in rankings.values():
        rows.sort(key=lambda row: (row["screening_completeness"] < 60, -(row["score"] or -1), row["name"]))
        for index, row in enumerate(rows, start=1):
            row["rank"] = index
    LOOKALIKES_PATH.write_text(
        json.dumps(
            {
                "metadata": {
                    "generated_at": generated_at,
                    "benchmark": "All mapped Bailey Nelson stores, separated by country and location setting",
                    "method": "Transparent lookalike screening rank; not a probability of store success",
                    "weights": {"footprint_similarity": 40, "whitespace": 30, "optical_validation": 20, "accessibility_retail_context": 10},
                },
                "bailey_benchmarks": bailey_benchmarks,
                "rankings": rankings,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
