#!/usr/bin/env python3
"""Fetch Oscar Wylee Australia stores from its public location page."""

from __future__ import annotations

import csv
import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RETAILER_DIR = ROOT / "retailers" / "oscar-wylee"
LIST_URL = "https://www.oscarwylee.com.au/locations/"
USER_AGENT = "Mozilla/5.0 (compatible; AU NZ Optical Network Map/2.0)"
CSV_PATH = RETAILER_DIR / "stores.csv"
GEOJSON_PATH = RETAILER_DIR / "stores.geojson"
SNAPSHOT_PATH = RETAILER_DIR / "source_snapshot.json"
VALID_STATES = {"ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"}
ADDRESS_CORRECTIONS = {
    "127": {
        "full_address": "Rouse Hill Town Centre, Shop A-GR 015, White Hart Dr, Rouse Hill NSW 2155",
        "city": "Rouse Hill",
        "state": "NSW",
        "postal_code": "2155",
    }
}
FIELDS = [
    "name",
    "id",
    "country",
    "state",
    "city",
    "postal_code",
    "full_address",
    "phone",
    "latitude",
    "longitude",
    "official_url",
    "services",
    "audiology",
    "status",
]


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", "replace")


def tidy(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip(" ,")


def embedded_stores(page_html: str) -> list[dict]:
    match = re.search(
        r'"geo_json"\s*:\s*(\[.*?\])\s*,\s*"locationUrl"',
        page_html,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError("Oscar Wylee public store data was not found")
    value = json.loads(match.group(1))
    if not isinstance(value, list):
        raise ValueError("Oscar Wylee public store data is not a list")
    return value


def address_parts(value: str) -> tuple[str, str, str, str]:
    flattened = tidy(value)
    normalised = flattened
    for full_name, abbreviation in (
        ("Australian Capital Territory", "ACT"),
        ("New South Wales", "NSW"),
        ("Northern Territory", "NT"),
        ("Queensland", "QLD"),
        ("South Australia", "SA"),
        ("Tasmania", "TAS"),
        ("Victoria", "VIC"),
        ("Western Australia", "WA"),
    ):
        normalised = re.sub(rf"\b{full_name}\b", abbreviation, normalised, flags=re.IGNORECASE)
    matches = list(
        re.finditer(
            r"([A-Za-z][A-Za-z .'-]*?)[,\s]+(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)[,\s]+(\d{4})\b",
            normalised,
        )
    )
    if not matches:
        raise ValueError(f"State, suburb and postcode missing from address: {flattened}")
    locality = tidy(matches[-1].group(1))
    locality = re.split(r"\b(?:Road|Rd|Street|St|Highway|Hwy|Drive|Dr|Parade|Pde)\b", locality)[-1]
    locality = tidy(locality)
    return flattened, locality, matches[-1].group(2), matches[-1].group(3)


def clean_store(item: dict) -> dict:
    store_id = tidy(str(item.get("storeId", "")))
    correction = ADDRESS_CORRECTIONS.get(store_id)
    if correction:
        full_address = correction["full_address"]
        city = correction["city"]
        state = correction["state"]
        postcode = correction["postal_code"]
    else:
        full_address, city, state, postcode = address_parts(item.get("address", ""))
    location = item.get("Latlng") or {}
    official_url = urllib.parse.urljoin(LIST_URL, item.get("storeUrl", ""))
    return {
        "name": tidy(item.get("name", "")),
        "id": store_id,
        "country": "Australia",
        "state": state,
        "city": city,
        "postal_code": postcode,
        "full_address": full_address,
        "phone": tidy(item.get("phone", "")),
        "latitude": float(location["lat"]),
        "longitude": float(location["lng"]),
        "official_url": official_url,
        "services": "Comprehensive eye tests, Prescription glasses, Sunglasses",
        "audiology": "false",
        "status": "Active",
    }


def validate(stores: list[dict]) -> None:
    if not 110 <= len(stores) <= 150:
        raise ValueError(f"Unexpected Oscar Wylee Australia count: {len(stores)}")
    ids = [store["id"] for store in stores]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate Oscar Wylee store IDs")
    for store in stores:
        if not store["name"] or not store["id"] or store["state"] not in VALID_STATES:
            raise ValueError(f"Incomplete Oscar Wylee store: {store}")
        if not (-44.5 <= store["latitude"] <= -9 and 112 <= store["longitude"] <= 154.5):
            raise ValueError(f"Invalid Oscar Wylee coordinates: {store['id']}")


def write_csv(stores: list[dict]) -> None:
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(stores)


def write_geojson(stores: list[dict], fetched_at: str) -> None:
    features = []
    for store in stores:
        properties = {key: value for key, value in store.items() if key not in {"latitude", "longitude"}}
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [store["longitude"], store["latitude"]],
                },
                "properties": properties,
            }
        )
    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "retailer": "Oscar Wylee",
            "countries": ["Australia"],
            "source_url": LIST_URL,
            "fetched_at": fetched_at,
            "store_count": len(stores),
        },
        "features": features,
    }
    GEOJSON_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    page_html = fetch_text(LIST_URL)
    raw = embedded_stores(page_html)
    stores = [clean_store(item) for item in raw]
    stores.sort(key=lambda store: (store["state"], store["city"], store["name"]))
    validate(stores)
    RETAILER_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(stores)
    write_geojson(stores, fetched_at)
    SNAPSHOT_PATH.write_text(
        json.dumps(
            {
                "source_url": LIST_URL,
                "fetched_at": fetched_at,
                "store_count": len(stores),
                "collection_method": "Official embedded store-locator data",
                "stores": raw,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(stores)} validated Oscar Wylee Australia stores")


if __name__ == "__main__":
    main()
