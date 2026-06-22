#!/usr/bin/env python3
"""Fetch Australian Ozmosis stores from the public Stockinstore locator endpoint."""

from __future__ import annotations

import csv
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RETAILER_ROOT = ROOT / "retailers" / "ozmosis"
ENDPOINT = "https://stockinstore.net/stores/getAllStores"
SOURCE_PAGE = "https://www.ozmosis.com.au/pages/stores"
POST_DATA = {
    "site": "10326",
    "storeid": "",
    "widget": "330",
    "lang": "en",
    "widgetType": "storelocator",
    "isajax": "1",
    "info": "none",
    "preview": "false",
}

CSV_PATH = RETAILER_ROOT / "stores.csv"
GEOJSON_PATH = RETAILER_ROOT / "stores.geojson"
RAW_PATH = RETAILER_ROOT / "ozmosis_store_locator_raw.json"


def clean_part(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def fetch_json() -> dict:
    body = urllib.parse.urlencode(POST_DATA).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.ozmosis.com.au",
            "Referer": SOURCE_PAGE,
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_store(store: dict) -> dict:
    state = clean_part(store.get("state") or store.get("region_code"))
    city = clean_part(store.get("city"))
    postal_code = clean_part(store.get("postcode"))
    address_parts = [clean_part(part) for part in store.get("address_lines") or []]
    address_parts.extend([city, state, postal_code])

    services = ["Official Ozmosis store"]
    if clean_part(store.get("is_cnc_fulfiller")) == "1":
        services.append("Click & Collect")

    return {
        "name": clean_part(store.get("store_name") or store.get("label") or store.get("name")),
        "id": clean_part(store.get("code") or store.get("id")),
        "state": state,
        "city": city,
        "postal_code": postal_code,
        "full_address": ", ".join(part for part in address_parts if part),
        "phone": clean_part(store.get("phone")),
        "latitude": float(store.get("latitude") or store.get("store_latitude")),
        "longitude": float(store.get("longitude") or store.get("store_longitude")),
        "services": ", ".join(services),
        "store_url": urllib.parse.urljoin(SOURCE_PAGE, clean_part(store.get("store_locator_page_url"))),
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
                    "retailer": "Ozmosis",
                    "brand_context": "Rhythm",
                    "source": ENDPOINT,
                    "source_page": SOURCE_PAGE,
                    "source_post_data": POST_DATA,
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
    for item in raw.get("response", {}).get("stores_list", []):
        if item.get("country_code") != "AU":
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

    print(f"Fetched {len(raw.get('response', {}).get('stores_list', []))} stores from Ozmosis.")
    print(f"Wrote {len(stores)} Australian stores.")
    print(", ".join(f"{state}: {count}" for state, count in sorted(by_state.items())))
    print(f"CSV: {CSV_PATH}")
    print(f"GeoJSON: {GEOJSON_PATH}")


if __name__ == "__main__":
    main()
