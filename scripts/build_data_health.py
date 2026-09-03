#!/usr/bin/env python3
"""Build practical store usability, place mapping and source health outputs."""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST_PATH = DATA / "source_manifest.json"
STORE_PATH = DATA / "optical_stores.csv"
MEMBERSHIP_PATH = DATA / "store_place_memberships.csv"
PLACE_PATH = DATA / "retail_places.json"
REVIEW_PATH = DATA / "place_review.csv"
STORE_HEALTH_PATH = DATA / "store_certification.csv"
HEALTH_PATH = DATA / "data_health.json"
PROPERTY_INTELLIGENCE_PATH = DATA / "property_intelligence.json"
PLACE_TENANTS_PATH = DATA / "place_tenants.json"
INTELLIGENCE_LAYER_REGISTER_PATH = DATA / "intelligence_layer_register.csv"
NAMED_RETAILERS = {
    "OPSM", "Specsavers", "Bailey Nelson", "Oscar Wylee",
    "George & Matilda", "Eyecare Plus", "Optical Superstore",
    "1001 Optometry", "EyeQ Optometrists", "Laubman & Pank",
    "Bupa Optical", "Chemist Warehouse Optometry", "Dresden Vision",
    "Optical Warehouse", "The Optical Company", "Optical by National Pharmacies",
    "Matthews Eyecare",
}
FRESHNESS_KEYS = {
    "opsm-au": "OPSM Australia", "opsm-nz": "OPSM New Zealand",
    "specsavers-au": "Specsavers Australia", "specsavers-nz": "Specsavers New Zealand",
    "bailey-nelson-au": "Bailey Nelson Australia", "bailey-nelson-nz": "Bailey Nelson New Zealand",
    "oscar-wylee-au": "Oscar Wylee Australia", "oscar-wylee-nz": "Oscar Wylee New Zealand",
    "george-and-matilda-au": "George & Matilda Australia",
    "eyecare-plus-au": "Eyecare Plus Australia",
    "optical-superstore-au": "Optical Superstore Australia",
    "1001-optometry-au": "1001 Optometry Australia",
    "eyeq-optometrists-au": "EyeQ Optometrists Australia",
    "laubman-and-pank-au": "Laubman & Pank Australia",
    "bupa-optical-au": "Bupa Optical Australia",
    "chemist-warehouse-optometry-au": "Chemist Warehouse Optometry Australia",
    "dresden-vision-au": "Dresden Vision Australia",
    "optical-warehouse-au": "Optical Warehouse Australia",
    "the-optical-company-au": "The Optical Company Australia",
    "national-pharmacies-optical-au": "Optical by National Pharmacies Australia",
    "matthews-eyecare-nz": "Matthews Eyecare New Zealand",
    "provision-affiliation": "ProVision Australia",
    "osm-opticians": "Independent / Other optical",
}


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_date(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) == 10:
        text += "T00:00:00+00:00"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def now_utc() -> datetime:
    override = parse_date(os.environ.get("DATA_HEALTH_AS_OF"))
    return override or datetime.now(timezone.utc)


def percent(passed: int, total: int) -> float:
    return round((passed / total * 100) if total else 100.0, 1)


def find_timestamp(value: object) -> str:
    if isinstance(value, dict):
        for key in ("fetched_at", "generated_at", "snapshot_date", "source_date"):
            if key in value and parse_date(value[key]):
                return str(value[key])
        for child in value.values():
            found = find_timestamp(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_timestamp(child)
            if found:
                return found
    return ""


def source_results(manifest: dict, as_of: datetime, metadata: dict) -> list[dict]:
    policies = manifest["freshness_policy_days"]
    results = []
    for source in manifest["sources"]:
        snapshot = ROOT / source["snapshot"]
        timestamp = str(source.get("last_success", ""))
        if source["id"] in FRESHNESS_KEYS:
            timestamp = str(metadata.get("source_freshness", {}).get(FRESHNESS_KEYS[source["id"]], timestamp))
        elif snapshot.suffix.lower() == ".json" and snapshot.exists():
            timestamp = find_timestamp(json.loads(snapshot.read_text(encoding="utf-8"))) or timestamp
        elif snapshot.suffix.lower() == ".csv" and snapshot.exists() and not timestamp:
            dates = [row.get("source_date", "") for row in read_csv(snapshot)]
            timestamp = max((value for value in dates if parse_date(value)), default="")
        parsed = parse_date(timestamp)
        max_age = int(policies[source["category"]])
        age_days = (as_of - parsed).days if parsed else None
        complete = source.get("completion_status", "complete") == "complete"
        available = snapshot.exists()
        fresh = age_days is not None and age_days <= max_age
        status = "current" if available and complete and fresh else "partial" if available and not complete else "stale" if available and not fresh else "missing"
        results.append({**source, "last_success": timestamp or None, "age_days": age_days, "max_age_days": max_age, "available": available, "complete": complete, "fresh": fresh, "status": status})
    return results


def source_id_for_store(store: dict) -> str:
    country = "nz" if store["country"] == "New Zealand" else "au"
    if store["retailer"] == "Independent / Other optical":
        return "provision-affiliation" if "provision" in store.get("affiliations", "").split("|") else "osm-opticians"
    retailer = {
        "OPSM": "opsm", "Specsavers": "specsavers", "Bailey Nelson": "bailey-nelson",
        "Oscar Wylee": "oscar-wylee", "George & Matilda": "george-and-matilda",
        "Eyecare Plus": "eyecare-plus", "Optical Superstore": "optical-superstore",
        "1001 Optometry": "1001-optometry", "EyeQ Optometrists": "eyeq-optometrists",
        "Laubman & Pank": "laubman-and-pank",
        "Bupa Optical": "bupa-optical",
        "Chemist Warehouse Optometry": "chemist-warehouse-optometry",
        "Dresden Vision": "dresden-vision",
        "Optical Warehouse": "optical-warehouse",
        "The Optical Company": "the-optical-company",
        "Optical by National Pharmacies": "national-pharmacies-optical",
        "Matthews Eyecare": "matthews-eyecare",
    }[store["retailer"]]
    return f"{retailer}-{country}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-certified", action="store_true", help="Fail unless every operational health gate is 100%")
    args = parser.parse_args()
    as_of = now_utc()
    generated_at = as_of.isoformat(timespec="seconds")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    metadata = json.loads((DATA / "optical_stores.meta.json").read_text(encoding="utf-8"))
    stores = read_csv(STORE_PATH)
    memberships = read_csv(MEMBERSHIP_PATH)
    membership_by_id = {row["store_id"]: row for row in memberships}
    places_payload = json.loads(PLACE_PATH.read_text(encoding="utf-8"))
    places = places_payload["places"]
    property_intelligence = json.loads(PROPERTY_INTELLIGENCE_PATH.read_text(encoding="utf-8"))
    place_tenants = json.loads(PLACE_TENANTS_PATH.read_text(encoding="utf-8"))
    reviews = read_csv(REVIEW_PATH)
    pending_reviews = [row for row in reviews if row.get("review_status") == "Pending"]
    discovery = read_csv(DATA / "discovery_candidates.csv")
    background_leads = [row for row in discovery if row.get("review_status") == "Pending"]
    sources = source_results(manifest, as_of, metadata)
    source_by_id = {source["id"]: source for source in sources}

    certification_rows = []
    for store in stores:
        membership = membership_by_id.get(store["store_id"], {})
        source_id = source_id_for_store(store)
        source = source_by_id[source_id]
        usable = membership.get("usable_for_network") == "true"
        setting_complete = membership.get("location_setting") not in {"", "Uncertain"}
        place_complete = setting_complete and (membership.get("location_setting") == "Other" or bool(membership.get("place_id")))
        current_source = source["fresh"] and source["complete"]
        issues = []
        if not usable:
            issues.append("record lacks a meaningful public storefront address")
        if not setting_complete:
            issues.append("location setting needs review")
        if setting_complete and membership.get("location_setting") != "Other" and not membership.get("place_id"):
            issues.append("canonical retail place is missing")
        if not current_source:
            issues.append("source refresh is stale or incomplete; record remains usable as last-known public data")
        status = "Usable" if usable and setting_complete and place_complete else "Needs review" if usable else "Limited"
        certification_rows.append({
            "store_id": store["store_id"], "retailer": store["retailer"], "country": store["country"], "state": store["state"],
            "location_setting": membership.get("location_setting", "Uncertain"), "place_id": membership.get("place_id", ""),
            "mapping_confidence": membership.get("mapping_confidence", "Uncertain"), "operational_status": status,
            "usable_for_network": str(usable).lower(), "current_source": str(current_source).lower(),
            "eligible_for_analytics": str(usable).lower(), "eligible_for_place_analytics": str(usable and place_complete).lower(),
            "source_id": source_id, "issues": "; ".join(issues),
        })

    named_rows = [row for row in certification_rows if row["retailer"] in NAMED_RETAILERS]
    usable_named = sum(row["usable_for_network"] == "true" for row in named_rows)
    setting_named = sum(row["location_setting"] != "Uncertain" for row in named_rows)
    mapped_named = sum(row["location_setting"] != "Uncertain" and (row["location_setting"] == "Other" or bool(row["place_id"])) for row in named_rows)
    current_named = sum(row["current_source"] == "true" for row in named_rows)
    required_sources = [source for source in sources if source["required"]]
    current_sources = sum(source["fresh"] and source["complete"] and source["available"] for source in required_sources)
    dimensions = {
        "source_freshness": percent(current_sources, len(required_sources)),
        "usable_store_coverage": percent(usable_named, len(named_rows)),
        "location_setting_coverage": percent(setting_named, len(named_rows)),
        "place_mapping_coverage": percent(mapped_named, len(named_rows)),
        "review_reconciliation": percent(len(named_rows) - len(pending_reviews), len(named_rows)),
    }
    complete = all(value == 100.0 for value in dimensions.values())
    status = "Certified" if complete else "Operational" if usable_named == len(named_rows) else "In progress"

    by_retailer = {}
    for retailer in sorted({row["retailer"] for row in certification_rows}):
        subset = [row for row in certification_rows if row["retailer"] == retailer]
        by_retailer[retailer] = {
            "observed": len(subset), "usable": sum(row["usable_for_network"] == "true" for row in subset),
            "current_source": sum(row["current_source"] == "true" for row in subset),
            "needs_review": sum(row["operational_status"] == "Needs review" for row in subset),
        }

    property_summaries = property_intelligence["property_summaries"]
    property_relationships = [row for row in property_intelligence["relationships"] if row.get("status") == "ACTIVE"]
    shopping_centres = [place for place in places if place.get("place_type") == "Shopping Centre"]
    researched_centres = [
        place for place in shopping_centres
        if property_summaries.get(place["place_id"], {}).get("research_status") != "Not researched"
    ]
    classed_centres = [
        place for place in shopping_centres
        if property_summaries.get(place["place_id"], {}).get("centre_class") != "Unknown"
    ]
    bailey_centres = [
        place for place in shopping_centres
        if property_summaries.get(place["place_id"], {}).get("bailey_store_count", 0) > 0
    ]
    researched_bailey_centres = [
        place for place in bailey_centres
        if property_summaries.get(place["place_id"], {}).get("research_status") != "Not researched"
    ]
    classed_bailey_centres = [
        place for place in bailey_centres
        if property_summaries.get(place["place_id"], {}).get("centre_class") != "Unknown"
    ]
    property_conflicts = [
        place for place in shopping_centres
        if property_summaries.get(place["place_id"], {}).get("research_status") == "Conflict"
    ]
    current_property_relationships = []
    for relationship in property_relationships:
        verified = parse_date(relationship.get("last_verified_at"))
        max_age = 90 if relationship.get("role") in {"LEASING_CONTROLLER", "EXTERNAL_LEASING_AGENT"} else 180
        if verified and (as_of - verified).days <= max_age:
            current_property_relationships.append(relationship)
    property_dimensions = {
        "research_coverage": percent(len(researched_centres), len(shopping_centres)),
        "relationship_freshness": percent(len(current_property_relationships), len(property_relationships)),
        "centre_class_coverage": percent(len(classed_centres), len(shopping_centres)),
        "bailey_centre_research_coverage": percent(len(researched_bailey_centres), len(bailey_centres)),
        "bailey_centre_class_coverage": percent(len(classed_bailey_centres), len(bailey_centres)),
        "conflict_reconciliation": percent(len(shopping_centres) - len(property_conflicts), len(shopping_centres)),
    }

    tenant_metadata = place_tenants.get("metadata", {})
    bailey_tenant_scope = tenant_metadata.get("bailey_centre_place_ids", [])
    researched_bailey_tenants = tenant_metadata.get("researched_bailey_centre_place_ids", [])
    anchor_profiled_bailey = tenant_metadata.get("anchor_profiled_bailey_centre_place_ids", [])
    multi_category_bailey = tenant_metadata.get("multi_category_bailey_centre_place_ids", [])
    tenant_rows = [row for row in place_tenants.get("memberships", []) if row.get("category") != "Optical"]
    current_tenant_rows = []
    for row in tenant_rows:
        evidence_date = parse_date(row.get("source_date") or row.get("verified_at"))
        if evidence_date and (as_of - evidence_date).days <= 90:
            current_tenant_rows.append(row)
    co_tenancy_dimensions = {
        "bailey_research_started": percent(len(researched_bailey_tenants), len(bailey_tenant_scope)),
        "bailey_anchor_coverage": percent(len(anchor_profiled_bailey), len(bailey_tenant_scope)),
        "bailey_multi_category_coverage": percent(len(multi_category_bailey), len(bailey_tenant_scope)),
        "evidence_freshness": percent(len(current_tenant_rows), len(tenant_rows)),
    }
    intelligence_layers = read_csv(INTELLIGENCE_LAYER_REGISTER_PATH)
    for layer in intelligence_layers:
        if layer.get("status") not in {"Operational", "In progress", "Pilot", "Planned", "Client/private only"}:
            raise ValueError(f"Invalid intelligence layer status: {layer.get('layer_id')}")
        if layer.get("priority") not in {"Now", "Next", "Later"}:
            raise ValueError(f"Invalid intelligence layer priority: {layer.get('layer_id')}")

    health = {
        "schema_version": 3, "generated_at": generated_at, "coverage_as_of": generated_at[:10], "certification_status": status,
        "coverage_statement": "The network uses best-available public store data. Freshness, location setting and canonical place confidence are reported separately.",
        "baselines": {"stores": 1491, "places": 394},
        "observed": {
            "stores": len(stores), "named_network_stores": len(named_rows),
            "usable_stores": sum(row["usable_for_network"] == "true" for row in certification_rows),
            "usable_named_network_stores": usable_named, "current_named_network_stores": current_named,
            "places": len(places), "centres": places_payload["metadata"]["centre_count"], "corridors": places_payload["metadata"]["corridor_count"],
        },
        "changes_from_baseline": {"stores": len(stores) - 1491, "places": len(places) - 394},
        "dimensions": dimensions,
        "blocking_counts": {
            "unusable_named_network_stores": len(named_rows) - usable_named,
            "uncertain_named_network_settings": len(named_rows) - setting_named,
            "named_network_places_missing": len(named_rows) - mapped_named,
            "pending_mapping_reviews": len(pending_reviews),
            "stale_or_incomplete_named_sources": len(named_rows) - current_named,
        },
        "informational_counts": {"background_discovery_leads": len(background_leads), "independent_records": sum(store["retailer"] == "Independent / Other optical" for store in stores)},
        "by_retailer": by_retailer, "by_country": dict(Counter(store["country"] for store in stores)),
        "by_location_setting": dict(Counter(row["location_setting"] for row in certification_rows)),
        "place_types": dict(Counter(place["place_type"] for place in places)), "sources": sources,
        "property_intelligence": {
            "coverage_statement": property_intelligence["metadata"]["coverage_scope"],
            "portfolio_overlap_note": property_intelligence["metadata"]["portfolio_overlap_note"],
            "dimensions": property_dimensions,
            "counts": {
                "groups": len(property_intelligence["groups"]),
                "relationships": len(property_relationships),
                "current_relationships": len(current_property_relationships),
                "stale_relationships": len(property_relationships) - len(current_property_relationships),
                "shopping_centres": len(shopping_centres),
                "researched_centres": len(researched_centres),
                "classed_centres": len(classed_centres),
                "bailey_centres": len(bailey_centres),
                "researched_bailey_centres": len(researched_bailey_centres),
                "classed_bailey_centres": len(classed_bailey_centres),
                "conflicts": len(property_conflicts),
                "review_items": len(property_intelligence.get("review_items", [])),
                "development_assets": property_intelligence.get("metadata", {}).get("development_asset_count", 0),
                "unmatched_active_portfolio_assets": property_intelligence.get("metadata", {}).get("unmatched_active_portfolio_count", 0),
            },
            "freshness_policy_days": {"ownership_management": 180, "leasing_agency": 90},
        },
        "co_tenancy": {
            "coverage_statement": tenant_metadata.get("coverage_note", "Curated key co-tenancy profiles; not complete directories."),
            "dimensions": co_tenancy_dimensions,
            "counts": {
                "pilot_places": len(tenant_metadata.get("pilot_place_ids", [])),
                "bailey_centres": len(bailey_tenant_scope),
                "bailey_research_started": len(researched_bailey_tenants),
                "bailey_anchor_profiled": len(anchor_profiled_bailey),
                "bailey_multi_category_profiled": len(multi_category_bailey),
                "researched_places": len(tenant_metadata.get("researched_place_ids", [])),
                "key_tenant_records": len(tenant_rows),
                "current_key_tenant_records": len(current_tenant_rows),
            },
            "freshness_policy_days": 90,
        },
        "intelligence_layer_register": intelligence_layers,
        "store_certification": {
            row["store_id"]: {key: row[key] for key in ("operational_status", "usable_for_network", "current_source", "eligible_for_analytics", "eligible_for_place_analytics", "location_setting", "place_id", "mapping_confidence", "issues")}
            for row in certification_rows
        },
        "unresolved_mapping_reviews": pending_reviews,
    }

    with STORE_HEALTH_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(certification_rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(certification_rows)
    HEALTH_PATH.write_text(json.dumps(health, indent=2) + "\n", encoding="utf-8")
    print(f"Named-network stores usable: {usable_named}/{len(named_rows)}; setting mapped: {setting_named}; place mapped: {mapped_named}")
    print(f"Places: {len(places)}; promoted mapping reviews: {len(pending_reviews)}; background leads: {len(background_leads)}")
    print(f"Health dimensions: {dimensions}; status: {status}")
    if args.require_certified and not complete:
        raise SystemExit("Operational census is not fully certified; inspect data/data_health.json")


if __name__ == "__main__":
    main()
