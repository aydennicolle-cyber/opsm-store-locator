#!/usr/bin/env python3
"""Fetch Australian City Beach stores from the public City Beach locator endpoint."""

from __future__ import annotations

import csv
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RETAILER_ROOT = ROOT / "retailers" / "city-beach"
ENDPOINT = "https://www.citybeach.com/on/demandware.store/Sites-CityBeachAustralia-Site/en_AU/Stores-FindStores"
QUERY = {
    "showMap": "false",
    "postalCode": "4000",
    "radius": "5000",
}
SOURCE_URL = f"{ENDPOINT}?{urllib.parse.urlencode(QUERY)}"
STATE_CODES = {
    "Australian Capital Territory": "ACT",
    "New South Wales": "NSW",
    "Northern Territory": "NT",
    "Queensland": "QLD",
    "South Australia": "SA",
    "Tasmania": "TAS",
    "Victoria": "VIC",
    "Western Australia": "WA",
}

CSV_PATH = RETAILER_ROOT / "stores.csv"
GEOJSON_PATH = RETAILER_ROOT / "stores.geojson"
RAW_PATH = RETAILER_ROOT / "city_beach_store_locator_raw.json"


def text_from_html(value: str) -> str:
    without_comments = re.sub(r"<!--.*?-->", "", value or "", flags=re.DOTALL)
    with_separators = without_comments.replace("<br>", "; ").replace("<br/>", "; ").replace("<br />", "; ")
    cleaned = re.sub(r"<[^>]+>", "", with_separators)
    return re.sub(r"\s+", " ", unescape(cleaned)).strip(" ;")


def clean_part(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_state(value: object) -> str:
    state = clean_part(value)
    return STATE_CODES.get(state, state)


def fetch_json() -> dict:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_store(store: dict) -> dict:
    state = normalize_state(store.get("stateCode"))
    address_parts = [
        clean_part(store.get("address1")),
        clean_part(store.get("address2")),
        clean_part(store.get("city")),
        state,
        clean_part(store.get("postalCode")),
    ]
    services = ["Official City Beach store"]
    if store.get("availableForPickUp"):
        services.append("Click & Collect")

    return {
        "name": clean_part(store.get("name")),
        "id": clean_part(store.get("ID")),
        "state": state,
        "city": clean_part(store.get("city")),
        "postal_code": clean_part(store.get("postalCode")),
        "full_address": ", ".join(part for part in address_parts if part),
        "phone": clean_part(store.get("phone")),
        "latitude": float(store["latitude"]),
        "longitude": float(store["longitude"]),
        "services": ", ".join(services),
        "hours": text_from_html(store.get("storeHours", "")),
    }


def write_csv(stores: list[dict]) -> None:
    fields = [
        "name",
        "id",
        "state",
        "city",
        "postal_code",
        "full_address",
        "phone",
        "latitude",
        "longitude",
        "services",
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: store.get(field, "") for field in fields} for store in stores)


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

    GEOJSON_PATH.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "metadata": {
                    "retailer": "City Beach",
                    "brand_context": "Rhythm",
                    "source": SOURCE_URL,
                    "source_page": "https://www.citybeach.com/au/stores",
                    "fetched_at": fetched_at,
                    "geography_filter": "Australia",
                    "store_count": len(stores),
                },
                "features": features,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    RETAILER_ROOT.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    raw = fetch_json()
    RAW_PATH.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    stores_by_id = {}
    for item in raw.get("stores", []):
        if item.get("countryCode") != "AU":
            continue
        cleaned = clean_store(item)
        if not cleaned["id"] or not cleaned["latitude"] or not cleaned["longitude"]:
            continue
        stores_by_id[cleaned["id"]] = cleaned

    stores = sorted(stores_by_id.values(), key=lambda item: (item["state"], item["city"], item["name"]))
    write_csv(stores)
    write_geojson(stores, fetched_at)

    by_state: dict[str, int] = {}
    for store in stores:
        by_state[store["state"]] = by_state.get(store["state"], 0) + 1

    print(f"Fetched {len(raw.get('stores', []))} stores from City Beach.")
    print(f"Wrote {len(stores)} Australian stores.")
    print(", ".join(f"{state}: {count}" for state, count in sorted(by_state.items())))
    print(f"CSV: {CSV_PATH}")
    print(f"GeoJSON: {GEOJSON_PATH}")


if __name__ == "__main__":
    main()
