#!/usr/bin/env python3
"""Build public ABS market, centre, store-link, and network-history datasets."""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from openpyxl import load_workbook
except ImportError as exc:  # pragma: no cover - exercised by setup failures
    raise SystemExit("openpyxl is required. Run: python3 -m pip install -r requirements.txt") from exc


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CACHE_DIR = Path(os.environ.get("ABS_CACHE_DIR", ROOT / ".cache" / "market-intelligence"))
HISTORY_DIR = DATA_DIR / "history"
STORE_CSV = DATA_DIR / "optical_stores.csv"
SA2_OUTPUT = DATA_DIR / "sa2_market.geojson"
STORE_LINK_OUTPUT = DATA_DIR / "store_market_links.json"
CENTRE_OUTPUT = DATA_DIR / "centres.json"
EVENT_OUTPUT = DATA_DIR / "network_events.json"
PROFILE_CSV = DATA_DIR / "centre_profiles.csv"
BRAND_PROFILES = DATA_DIR / "brand_profiles.json"

ABS_RELEASE_DATE = "2026-05-26"
ABS_BASE = "https://www.abs.gov.au/methodologies/data-region-methodology/2011-25"
ABS_FILES = {
    "population": f"{ABS_BASE}/14100DO0001_2011-25.xlsx",
    "economy": f"{ABS_BASE}/14100DO0003_2011-25.xlsx",
    "income": f"{ABS_BASE}/14100DO0004_2011-25.xlsx",
    "employment": f"{ABS_BASE}/14100DO0005_2011-25.xlsx",
}
SA2_SERVICE = "https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/SA2/FeatureServer/0/query"


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def download(url: str, target: Path) -> None:
    if target.exists() and target.stat().st_size > 100_000:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Optical leasing intelligence builder/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)


def number(value):
    if value in (None, "", "-", "np", "n.p.", "na", "n.a."):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def whole_or_decimal(value):
    if value is None:
        return None
    return int(value) if float(value).is_integer() else round(float(value), 2)


def workbook_rows(path: Path, years: set[int], columns: dict[str, int]) -> dict[str, dict[int, dict]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook["Table 1"]
    results: dict[str, dict[int, dict]] = defaultdict(dict)
    for row in sheet.iter_rows(min_row=8, values_only=True):
        code = str(row[0] or "").strip()
        year = int(row[2]) if isinstance(row[2], (int, float)) else None
        if len(code) != 9 or year not in years:
            continue
        results[code][year] = {name: number(row[index]) for name, index in columns.items()}
    workbook.close()
    return results


def fetch_sa2_boundaries() -> list[dict]:
    features = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": (
                "sa2_code_2021,sa2_name_2021,state_code_2021,"
                "state_name_2021,area_albers_sqkm"
            ),
            "returnGeometry": "true",
            "outSR": "4326",
            "maxAllowableOffset": "0.01",
            "resultOffset": str(offset),
            "resultRecordCount": "2000",
            "f": "geojson",
        }
        request = urllib.request.Request(
            f"{SA2_SERVICE}?{urllib.parse.urlencode(params)}",
            headers={"User-Agent": "Optical leasing intelligence builder/1.0"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            page = json.load(response)
        if page.get("error"):
            raise RuntimeError(f"ABS SA2 service failed: {page['error']}")
        batch = page.get("features", [])
        features.extend(batch)
        if not page.get("exceededTransferLimit") or not batch:
            break
        offset += len(batch)
    unique = {feature["properties"]["sa2_code_2021"]: feature for feature in features}
    return [unique[key] for key in sorted(unique)]


def iter_points(coordinates):
    if not coordinates:
        return
    first = coordinates[0]
    if isinstance(first, (int, float)):
        yield coordinates
    else:
        for child in coordinates:
            yield from iter_points(child)


def geometry_bounds(geometry: dict) -> tuple[float, float, float, float]:
    points = list(iter_points(geometry["coordinates"]))
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def geometry_centre(geometry: dict) -> tuple[float, float]:
    min_x, min_y, max_x, max_y = geometry_bounds(geometry)
    return round((min_x + max_x) / 2, 5), round((min_y + max_y) / 2, 5)


def point_in_ring(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > latitude) != (y2 > latitude):
            boundary_x = (x2 - x1) * (latitude - y1) / ((y2 - y1) or 1e-12) + x1
            if longitude < boundary_x:
                inside = not inside
        previous = current
    return inside


def point_in_geometry(longitude: float, latitude: float, geometry: dict) -> bool:
    polygons = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        polygons = [polygons]
    for polygon in polygons:
        if polygon and point_in_ring(longitude, latitude, polygon[0]):
            if not any(point_in_ring(longitude, latitude, hole) for hole in polygon[1:]):
                return True
    return False


def build_market_features() -> list[dict]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, url in ABS_FILES.items():
        paths[name] = CACHE_DIR / f"abs-{name}.xlsx"
        download(url, paths[name])

    population = workbook_rows(
        paths["population"],
        {2021, 2025},
        {
            "population": 3,
            "density": 4,
            "median_age": 9,
            "age_45_49_pct": 111,
            "age_50_54_pct": 112,
            "age_55_59_pct": 113,
            "age_60_64_pct": 114,
            "age_65_69_pct": 115,
            "age_70_74_pct": 116,
            "age_75_79_pct": 117,
            "age_80_84_pct": 118,
            "age_85_plus_pct": 119,
        },
    )
    economy = workbook_rows(
        paths["economy"],
        {2025},
        {"total_businesses": 7, "retail_businesses": 14, "health_businesses": 24},
    )
    income = workbook_rows(
        paths["income"],
        {2021},
        {"median_household_income_weekly": 11},
    )
    employment = workbook_rows(
        paths["employment"],
        {2021},
        {"unemployment_rate": 53, "participation_rate": 54},
    )

    market_features = []
    for feature in fetch_sa2_boundaries():
        if not feature.get("geometry"):
            continue
        properties = feature["properties"]
        code = properties["sa2_code_2021"]
        current = population.get(code, {}).get(2025, {})
        baseline = population.get(code, {}).get(2021, {})
        census = population.get(code, {}).get(2021, {})
        population_current = current.get("population")
        population_baseline = baseline.get("population")
        growth = None
        if population_current is not None and population_baseline not in (None, 0):
            growth = (population_current / population_baseline - 1) * 100
        age_values = [
            census.get(key)
            for key in (
                "age_45_49_pct",
                "age_50_54_pct",
                "age_55_59_pct",
                "age_60_64_pct",
                "age_65_69_pct",
                "age_70_74_pct",
                "age_75_79_pct",
                "age_80_84_pct",
                "age_85_plus_pct",
            )
        ]
        age_45_plus = sum(value for value in age_values if value is not None) if any(
            value is not None for value in age_values
        ) else None
        centre_lon, centre_lat = geometry_centre(feature["geometry"])
        market_features.append(
            {
                "type": "Feature",
                "geometry": feature["geometry"],
                "properties": {
                    "sa2_code": code,
                    "sa2_name": properties["sa2_name_2021"],
                    "state": properties["state_name_2021"],
                    "area_sqkm": whole_or_decimal(properties.get("area_albers_sqkm")),
                    "centroid_longitude": centre_lon,
                    "centroid_latitude": centre_lat,
                    "population_2025": whole_or_decimal(population_current),
                    "population_growth_2021_2025_pct": whole_or_decimal(growth),
                    "population_density_2025": whole_or_decimal(current.get("density")),
                    "median_age_2021": whole_or_decimal(census.get("median_age")),
                    "age_45_plus_pct_2021": whole_or_decimal(age_45_plus),
                    "median_household_income_weekly_2021": whole_or_decimal(
                        income.get(code, {}).get(2021, {}).get("median_household_income_weekly")
                    ),
                    "unemployment_rate_2021": whole_or_decimal(
                        employment.get(code, {}).get(2021, {}).get("unemployment_rate")
                    ),
                    "participation_rate_2021": whole_or_decimal(
                        employment.get(code, {}).get(2021, {}).get("participation_rate")
                    ),
                    "total_businesses_2025": whole_or_decimal(
                        economy.get(code, {}).get(2025, {}).get("total_businesses")
                    ),
                    "retail_businesses_2025": whole_or_decimal(
                        economy.get(code, {}).get(2025, {}).get("retail_businesses")
                    ),
                    "health_businesses_2025": whole_or_decimal(
                        economy.get(code, {}).get(2025, {}).get("health_businesses")
                    ),
                    "source": "Australian Bureau of Statistics Data by Region 2011-25",
                    "source_url": ABS_BASE,
                    "source_release_date": ABS_RELEASE_DATE,
                    "confidence": "High",
                },
            }
        )
    return market_features


def query_sa2_for_point(longitude: float, latitude: float) -> dict:
    params = {
        "where": "1=1",
        "geometry": f"{longitude},{latitude}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "sa2_code_2021,sa2_name_2021",
        "returnGeometry": "false",
        "f": "json",
    }
    request = urllib.request.Request(
        f"{SA2_SERVICE}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "Optical leasing intelligence builder/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    matches = payload.get("features", [])
    return matches[0]["attributes"] if matches else {}


def link_stores_to_market(stores: list[dict], features: list[dict]) -> dict[str, dict]:
    spatial = []
    for feature in features:
        spatial.append((geometry_bounds(feature["geometry"]), feature))
    links = {}
    for store in stores:
        longitude = float(store["longitude"])
        latitude = float(store["latitude"])
        match = None
        for bounds, feature in spatial:
            min_x, min_y, max_x, max_y = bounds
            if min_x <= longitude <= max_x and min_y <= latitude <= max_y:
                if point_in_geometry(longitude, latitude, feature["geometry"]):
                    match = feature
                    break
        exact = {}
        if not match:
            exact = query_sa2_for_point(longitude, latitude)
        links[store["store_id"]] = {
            "sa2_code": (
                match["properties"]["sa2_code"]
                if match
                else exact.get("sa2_code_2021", "")
            ),
            "sa2_name": (
                match["properties"]["sa2_name"]
                if match
                else exact.get("sa2_name_2021", "")
            ),
            "match_confidence": "High" if match or exact else "Unmatched",
        }
    return links


def build_centres(stores: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for store in stores:
        if store.get("venue_id"):
            grouped[store["venue_id"]].append(store)
    overrides = {row["venue_id"]: row for row in read_csv(PROFILE_CSV)}
    centres = []
    for venue_id, members in sorted(grouped.items()):
        override = overrides.get(venue_id, {})
        venue_name = members[0]["venue_name"]
        manager = override.get("manager", "")
        public_url = override.get("public_url", "")
        confidence = override.get("confidence", "")
        if not manager and "westfield" in venue_name.lower():
            manager = "Scentre Group"
            public_url = "https://www.westfield.com.au/"
            confidence = "Medium"
        if not manager and "stockland" in venue_name.lower():
            manager = "Stockland"
            public_url = "https://www.stockland.com.au/shopping-centres"
            confidence = "Medium"
        centres.append(
            {
                "centre_id": venue_id,
                "name": venue_name,
                "state": members[0]["state"],
                "suburb": members[0]["suburb"],
                "latitude": round(sum(float(item["latitude"]) for item in members) / len(members), 6),
                "longitude": round(sum(float(item["longitude"]) for item in members) / len(members), 6),
                "retailers": sorted({item["retailer"] for item in members}),
                "optical_store_count": len(members),
                "owner": override.get("owner", ""),
                "manager": manager,
                "centre_type": override.get("centre_type", ""),
                "gla_sqm": whole_or_decimal(number(override.get("gla_sqm"))),
                "annual_visits": whole_or_decimal(number(override.get("annual_visits"))),
                "trade_area_population": whole_or_decimal(number(override.get("trade_area_population"))),
                "anchors": [item.strip() for item in override.get("anchors", "").split(";") if item.strip()],
                "tenancy_count": whole_or_decimal(number(override.get("tenancy_count"))),
                "redevelopment_activity": override.get("redevelopment_activity", ""),
                "leasing_contact": override.get("leasing_contact", ""),
                "public_url": public_url,
                "metrics_date": override.get("metrics_date", ""),
                "confidence": confidence or "Base",
                "source_basis": (
                    "Curated public centre profile"
                    if override
                    else "Centre entity derived from reviewed store venue IDs"
                ),
            }
        )
    return centres


def haversine(first: dict, second: dict) -> float:
    radius = 6371.0088
    lat1 = math.radians(float(first["latitude"]))
    lat2 = math.radians(float(second["latitude"]))
    delta_lat = math.radians(float(second["latitude"]) - float(first["latitude"]))
    delta_lon = math.radians(float(second["longitude"]) - float(first["longitude"]))
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def build_history(stores: list[dict]) -> dict:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_date = max(str(store["fetched_at"])[:10] for store in stores)
    snapshot_path = HISTORY_DIR / f"{snapshot_date}.json"
    current = {
        store["store_id"]: {
            key: store.get(key, "")
            for key in (
                "store_id",
                "retailer",
                "name",
                "status",
                "state",
                "suburb",
                "full_address",
                "latitude",
                "longitude",
                "venue_id",
            )
        }
        for store in stores
    }
    prior_paths = [path for path in sorted(HISTORY_DIR.glob("*.json")) if path != snapshot_path]
    events = []
    baseline_date = snapshot_date
    if prior_paths:
        prior_payload = json.loads(prior_paths[-1].read_text(encoding="utf-8"))
        prior = prior_payload["stores"]
        baseline_date = prior_payload["snapshot_date"]
        for store_id in sorted(current.keys() - prior.keys()):
            events.append({"type": "Opened", "date": snapshot_date, **current[store_id]})
        for store_id in sorted(prior.keys() - current.keys()):
            events.append({"type": "Closed", "date": snapshot_date, **prior[store_id]})
        for store_id in sorted(current.keys() & prior.keys()):
            before = prior[store_id]
            after = current[store_id]
            moved = haversine(before, after) >= 0.1 or before["full_address"] != after["full_address"]
            if moved:
                events.append(
                    {
                        "type": "Relocated",
                        "date": snapshot_date,
                        **after,
                        "previous_address": before["full_address"],
                        "distance_moved_km": round(haversine(before, after), 2),
                    }
                )
    snapshot_path.write_text(
        json.dumps({"snapshot_date": snapshot_date, "stores": current}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "baseline_date": baseline_date,
        "current_snapshot_date": snapshot_date,
        "event_count": len(events),
        "events": events,
        "note": (
            "This is the first archived baseline; changes will appear after the next successful refresh."
            if not prior_paths
            else "Events compare the current network with the latest prior successful snapshot."
        ),
    }


def main() -> None:
    if not STORE_CSV.exists() or not BRAND_PROFILES.exists():
        raise SystemExit("Run scripts/build_optical_network.py before building market intelligence.")
    stores = read_csv(STORE_CSV)
    features = build_market_features()
    links = link_stores_to_market(stores, features)
    centres = build_centres(stores)
    history = build_history(stores)

    SA2_OUTPUT.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "metadata": {
                    "name": "ABS SA2 leasing market indicators",
                    "feature_count": len(features),
                    "source": "Australian Bureau of Statistics Data by Region 2011-25",
                    "source_url": ABS_BASE,
                    "source_release_date": ABS_RELEASE_DATE,
                    "boundary_source": SA2_SERVICE.rsplit("/query", 1)[0],
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                "features": features,
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    STORE_LINK_OUTPUT.write_text(
        json.dumps(
            {
                "metadata": {
                    "store_count": len(stores),
                    "matched_count": sum(bool(link["sa2_code"]) for link in links.values()),
                    "source_release_date": ABS_RELEASE_DATE,
                },
                "links": links,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    CENTRE_OUTPUT.write_text(
        json.dumps(
            {
                "metadata": {
                    "centre_count": len(centres),
                    "enriched_count": sum(centre["confidence"] == "High" for centre in centres),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                "centres": centres,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    EVENT_OUTPUT.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(features)} SA2 market features to {SA2_OUTPUT}")
    print(f"Matched {sum(bool(link['sa2_code']) for link in links.values())}/{len(stores)} stores to SA2")
    print(f"Wrote {len(centres)} reviewed centre entities")
    print(f"Archived network snapshot with {history['event_count']} change events")


if __name__ == "__main__":
    main()
