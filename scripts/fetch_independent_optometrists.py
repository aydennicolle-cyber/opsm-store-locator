#!/usr/bin/env python3
"""Import public OpenStreetMap optician locations for Australia and New Zealand."""

from __future__ import annotations

import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "retailers" / "independent-other"
SNAPSHOT_PATH = OUTPUT_DIR / "source_snapshot.json"
CSV_PATH = OUTPUT_DIR / "stores.csv"
GEOJSON_PATH = OUTPUT_DIR / "stores.geojson"
OVERPASS_URLS = [
    os.environ.get("OVERPASS_URL", "https://overpass-api.de/api/interpreter"),
    "https://overpass.kumi.systems/api/interpreter",
]
NZ_BOUNDARIES_URL = (
    "https://services2.arcgis.com/vKb0s8tBIA3bdocZ/arcgis/rest/services/"
    "Regional_Council_2025/FeatureServer/0/query"
    "?where=1%3D1&outFields=REGC2025_V1_00_NAME&returnGeometry=true&outSR=4326&f=geojson"
)
NZ_BOUNDARIES_CACHE = ROOT / ".cache" / "market-intelligence" / "nz-regions-2025.geojson"
AU_SA2_PATH = ROOT / "data" / "sa2_market.geojson"
AU_REGIONS = {
    "ACT": "AU-ACT",
    "NSW": "AU-NSW",
    "NT": "AU-NT",
    "QLD": "AU-QLD",
    "SA": "AU-SA",
    "TAS": "AU-TAS",
    "VIC": "AU-VIC",
    "WA": "AU-WA",
}
NZ_REGIONS = [
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
]
MAJOR_BRAND = re.compile(
    r"\b(?:opsm|specsavers|bailey[\s&-]*(?:and[\s-]*)?nelson|oscar[\s-]*wylee)\b",
    flags=re.IGNORECASE,
)
NON_COMPARABLE = re.compile(
    r"\b(?:sunglass(?:es)?\s+(?:hut|style|shack)|eyewear\s+glasses\s+repair|ophthalmolog|eye\s+surgery|laser\s+eye)\b",
    flags=re.IGNORECASE,
)


def tidy(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def social_url(value: object, network: str) -> str:
    """Return a public social URL without guessing an account from a store name."""
    raw = tidy(value)
    if not raw:
        return ""
    if raw.startswith(("https://", "http://")):
        return raw
    handle = raw.lstrip("@").strip("/")
    if not handle or any(character.isspace() for character in handle):
        return ""
    domains = {
        "instagram": "https://www.instagram.com/",
        "facebook": "https://www.facebook.com/",
    }
    return f"{domains[network]}{handle}/"


def overpass(query: str) -> dict:
    encoded = urllib.parse.urlencode({"data": query}).encode()
    last_error: Exception | None = None
    for attempt in range(4):
        endpoint = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
        request = urllib.request.Request(
            endpoint,
            data=encoded,
            headers={
                "User-Agent": "Optical leasing intelligence public-source importer/1.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
            time.sleep(2 + attempt * 3)
    raise RuntimeError(f"Overpass request failed after retries: {last_error}")


def query_country(country_code: str) -> dict:
    return overpass(
        f"""
        [out:json][timeout:180];
        area["ISO3166-1"="{country_code}"][admin_level="2"]->.searchArea;
        nwr["shop"="optician"](area.searchArea);
        out center tags;
        """
    )


def point_in_ring(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    inside = False
    previous = len(ring) - 1
    for index, point in enumerate(ring):
        first_x, first_y = point[:2]
        second_x, second_y = ring[previous][:2]
        crosses = (first_y > latitude) != (second_y > latitude)
        if crosses:
            boundary = (second_x - first_x) * (latitude - first_y) / (second_y - first_y) + first_x
            if longitude < boundary:
                inside = not inside
        previous = index
    return inside


def point_in_geometry(longitude: float, latitude: float, geometry: dict) -> bool:
    polygons = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        polygons = [polygons]
    for polygon in polygons:
        if point_in_ring(longitude, latitude, polygon[0]) and not any(
            point_in_ring(longitude, latitude, hole) for hole in polygon[1:]
        ):
            return True
    return False


def geometry_bounds(geometry: dict) -> tuple[float, float, float, float]:
    coordinates = geometry["coordinates"]
    while coordinates and isinstance(coordinates[0][0], list):
        coordinates = [point for group in coordinates for point in group]
    longitudes = [point[0] for point in coordinates]
    latitudes = [point[1] for point in coordinates]
    return min(longitudes), min(latitudes), max(longitudes), max(latitudes)


def fetch_nz_boundaries() -> list[tuple[tuple[float, float, float, float], dict, str]]:
    if not NZ_BOUNDARIES_CACHE.exists():
        NZ_BOUNDARIES_CACHE.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(
            NZ_BOUNDARIES_URL,
            headers={"User-Agent": "Optical leasing intelligence public-source importer/1.0"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            NZ_BOUNDARIES_CACHE.write_bytes(response.read())
    payload = json.loads(NZ_BOUNDARIES_CACHE.read_text(encoding="utf-8"))
    boundaries = []
    for feature in payload.get("features", []):
        raw_name = feature["properties"].get("REGC2025_V1_00_NAME", "")
        name = raw_name.removesuffix(" Region").replace("Manawatū", "Manawatu")
        if name in NZ_REGIONS:
            boundaries.append((geometry_bounds(feature["geometry"]), feature["geometry"], name))
    if len(boundaries) != 16:
        raise ValueError(f"Expected 16 New Zealand regions, found {len(boundaries)}")
    return boundaries


def assign_nz_region(
    latitude: float,
    longitude: float,
    boundaries: list[tuple[tuple[float, float, float, float], dict, str]],
) -> str:
    for bounds, geometry, name in boundaries:
        min_x, min_y, max_x, max_y = bounds
        if min_x <= longitude <= max_x and min_y <= latitude <= max_y:
            if point_in_geometry(longitude, latitude, geometry):
                return name
    return ""


def load_au_boundaries() -> list[tuple[tuple[float, float, float, float], dict, str]]:
    aliases = {
        "Australian Capital Territory": "ACT",
        "New South Wales": "NSW",
        "Northern Territory": "NT",
        "Queensland": "QLD",
        "South Australia": "SA",
        "Tasmania": "TAS",
        "Victoria": "VIC",
        "Western Australia": "WA",
    }
    if not AU_SA2_PATH.exists():
        return []
    payload = json.loads(AU_SA2_PATH.read_text(encoding="utf-8"))
    boundaries = []
    for feature in payload.get("features", []):
        state = aliases.get(feature["properties"].get("state", ""), "")
        if state:
            boundaries.append((geometry_bounds(feature["geometry"]), feature["geometry"], state))
    return boundaries


def assign_au_state(
    latitude: float,
    longitude: float,
    tags: dict,
    boundaries: list[tuple[tuple[float, float, float, float], dict, str]],
) -> str:
    for bounds, geometry, state in boundaries:
        min_x, min_y, max_x, max_y = bounds
        if min_x <= longitude <= max_x and min_y <= latitude <= max_y:
            if point_in_geometry(longitude, latitude, geometry):
                return state
    raw = tidy(tags.get("addr:state") or tags.get("is_in:state")).upper()
    aliases = {
        "AUSTRALIAN CAPITAL TERRITORY": "ACT",
        "NEW SOUTH WALES": "NSW",
        "NORTHERN TERRITORY": "NT",
        "QUEENSLAND": "QLD",
        "SOUTH AUSTRALIA": "SA",
        "TASMANIA": "TAS",
        "VICTORIA": "VIC",
        "WESTERN AUSTRALIA": "WA",
    }
    if raw in AU_REGIONS:
        return raw
    if raw in aliases:
        return aliases[raw]
    # Australian state boundaries are unambiguous at optical-store coordinates.
    if latitude < -39:
        return "TAS"
    if longitude < 129:
        return "WA"
    if longitude < 138:
        return "NT" if latitude > -26 else "SA"
    if longitude < 141:
        return "QLD" if latitude > -29 else "SA"
    if 148.75 < longitude < 149.45 and -35.95 < latitude < -35.1:
        return "ACT"
    if latitude > -29:
        return "QLD"
    if longitude < 141:
        return "SA"
    if latitude < -36:
        return "VIC"
    return "NSW"


def element_coordinates(element: dict) -> tuple[float, float]:
    point = element.get("center", element)
    return float(point["lat"]), float(point["lon"])


def address(tags: dict, country: str) -> str:
    house = tidy(tags.get("addr:housenumber"))
    street = tidy(tags.get("addr:street"))
    first = " ".join(part for part in (house, street) if part)
    parts = [
        first,
        tidy(tags.get("addr:suburb") or tags.get("addr:city") or tags.get("addr:town")),
        tidy(tags.get("addr:postcode")),
        country,
    ]
    return ", ".join(part for part in parts if part)


def clean_element(
    element: dict,
    country: str,
    region: str = "",
    au_boundaries: list[tuple[tuple[float, float, float, float], dict, str]] | None = None,
    nz_boundaries: list[tuple[tuple[float, float, float, float], dict, str]] | None = None,
) -> dict | None:
    tags = element.get("tags", {})
    name = tidy(tags.get("name") or tags.get("brand"))
    if not name or MAJOR_BRAND.search(name) or NON_COMPARABLE.search(name):
        return None
    latitude, longitude = element_coordinates(element)
    if country == "Australia" and not (-44.5 <= latitude <= -9 and 112 <= longitude <= 154.5):
        return None
    if country == "New Zealand" and not (-48 <= latitude <= -33.5 and 165 <= longitude <= 179.5):
        return None
    if country == "Australia":
        region = assign_au_state(latitude, longitude, tags, au_boundaries or [])
    elif nz_boundaries:
        region = assign_nz_region(latitude, longitude, nz_boundaries)
    if not region:
        return None
    element_type = element["type"]
    element_id = str(element["id"])
    source_url = f"https://www.openstreetmap.org/{element_type}/{element_id}"
    locality = tidy(
        tags.get("addr:suburb")
        or tags.get("addr:city")
        or tags.get("addr:town")
        or tags.get("addr:village")
    )
    phone = tidy(tags.get("contact:phone") or tags.get("phone"))
    website = tidy(tags.get("contact:website") or tags.get("website"))
    instagram = social_url(tags.get("contact:instagram") or tags.get("instagram"), "instagram")
    facebook = social_url(tags.get("contact:facebook") or tags.get("facebook"), "facebook")
    return {
        "id": f"osm-{country[:2].lower()}-{element_type}-{element_id}",
        "name": name,
        "status": "Mapped",
        "country": country,
        "state": region,
        "city": locality,
        "postal_code": tidy(tags.get("addr:postcode")),
        "full_address": address(tags, country) or locality or f"{latitude:.6f}, {longitude:.6f}",
        "phone": phone,
        "latitude": latitude,
        "longitude": longitude,
        "official_url": website,
        "website_url": website,
        "instagram_url": instagram,
        "facebook_url": facebook,
        "directory_url": "",
        "services": "Optical / optician listing",
        "audiology": "false",
        "source_url": source_url,
        "source_confidence": "Community-mapped",
    }


def collect() -> tuple[list[dict], list[dict]]:
    stores: dict[str, dict] = {}
    queries = []
    au_boundaries = load_au_boundaries()
    nz_boundaries = fetch_nz_boundaries()
    for country, code in (("Australia", "AU"), ("New Zealand", "NZ")):
        raw_path = OUTPUT_DIR / f"raw_source_{code.lower()}.json"
        if raw_path.exists() and os.environ.get("FORCE_REFRESH") != "1":
            print(f"Using saved {country} source snapshot...", flush=True)
            payload = json.loads(raw_path.read_text(encoding="utf-8"))
        else:
            print(f"Fetching {country} optical listings...", flush=True)
            payload = query_country(code)
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
        queries.append({"country": country, "elements": len(payload.get("elements", []))})
        for element in payload.get("elements", []):
            store = clean_element(
                element,
                country,
                au_boundaries=au_boundaries if country == "Australia" else None,
                nz_boundaries=nz_boundaries if country == "New Zealand" else None,
            )
            if store:
                stores[store["id"]] = store
    candidates = sorted(stores.values(), key=lambda row: (row["country"], row["state"], row["name"], row["id"]))
    rows = []
    for candidate in candidates:
        normalised_name = re.sub(r"[^a-z0-9]+", "", candidate["name"].lower())
        duplicate = next(
            (
                row
                for row in rows
                if row["country"] == candidate["country"]
                and row["state"] == candidate["state"]
                and re.sub(r"[^a-z0-9]+", "", row["name"].lower()) == normalised_name
                and abs(float(row["latitude"]) - float(candidate["latitude"])) <= 0.00045
                and abs(float(row["longitude"]) - float(candidate["longitude"])) <= 0.00055
            ),
            None,
        )
        if duplicate:
            continue
        rows.append(candidate)
    rows.sort(key=lambda row: (row["country"], row["state"], row["city"], row["name"]))
    return rows, queries


def validate(stores: list[dict]) -> None:
    if len(stores) < 300:
        raise ValueError(f"Independent/other optical count unexpectedly low: {len(stores)}")
    if len({store["id"] for store in stores}) != len(stores):
        raise ValueError("Duplicate OpenStreetMap element IDs")
    for store in stores:
        latitude = float(store["latitude"])
        longitude = float(store["longitude"])
        if store["country"] == "Australia":
            if store["state"] not in AU_REGIONS:
                raise ValueError(f"Invalid Australian state: {store['state']}")
            valid = -44.5 <= latitude <= -9 and 112 <= longitude <= 154.5
        else:
            if store["state"] not in NZ_REGIONS:
                raise ValueError(f"Invalid New Zealand region: {store['state']}")
            valid = -48 <= latitude <= -33.5 and 165 <= longitude <= 179.5
        if not valid:
            raise ValueError(f"Invalid coordinates for {store['name']}: {latitude}, {longitude}")


def write_outputs(stores: list[dict], queries: list[dict], fetched_at: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "id",
        "name",
        "status",
        "country",
        "state",
        "city",
        "postal_code",
        "full_address",
        "phone",
        "latitude",
        "longitude",
        "official_url",
        "website_url",
        "instagram_url",
        "facebook_url",
        "directory_url",
        "services",
        "audiology",
        "source_url",
        "source_confidence",
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(stores)
    features = []
    for store in stores:
        properties = {key: value for key, value in store.items() if key not in {"latitude", "longitude"}}
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [store["longitude"], store["latitude"]]},
                "properties": properties,
            }
        )
    GEOJSON_PATH.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "metadata": {
                    "retailer": "Independent / Other optical",
                    "source": "OpenStreetMap contributors",
                    "source_url": "https://www.openstreetmap.org/copyright",
                    "license": "ODbL 1.0",
                    "fetched_at": fetched_at,
                    "store_count": len(stores),
                    "coverage": "Community-mapped and non-exhaustive",
                },
                "features": features,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    SNAPSHOT_PATH.write_text(
        json.dumps(
            {
                "source": "OpenStreetMap contributors",
                "source_url": "https://www.openstreetmap.org/copyright",
                "license": "ODbL 1.0",
                "fetched_at": fetched_at,
                "store_count": len(stores),
                "profile_link_counts": {
                    "website": sum(bool(store["website_url"]) for store in stores),
                    "instagram": sum(bool(store["instagram_url"]) for store in stores),
                    "facebook": sum(bool(store["facebook_url"]) for store in stores),
                },
                "coverage": "Community-mapped shop=optician discovery records; non-exhaustive and subject to comparability review",
                "excluded_major_brands": [
                    "OPSM", "Specsavers", "Bailey Nelson", "Oscar Wylee",
                ],
                "excluded_non_comparable_patterns": ["sunglasses-only", "repair-only", "ophthalmology", "eye surgery", "laser eye"],
                "queries": queries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    cached_snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8")) if SNAPSHOT_PATH.exists() else {}
    using_saved_raw = (
        os.environ.get("FORCE_REFRESH") != "1"
        and all((OUTPUT_DIR / f"raw_source_{code}.json").exists() for code in ("au", "nz"))
    )
    stores, queries = collect()
    validate(stores)
    fetched_at = (
        tidy(cached_snapshot.get("fetched_at"))
        if using_saved_raw and cached_snapshot.get("fetched_at")
        else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    write_outputs(stores, queries, fetched_at)
    by_country: dict[str, int] = {}
    for store in stores:
        by_country[store["country"]] = by_country.get(store["country"], 0) + 1
    print(f"Wrote {len(stores)} independent/other optical locations.")
    print(", ".join(f"{country}: {count}" for country, count in sorted(by_country.items())))
    print(f"Data: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
