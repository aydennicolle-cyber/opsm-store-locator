#!/usr/bin/env python3
"""Build validated public property and leasing intelligence for canonical retail places."""

from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

GROUPS_PATH = DATA / "property_groups.csv"
ALIASES_PATH = DATA / "property_group_aliases.csv"
GROUP_REMAPS_PATH = DATA / "property_group_id_remaps.csv"
DOMAIN_RULES_PATH = DATA / "property_group_domain_rules.csv"
PORTFOLIO_ASSETS_PATH = DATA / "property_portfolio_assets.csv"
PORTFOLIO_SCOPES_PATH = DATA / "property_portfolio_scopes.csv"
RELATIONSHIPS_PATH = DATA / "asset_relationships.csv"
ATTRIBUTES_PATH = DATA / "property_attributes.csv"
RESEARCH_PATH = DATA / "property_research_status.csv"
PLACES_PATH = DATA / "retail_places.json"
MEMBERSHIPS_PATH = DATA / "store_place_memberships.csv"
STORES_PATH = DATA / "optical_stores.csv"
MARKETS_PATH = DATA / "sa2_market.geojson"
OUTPUT_PATH = DATA / "property_intelligence.json"
REVIEW_PATH = DATA / "property_relationship_review.csv"
RESEARCH_QUEUE_PATH = DATA / "property_research_queue.csv"

ROLES = {
    "OWNER", "CO_OWNER", "MANAGER", "OPERATOR", "LEASING_CONTROLLER",
    "EXTERNAL_LEASING_AGENT",
}
OWNER_ROLES = {"OWNER", "CO_OWNER"}
PROPERTY_GROUP_ROLES = {"OWNER", "CO_OWNER", "MANAGER", "OPERATOR"}
CONFIDENCE = {"High", "Medium", "Low"}
RELATIONSHIP_STATUS = {"ACTIVE", "DISPUTED", "RETIRED"}
RESEARCH_STATUS = {"Not researched", "Partial", "Verified", "Verified unknown", "Conflict"}
CENTRE_CLASSES = {
    "Super Regional", "Regional", "Sub-regional", "Neighbourhood", "CBD / Mixed-use",
    "Outlet", "Large Format", "Other", "Unknown",
}
CLASS_METHODS = {"Confirmed", "Inferred", "Manual"}
GROUP_TYPES = {
    "PROPERTY_COMPANY", "INVESTMENT_VEHICLE", "ASSET_MANAGER", "CENTRE_OPERATOR",
    "EXTERNAL_AGENCY", "PRIVATE_LANDLORD", "OTHER",
}
ACTIVE_GROUP_STATUS = {"Active", "Inactive"}
REVIEW_FIELDS = ["review_id", "place_id", "candidate_group_id", "reason", "source_url", "status"]
RESEARCH_QUEUE_FIELDS = [
    "priority", "place_id", "name", "country", "state", "locality", "research_status",
    "centre_class", "bailey_store_count", "mapped_named_brands", "mapped_optical_stores",
    "official_url", "reason",
]


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"(^-|-$)", "", re.sub(r"[^a-z0-9]+", "-", value))


def normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower())


def parse_date(value: str, field: str, required: bool = False) -> str:
    value = str(value or "").strip()
    if not value:
        if required:
            raise ValueError(f"{field} is required")
        return ""
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must use YYYY-MM-DD: {value}") from error
    return value


def require_url(value: str, field: str) -> str:
    value = str(value or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field} must be a public HTTP(S) URL: {value}")
    return value


def host_for(value: str) -> str:
    try:
        return (urlparse(str(value or "")).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def active_relationship(row: dict) -> bool:
    if row.get("status") != "ACTIVE":
        return False
    today = date.today().isoformat()
    return (not row.get("valid_from") or row["valid_from"] <= today) and (
        not row.get("valid_to") or row["valid_to"] >= today
    )


def haversine(first: dict, second: dict) -> float:
    radius = 6371.0088
    lat1 = math.radians(float(first["latitude"]))
    lat2 = math.radians(float(second["latitude"]))
    dlat = math.radians(float(second["latitude"]) - float(first["latitude"]))
    dlon = math.radians(float(second["longitude"]) - float(first["longitude"]))
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def point_in_ring(longitude: float, latitude: float, ring: list) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous[:2]
        x2, y2 = current[:2]
        if ((y1 > latitude) != (y2 > latitude)) and (
            longitude < (x2 - x1) * (latitude - y1) / ((y2 - y1) or 1e-12) + x1
        ):
            inside = not inside
        previous = current
    return inside


def point_in_geometry(longitude: float, latitude: float, geometry: dict) -> bool:
    coordinates = geometry.get("coordinates", [])
    polygons = [coordinates] if geometry.get("type") == "Polygon" else coordinates
    for polygon in polygons:
        if polygon and point_in_ring(longitude, latitude, polygon[0]):
            if not any(point_in_ring(longitude, latitude, hole) for hole in polygon[1:]):
                return True
    return False


def load_groups() -> tuple[list[dict], dict[str, dict], dict[str, str], list[dict]]:
    raw_groups = read_csv(GROUPS_PATH)
    groups: list[dict] = []
    by_id: dict[str, dict] = {}
    aliases_by_group: dict[str, list[str]] = defaultdict(list)
    alias_owner: dict[str, str] = {}

    for row in raw_groups:
        group_id = row.get("group_id", "").strip()
        if not group_id or group_id in by_id:
            raise ValueError(f"Missing or duplicate group_id: {group_id}")
        if row.get("group_type") not in GROUP_TYPES:
            raise ValueError(f"Invalid group_type for {group_id}: {row.get('group_type')}")
        if row.get("status") not in ACTIVE_GROUP_STATUS:
            raise ValueError(f"Invalid group status for {group_id}: {row.get('status')}")
        if row.get("confidence") not in CONFIDENCE:
            raise ValueError(f"Invalid group confidence for {group_id}: {row.get('confidence')}")
        require_url(row.get("official_url", ""), f"{group_id}.official_url")
        require_url(row.get("source_url", ""), f"{group_id}.source_url")
        parse_date(row.get("last_verified_at", ""), f"{group_id}.last_verified_at", True)
        item = dict(row)
        item["aliases"] = []
        groups.append(item)
        by_id[group_id] = item

    for group in groups:
        parent = group.get("parent_group_id", "").strip()
        if parent and parent not in by_id:
            raise ValueError(f"Unknown parent_group_id for {group['group_id']}: {parent}")
        for label in (group["canonical_name"], group.get("brand_name", "")):
            if label:
                aliases_by_group[group["group_id"]].append(label)

    for row in read_csv(ALIASES_PATH):
        group_id = row.get("canonical_group_id", "").strip()
        alias = row.get("alias", "").strip()
        if group_id not in by_id or not alias:
            raise ValueError(f"Invalid property group alias row: {row}")
        require_url(row.get("source_url", ""), f"alias {alias}.source_url")
        parse_date(row.get("last_verified_at", ""), f"alias {alias}.last_verified_at", True)
        aliases_by_group[group_id].append(alias)

    for group_id, aliases in aliases_by_group.items():
        unique = []
        for alias in aliases:
            key = normalise(alias)
            if not key:
                continue
            prior = alias_owner.get(key)
            if prior and prior != group_id:
                raise ValueError(f"Property group alias collision: {alias} ({prior}, {group_id})")
            alias_owner[key] = group_id
            if alias not in unique:
                unique.append(alias)
        by_id[group_id]["aliases"] = unique

    remaps = read_csv(GROUP_REMAPS_PATH)
    previous_ids = set()
    for row in remaps:
        previous = row.get("previous_group_id", "").strip()
        canonical = row.get("canonical_group_id", "").strip()
        if not previous or previous in previous_ids or canonical not in by_id or previous in by_id:
            raise ValueError(f"Invalid property group ID remap: {row}")
        previous_ids.add(previous)

    return groups, by_id, alias_owner, remaps


def validate_relationship(row: dict, places: dict[str, dict], groups: dict[str, dict]) -> dict:
    item = {key: str(value or "").strip() for key, value in row.items()}
    relationship_id = item.get("relationship_id", "")
    if not relationship_id:
        raise ValueError("relationship_id is required")
    if item.get("place_id") not in places:
        raise ValueError(f"Unknown relationship place_id in {relationship_id}: {item.get('place_id')}")
    if item.get("group_id") not in groups:
        raise ValueError(f"Unknown relationship group_id in {relationship_id}: {item.get('group_id')}")
    if item.get("role") not in ROLES:
        raise ValueError(f"Invalid role in {relationship_id}: {item.get('role')}")
    if item.get("status") not in RELATIONSHIP_STATUS:
        raise ValueError(f"Invalid relationship status in {relationship_id}: {item.get('status')}")
    if item.get("confidence") not in CONFIDENCE:
        raise ValueError(f"Invalid confidence in {relationship_id}: {item.get('confidence')}")
    item["source_url"] = require_url(item.get("source_url", ""), f"{relationship_id}.source_url")
    if not item.get("source_type"):
        raise ValueError(f"source_type is required in {relationship_id}")
    parse_date(item.get("last_verified_at", ""), f"{relationship_id}.last_verified_at", True)
    parse_date(item.get("valid_from", ""), f"{relationship_id}.valid_from")
    parse_date(item.get("valid_to", ""), f"{relationship_id}.valid_to")
    if item.get("valid_from") and item.get("valid_to") and item["valid_from"] > item["valid_to"]:
        raise ValueError(f"valid_from is after valid_to in {relationship_id}")
    percentage = item.get("ownership_percentage", "")
    if percentage:
        if item["role"] not in OWNER_ROLES:
            raise ValueError(f"ownership_percentage is only valid for owner roles: {relationship_id}")
        try:
            number = float(percentage)
        except ValueError as error:
            raise ValueError(f"Invalid ownership_percentage in {relationship_id}: {percentage}") from error
        if not 0 < number <= 100:
            raise ValueError(f"ownership_percentage out of range in {relationship_id}: {number}")
        item["ownership_percentage"] = number
    else:
        item["ownership_percentage"] = None
    item["derived_from"] = item.get("derived_from") or "curated_relationship"
    return item


def infer_centre_class(asset: dict) -> dict | None:
    """Infer scale only when two independent official portfolio measures agree."""
    try:
        gla = float(asset.get("gla_sqm") or 0)
        tenancies = int(float(asset.get("tenancy_count") or 0))
    except ValueError:
        return None
    if not gla or not tenancies:
        return None
    if gla >= 85000 and tenancies >= 250:
        centre_class = "Super Regional"
    elif gla >= 50000 and tenancies >= 150:
        centre_class = "Regional"
    elif gla >= 20000 and tenancies >= 70:
        centre_class = "Sub-regional"
    else:
        return None
    return {
        "centre_class": centre_class,
        "classification_method": "Inferred",
        "source_url": asset["source_url"],
        "source_type": asset["source_type"],
        "last_verified_at": asset["last_verified_at"],
        "confidence": "Medium",
        "public_note": f"Scale inferred from official portfolio GLA ({gla:,.0f} sqm) and tenant count ({tenancies}); not inferred from GLA alone",
    }


def load_portfolio_assets(places: dict[str, dict], groups: dict[str, dict]) -> tuple[list[dict], list[dict], dict[str, dict], set[str], list[dict]]:
    assets: list[dict] = []
    generated: list[dict] = []
    attributes: dict[str, dict] = {}
    reviews: list[dict] = []
    bounded_groups = {
        row.get("group_id", "").strip()
        for row in read_csv(PORTFOLIO_SCOPES_PATH)
        if row.get("scope_status", "").strip() == "Complete"
    }
    if any(group_id not in groups for group_id in bounded_groups):
        raise ValueError("property_portfolio_scopes.csv references an unknown group")
    seen_ids: set[str] = set()
    name_index: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for place in places.values():
        if place.get("place_type") != "Shopping Centre":
            continue
        for label in [place.get("name", ""), *place.get("aliases", [])]:
            if label:
                name_index[(place.get("country", ""), place.get("state", ""), normalise(label))].append(place["place_id"])

    for raw in read_csv(PORTFOLIO_ASSETS_PATH):
        asset = {key: str(value or "").strip() for key, value in raw.items()}
        asset_id = asset.get("portfolio_asset_id", "")
        group_id = asset.get("group_id", "")
        if not asset_id or asset_id in seen_ids or group_id not in groups:
            raise ValueError(f"Invalid or duplicate portfolio asset: {asset}")
        seen_ids.add(asset_id)
        asset["source_url"] = require_url(asset.get("source_url", ""), f"{asset_id}.source_url")
        parse_date(asset.get("source_date", ""), f"{asset_id}.source_date", True)
        parse_date(asset.get("last_verified_at", ""), f"{asset_id}.last_verified_at", True)
        if asset.get("confidence") not in CONFIDENCE or asset.get("status") not in {"ACTIVE", "RETIRED"}:
            raise ValueError(f"Invalid portfolio asset status/confidence: {asset_id}")
        roles = [role for role in asset.get("roles", "").split("|") if role]
        if not roles or any(role not in ROLES for role in roles):
            raise ValueError(f"Invalid portfolio asset roles: {asset_id}")
        percentage = asset.get("ownership_percentage", "")
        if percentage:
            try:
                if not 0 < float(percentage) <= 100:
                    raise ValueError
            except ValueError as error:
                raise ValueError(f"Invalid portfolio ownership percentage: {asset_id}") from error

        preferred = asset.get("preferred_place_id", "")
        candidates = [preferred] if preferred and preferred in places else []
        if not candidates:
            labels = [asset.get("canonical_name", ""), *[item.strip() for item in asset.get("aliases", "").split("|") if item.strip()]]
            candidates = sorted({place_id for label in labels for place_id in name_index.get((asset.get("country", ""), asset.get("state", ""), normalise(label)), [])})
        if len(candidates) != 1:
            reviews.append({
                "review_id": f"review-portfolio-{slug(asset_id)}",
                "place_id": candidates[0] if len(candidates) == 1 else "",
                "candidate_group_id": group_id,
                "reason": "Official portfolio asset has no exact canonical-place match" if not candidates else f"Official portfolio asset has {len(candidates)} exact canonical-place matches",
                "source_url": asset["source_url"],
                "status": "Pending",
            })
            asset["match_status"] = "Unmatched" if not candidates else "Ambiguous"
            asset["matched_place_id"] = ""
            assets.append(asset)
            continue

        place_id = candidates[0]
        asset["match_status"] = "Matched"
        asset["matched_place_id"] = place_id
        assets.append(asset)
        for role in roles:
            row = {
                "relationship_id": f"rel-portfolio-{slug(asset_id)}-{role.lower()}",
                "place_id": place_id,
                "group_id": group_id,
                "role": role,
                "ownership_percentage": percentage if role in OWNER_ROLES else "",
                "valid_from": "",
                "valid_to": "" if asset["status"] == "ACTIVE" else asset["source_date"],
                "status": asset["status"],
                "source_url": asset["source_url"],
                "source_type": asset["source_type"],
                "last_verified_at": asset["last_verified_at"],
                "confidence": asset["confidence"],
                "public_note": asset.get("public_note", "Official portfolio evidence"),
                "derived_from": "official_portfolio_asset",
            }
            generated.append(validate_relationship(row, places, groups))
        inferred = infer_centre_class(asset)
        if inferred:
            attributes[place_id] = {"place_id": place_id, **inferred}
    return assets, generated, attributes, bounded_groups, reviews


def load_relationships(places: dict[str, dict], groups: dict[str, dict], portfolio_relationships: list[dict], portfolio_groups: set[str]) -> tuple[list[dict], list[dict]]:
    relationships: list[dict] = []
    seen_ids: set[str] = set()
    seen_keys: set[tuple[str, str, str]] = set()
    reviews: list[dict] = []

    for row in read_csv(RELATIONSHIPS_PATH):
        item = validate_relationship(row, places, groups)
        if item["relationship_id"] in seen_ids:
            raise ValueError(f"Duplicate relationship_id: {item['relationship_id']}")
        seen_ids.add(item["relationship_id"])
        seen_keys.add((item["place_id"], item["group_id"], item["role"]))
        relationships.append(item)

    for item in portfolio_relationships:
        key = (item["place_id"], item["group_id"], item["role"])
        if item["relationship_id"] in seen_ids or key in seen_keys:
            continue
        relationships.append(item)
        seen_ids.add(item["relationship_id"])
        seen_keys.add(key)

    rules = read_csv(DOMAIN_RULES_PATH)
    for rule in rules:
        domain = rule.get("domain", "").strip().lower().removeprefix("www.")
        group_id = rule.get("canonical_group_id", "").strip()
        role = rule.get("role", "").strip()
        if not domain or group_id not in groups or role not in ROLES or rule.get("confidence") not in CONFIDENCE:
            raise ValueError(f"Invalid property domain rule: {rule}")
        # Where a bounded official portfolio exists, it is the authority. A domain
        # alone may be stale or misleading and must not certify an extra asset.
        if group_id in portfolio_groups:
            continue
        for place in places.values():
            if place.get("place_type") != "Shopping Centre":
                continue
            urls = [place.get("official_url", ""), place.get("source_url", "")]
            matched_url = next((url for url in urls if host_for(url) == domain or host_for(url).endswith(f".{domain}")), "")
            if not matched_url:
                continue
            key = (place["place_id"], group_id, role)
            if key in seen_keys:
                continue
            row = {
                "relationship_id": f"rel-domain-{slug(place['place_id'])}-{slug(group_id)}-{role.lower()}",
                "place_id": place["place_id"],
                "group_id": group_id,
                "role": role,
                "ownership_percentage": "",
                "valid_from": "",
                "valid_to": "",
                "status": "ACTIVE",
                "source_url": matched_url,
                "source_type": rule.get("source_type", "Official property website"),
                "last_verified_at": place.get("source_date") or date.today().isoformat(),
                "confidence": rule["confidence"],
                "public_note": "Official property or portfolio domain identifies this group",
                "derived_from": "official_domain_rule",
            }
            item = validate_relationship(row, places, groups)
            if item["relationship_id"] in seen_ids:
                raise ValueError(f"Generated duplicate relationship_id: {item['relationship_id']}")
            relationships.append(item)
            seen_ids.add(item["relationship_id"])
            seen_keys.add(key)

    ownership_totals: dict[str, float] = defaultdict(float)
    for relationship in relationships:
        if active_relationship(relationship) and relationship["role"] in OWNER_ROLES:
            ownership_totals[relationship["place_id"]] += relationship.get("ownership_percentage") or 0
    for place_id, total in ownership_totals.items():
        if total > 100.0001:
            raise ValueError(f"Active ownership percentages exceed 100% for {place_id}: {total}")

    return relationships, reviews


def load_attributes(places: dict[str, dict]) -> dict[str, dict]:
    attributes: dict[str, dict] = {}
    for row in read_csv(ATTRIBUTES_PATH):
        place_id = row.get("place_id", "").strip()
        if place_id not in places or place_id in attributes:
            raise ValueError(f"Invalid or duplicate property attribute place_id: {place_id}")
        if row.get("centre_class") not in CENTRE_CLASSES:
            raise ValueError(f"Invalid centre_class for {place_id}: {row.get('centre_class')}")
        if row.get("classification_method") not in CLASS_METHODS:
            raise ValueError(f"Invalid classification_method for {place_id}: {row.get('classification_method')}")
        if row.get("confidence") not in CONFIDENCE:
            raise ValueError(f"Invalid attribute confidence for {place_id}: {row.get('confidence')}")
        require_url(row.get("source_url", ""), f"{place_id}.centre_class.source_url")
        parse_date(row.get("last_verified_at", ""), f"{place_id}.centre_class.last_verified_at", True)
        attributes[place_id] = dict(row)
    return attributes


def load_research(places: dict[str, dict]) -> dict[str, dict]:
    research: dict[str, dict] = {}
    for row in read_csv(RESEARCH_PATH):
        place_id = row.get("place_id", "").strip()
        if place_id not in places or place_id in research:
            raise ValueError(f"Invalid or duplicate research place_id: {place_id}")
        if row.get("research_status") not in RESEARCH_STATUS:
            raise ValueError(f"Invalid research_status for {place_id}: {row.get('research_status')}")
        require_url(row.get("source_url", ""), f"{place_id}.research.source_url")
        parse_date(row.get("last_verified_at", ""), f"{place_id}.research.last_verified_at", True)
        if row.get("confidence") not in CONFIDENCE:
            raise ValueError(f"Invalid research confidence for {place_id}: {row.get('confidence')}")
        research[place_id] = dict(row)
    return research


def derive_arrangement(relationships: list[dict], groups: dict[str, dict]) -> str:
    active = [item for item in relationships if active_relationship(item)]
    if any(item["role"] == "EXTERNAL_LEASING_AGENT" for item in active):
        return "External agency"
    controllers = {item["group_id"] for item in active if item["role"] == "LEASING_CONTROLLER"}
    operating = {item["group_id"] for item in active if item["role"] in PROPERTY_GROUP_ROLES}
    if any(groups[group_id]["group_type"] == "PRIVATE_LANDLORD" for group_id in controllers):
        return "Private landlord"
    if controllers & operating:
        return "In-house"
    return "Unknown"


def load_stores() -> list[dict]:
    memberships = {row["store_id"]: row for row in read_csv(MEMBERSHIPS_PATH)}
    stores: list[dict] = []
    for row in read_csv(STORES_PATH):
        membership = memberships.get(row.get("store_id", ""), {})
        try:
            latitude, longitude = float(row["latitude"]), float(row["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        stores.append({
            "store_id": row.get("store_id", ""),
            "name": row.get("name", ""),
            "retailer": row.get("retailer", ""),
            "latitude": latitude,
            "longitude": longitude,
            "place_id": membership.get("place_id", ""),
            "usable_for_network": membership.get("usable_for_network", "").lower() == "true",
        })
    return stores


def competitor_context(place: dict, stores: list[dict]) -> dict:
    brands: dict[str, dict] = defaultdict(lambda: {"in_centre": [], "nearby_unverified": [], "catchment_2km": []})
    nearest: dict[str, float] = {}
    for store in stores:
        distance = haversine(place, store)
        brand = store["retailer"]
        nearest[brand] = min(distance, nearest.get(brand, float("inf")))
        brief = {"store_id": store["store_id"], "name": store["name"], "distance_km": round(distance, 2)}
        if store.get("place_id") == place["place_id"]:
            brands[brand]["in_centre"].append(brief)
        elif distance <= 0.25:
            brands[brand]["nearby_unverified"].append(brief)
        elif distance <= 2:
            brands[brand]["catchment_2km"].append(brief)
    return {
        "by_retailer": dict(brands),
        "nearest_by_retailer_km": {key: round(value, 2) for key, value in nearest.items()},
        "independent_2km_count": sum(
            len(value["nearby_unverified"]) + len(value["catchment_2km"])
            for key, value in brands.items() if key == "Independent / Other optical"
        ),
    }


def market_for_place(place: dict, market_features: list[dict]) -> dict:
    for feature in market_features:
        geometry = feature.get("geometry") or {}
        if point_in_geometry(float(place["longitude"]), float(place["latitude"]), geometry):
            props = feature.get("properties", {})
            return {
                "sa2_code": props.get("sa2_code") or props.get("SA2_CODE21") or props.get("code") or "",
                "sa2_name": props.get("sa2_name") or props.get("SA2_NAME21") or props.get("name") or "",
                "population_2025": props.get("population_2025"),
                "population_growth_pct": props.get("population_growth_2021_2025_pct"),
                "median_household_income": props.get("median_household_income_weekly_2021"),
                "age_45_plus_pct": props.get("age_45_plus_pct_2021"),
                "retail_businesses": props.get("retail_businesses_2025"),
            }
    return {}


def main() -> None:
    places_payload = json.loads(PLACES_PATH.read_text(encoding="utf-8"))
    place_rows = places_payload.get("places", places_payload if isinstance(places_payload, list) else [])
    places = {item["place_id"]: item for item in place_rows}
    if len(places) != len(place_rows):
        raise ValueError("retail_places.json contains duplicate place_id values")

    groups, groups_by_id, alias_index, group_remaps = load_groups()
    portfolio_assets, portfolio_relationships, inferred_attributes, portfolio_groups, portfolio_reviews = load_portfolio_assets(places, groups_by_id)
    relationships, reviews = load_relationships(places, groups_by_id, portfolio_relationships, portfolio_groups)
    reviews.extend(portfolio_reviews)
    attributes = load_attributes(places)
    for place_id, attribute in inferred_attributes.items():
        attributes.setdefault(place_id, attribute)
    research = load_research(places)
    stores = load_stores()
    market_payload = json.loads(MARKETS_PATH.read_text(encoding="utf-8")) if MARKETS_PATH.exists() else {"features": []}
    market_features = market_payload.get("features", [])

    portfolio_metrics_by_place: dict[str, dict] = defaultdict(dict)
    for asset in portfolio_assets:
        place_id = asset.get("matched_place_id", "")
        if not place_id:
            continue
        metrics = portfolio_metrics_by_place[place_id]
        for field in ("gla_sqm", "tenancy_count"):
            if asset.get(field) and not metrics.get(field):
                metrics[field] = float(asset[field]) if field == "gla_sqm" else int(float(asset[field]))
        if asset.get("annual_visits_m") and not metrics.get("annual_visits"):
            metrics["annual_visits"] = float(asset["annual_visits_m"]) * 1_000_000
        if any(asset.get(field) for field in ("gla_sqm", "tenancy_count", "annual_visits_m")):
            metrics.setdefault("source_url", asset["source_url"])
            metrics.setdefault("last_verified_at", asset["last_verified_at"])

    relationships_by_place: dict[str, list[dict]] = defaultdict(list)
    for relationship in relationships:
        relationships_by_place[relationship["place_id"]].append(relationship)

    # Any official-domain relationship establishes partial research, but never complete verification.
    for place_id in relationships_by_place:
        if place_id not in research:
            research[place_id] = {
                "place_id": place_id,
                "research_status": "Partial",
                "source_url": relationships_by_place[place_id][0]["source_url"],
                "last_verified_at": max(item["last_verified_at"] for item in relationships_by_place[place_id]),
                "confidence": max((item["confidence"] for item in relationships_by_place[place_id]), key=lambda x: ["Low", "Medium", "High"].index(x)),
                "public_note": "At least one public property-group role is identified; full ownership and leasing research is incomplete",
            }

    bailey_stores_by_place: dict[str, list[str]] = defaultdict(list)
    for store in stores:
        if store["retailer"] == "Bailey Nelson" and store.get("place_id"):
            bailey_stores_by_place[store["place_id"]].append(store["store_id"])

    active_by_group: dict[str, list[dict]] = defaultdict(list)
    for relationship in relationships:
        if active_relationship(relationship):
            active_by_group[relationship["group_id"]].append(relationship)

    group_portfolios: dict[str, dict] = {}
    for group in groups:
        group_relationships = active_by_group[group["group_id"]]
        asset_roles: dict[str, set[str]] = defaultdict(set)
        for relationship in group_relationships:
            asset_roles[relationship["place_id"]].add(relationship["role"])
        bailey_properties = sorted(place_id for place_id in asset_roles if bailey_stores_by_place.get(place_id))
        bailey_store_ids = sorted({store_id for place_id in bailey_properties for store_id in bailey_stores_by_place[place_id]})
        group_portfolios[group["group_id"]] = {
            "group_id": group["group_id"],
            "property_count": len(asset_roles),
            "bailey_property_count": len(bailey_properties),
            "bailey_store_count": len(bailey_store_ids),
            "bailey_property_ids": bailey_properties,
            "asset_roles": {key: sorted(value) for key, value in sorted(asset_roles.items())},
            "white_space_property_ids": [],
        }

    summaries: dict[str, dict] = {}
    feature_vectors: dict[str, dict] = {}
    for place_id, place in places.items():
        active = [item for item in relationships_by_place.get(place_id, []) if active_relationship(item)]
        research_item = research.get(place_id, {
            "place_id": place_id,
            "research_status": "Not researched",
            "source_url": "",
            "last_verified_at": "",
            "confidence": "",
            "public_note": "No public property relationship research has been completed",
        })
        attribute = attributes.get(place_id, {
            "place_id": place_id,
            "centre_class": "Unknown",
            "classification_method": "",
            "source_url": "",
            "source_type": "",
            "last_verified_at": "",
            "confidence": "",
            "public_note": "",
        })
        has_bailey = bool(bailey_stores_by_place.get(place_id) or place.get("has_bailey"))

        overlap_options: list[tuple[int, str, dict, dict]] = []
        role_priority = {
            "LEASING_CONTROLLER": (1, "LEASING_CONTROLLER_OVERLAP"),
            "OWNER": (2, "PROPERTY_GROUP_OVERLAP"),
            "CO_OWNER": (2, "PROPERTY_GROUP_OVERLAP"),
            "MANAGER": (2, "PROPERTY_GROUP_OVERLAP"),
            "OPERATOR": (2, "PROPERTY_GROUP_OVERLAP"),
            "EXTERNAL_LEASING_AGENT": (3, "EXTERNAL_AGENCY_OVERLAP"),
        }
        for relationship in active:
            portfolio = group_portfolios[relationship["group_id"]]
            if portfolio["bailey_property_count"] and relationship["role"] in role_priority:
                rank, label = role_priority[relationship["role"]]
                overlap_options.append((rank, label, relationship, portfolio))
        if has_bailey:
            overlap_status = "SAME_CENTRE"
        elif overlap_options:
            overlap_status = sorted(overlap_options, key=lambda item: item[0])[0][1]
        elif research_item["research_status"] in {"Verified", "Verified unknown"}:
            overlap_status = "NO_KNOWN_OVERLAP"
        else:
            overlap_status = "UNKNOWN"

        overlap_groups = []
        for _, _, relationship, portfolio in sorted(overlap_options, key=lambda item: (item[0], groups_by_id[item[2]["group_id"]]["canonical_name"])):
            overlap_groups.append({
                "group_id": relationship["group_id"],
                "canonical_name": groups_by_id[relationship["group_id"]]["canonical_name"],
                "role": relationship["role"],
                "bailey_property_count": portfolio["bailey_property_count"],
                "bailey_store_count": portfolio["bailey_store_count"],
            })
        seen_overlap = set()
        overlap_groups = [item for item in overlap_groups if not (item["group_id"], item["role"]) in seen_overlap and not seen_overlap.add((item["group_id"], item["role"]))]

        competition = competitor_context(place, stores)
        nearest_bailey = competition["nearest_by_retailer_km"].get("Bailey Nelson")
        market = market_for_place(place, market_features) if market_features else {}
        portfolio_white_space = not has_bailey and overlap_status in {
            "LEASING_CONTROLLER_OVERLAP", "PROPERTY_GROUP_OVERLAP", "EXTERNAL_AGENCY_OVERLAP",
        }
        for item in overlap_groups:
            if portfolio_white_space:
                group_portfolios[item["group_id"]]["white_space_property_ids"].append(place_id)

        owners = [item for item in active if item["role"] in OWNER_ROLES]
        managers = [item for item in active if item["role"] == "MANAGER"]
        summary = {
            "place_id": place_id,
            "centre_class": attribute["centre_class"],
            "centre_class_method": attribute.get("classification_method", ""),
            "centre_class_evidence": attribute,
            "research_status": research_item["research_status"],
            "research_evidence": research_item,
            "leasing_arrangement": derive_arrangement(active, groups_by_id),
            "relationship_ids": [item["relationship_id"] for item in active],
            "group_ids": sorted({item["group_id"] for item in active}),
            "owner_names": [groups_by_id[item["group_id"]]["canonical_name"] for item in owners],
            "manager_names": [groups_by_id[item["group_id"]]["canonical_name"] for item in managers],
            "has_bailey": has_bailey,
            "bailey_store_count": len(bailey_stores_by_place.get(place_id, [])),
            "portfolio_overlap_status": overlap_status,
            "portfolio_overlap_groups": overlap_groups,
            "portfolio_white_space": portfolio_white_space,
            "nearest_bailey_km": nearest_bailey,
            "competitor_context": competition,
            "market": market,
            **portfolio_metrics_by_place.get(place_id, {}),
        }
        summaries[place_id] = summary
        feature_vectors[place_id] = {
            "schema_version": 1,
            "place_id": place_id,
            "demographic": {"availability": "Available" if market else "Unavailable", "values": market},
            "competition": {
                "availability": "Available",
                "evidence_pointer": f"property_summaries.{place_id}.competitor_context",
                "values": {"in_centre_rule": "accepted shared canonical place_id", "nearby_rule": "straight-line distance only; never centre membership"},
            },
            "retail_environment": {
                "availability": "Partial",
                "values": {"location_setting": place.get("location_setting"), "centre_class": attribute["centre_class"]},
            },
            "accessibility": {"availability": "Unavailable", "values": {}},
            "catchment": {"availability": "Indicative only", "values": {"method": "2 km straight-line competitor context"}},
            "portfolio": {
                "availability": "Available" if active else "Not researched",
                "values": {"nearest_bailey_km": nearest_bailey, "group_ids": summary["group_ids"], "overlap_status": overlap_status},
            },
        }

    for portfolio in group_portfolios.values():
        portfolio["white_space_property_ids"] = sorted(set(portfolio["white_space_property_ids"]))

    shopping_centres = [place for place in places.values() if place.get("place_type") == "Shopping Centre"]
    relationship_conflicts = [item for item in research.values() if item["research_status"] == "Conflict"]
    metadata = {
        "coverage_scope": "Shopping centres are the Phase 1 relationship scope; high-street corridors remain Unknown unless explicitly researched.",
        "group_count": len(groups),
        "relationship_count": len(relationships),
        "active_relationship_count": sum(active_relationship(item) for item in relationships),
        "shopping_centre_count": len(shopping_centres),
        "researched_property_count": sum(summaries[item["place_id"]]["research_status"] != "Not researched" for item in shopping_centres),
        "classed_property_count": sum(summaries[item["place_id"]]["centre_class"] != "Unknown" for item in shopping_centres),
        "conflict_count": len(relationship_conflicts),
        "unknown_is_valid": True,
        "relationship_derivation_note": "Official property or portfolio domains may establish a group role. Geographic proximity never establishes property membership or a group relationship.",
        "portfolio_overlap_note": "Portfolio overlap is derived from public tenancy and property-group evidence; it is not proof of a private commercial relationship.",
    }
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata,
        "groups": groups,
        "group_alias_index": alias_index,
        "group_id_remaps": group_remaps,
        "relationships": relationships,
        "portfolio_assets": portfolio_assets,
        "property_summaries": summaries,
        "group_portfolios": group_portfolios,
        "feature_vectors": feature_vectors,
        "review_items": reviews,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(REVIEW_PATH, reviews, REVIEW_FIELDS)
    research_queue = []
    for place in shopping_centres:
        summary = summaries[place["place_id"]]
        if summary["research_status"] != "Not researched" and summary["centre_class"] != "Unknown":
            continue
        by_retailer = summary.get("competitor_context", {}).get("by_retailer", {})
        named_brands = sum(
            bool(context.get("in_centre"))
            for retailer, context in by_retailer.items()
            if retailer != "Independent / Other optical"
        )
        optical_stores = sum(len(context.get("in_centre", [])) for context in by_retailer.values())
        if summary.get("bailey_store_count", 0):
            priority = "P1"
            reason = "Bailey Nelson centre still has an unresolved property-research or centre-class field"
        elif named_brands >= 2:
            priority = "P2"
            reason = "Multiple named optical networks make this a high-value leasing and competition research target"
        elif named_brands == 1 or place.get("official_url"):
            priority = "P3"
            reason = "Mapped named-network tenancy or official venue source provides a practical research starting point"
        else:
            priority = "P4"
            reason = "Broad-registry centre with no mapped named-network tenancy or official venue source yet"
        research_queue.append({
            "priority": priority,
            "place_id": place["place_id"],
            "name": place.get("name", ""),
            "country": place.get("country", ""),
            "state": place.get("state", ""),
            "locality": place.get("locality") or place.get("suburb", ""),
            "research_status": summary["research_status"],
            "centre_class": summary["centre_class"],
            "bailey_store_count": summary.get("bailey_store_count", 0),
            "mapped_named_brands": named_brands,
            "mapped_optical_stores": optical_stores,
            "official_url": place.get("official_url") or place.get("source_url", ""),
            "reason": reason,
        })
    research_queue.sort(key=lambda row: (row["priority"], -row["mapped_named_brands"], -row["mapped_optical_stores"], row["country"], row["state"], row["name"]))
    write_csv(RESEARCH_QUEUE_PATH, research_queue, RESEARCH_QUEUE_FIELDS)
    print(
        f"Built {len(groups)} groups, {len(relationships)} property relationships, "
        f"{metadata['researched_property_count']}/{len(shopping_centres)} researched shopping centres; "
        f"{len(research_queue)} queued property/class follow-ups"
    )


if __name__ == "__main__":
    main()
