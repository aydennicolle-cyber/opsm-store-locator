#!/usr/bin/env python3
"""Fetch Australian OPSM stores from the public OPSM store locator endpoint."""

from __future__ import annotations

import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = (
    "https://www.opsm.com.au/AjaxStoreLocatorSearch"
    "?storeId=10151&radius=5000&latitude=-25.2744&longitude=133.7751"
)

CSV_PATH = ROOT / "opsm_stores.csv"
GEOJSON_PATH = ROOT / "opsm_stores.geojson"
RAW_PATH = ROOT / "opsm_store_locator_raw.json"
RETAILER_DIR = ROOT / "retailers" / "opsm"
RETAILER_CSV_PATH = RETAILER_DIR / "stores.csv"
RETAILER_GEOJSON_PATH = RETAILER_DIR / "stores.geojson"
RETAILER_RAW_PATH = RETAILER_DIR / "source_snapshot.json"


def attr_map(store: dict) -> dict[str, str]:
    return {item.get("name", ""): item.get("value", "") for item in store.get("attribute", [])}


def format_hours(raw_hours: str) -> str:
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    slots = raw_hours.split(";") if raw_hours else []
    output = []
    for index, day in enumerate(days):
        start_index = index * 2
        start = slots[start_index] if start_index < len(slots) else ""
        end = slots[start_index + 1] if start_index + 1 < len(slots) else ""
        if not start or start == "closed":
            output.append(f"{day}: closed")
        elif end:
            output.append(f"{day}: {start}-{end}")
    return "; ".join(output)


def service_list(attrs: dict[str, str]) -> list[str]:
    services = []
    if attrs.get("StoreAudio") == "true":
        services.append("Audiology")
    if attrs.get("StoreDryEye") == "true":
        services.append("Dry Eye")
    if attrs.get("StoreKids") == "true":
        services.append("Kids Vision Centre")
    if attrs.get("StoreBoss") == "true" and attrs.get("StoreBoris") == "true":
        services.append("Collect & Return")
    elif attrs.get("StoreBoss") == "true":
        services.append("Collect")
    elif attrs.get("StoreBoris") == "true":
        services.append("Return")
    return services


def clean_store(store: dict) -> dict:
    info = store["locationInfo"]
    address = info["address"]
    attrs = attr_map(store)
    services = service_list(attrs)
    address_parts = [
        address.get("address1", ""),
        address.get("address2", ""),
        address.get("address3", ""),
        address.get("city", ""),
        address.get("stateOrProvinceName", ""),
        address.get("postalCode", ""),
    ]
    return {
        "identifier": store.get("identifier", ""),
        "sap_id": attrs.get("StoreSAPId", ""),
        "name": store["description"][0]["name"],
        "address_1": address.get("address1", ""),
        "address_2": address.get("address2", ""),
        "address_3": address.get("address3", ""),
        "city": address.get("city", ""),
        "state": address.get("stateOrProvinceName", ""),
        "postal_code": address.get("postalCode", ""),
        "country": address.get("country", ""),
        "phone": info.get("telephone", {}).get("phone", ""),
        "fax": info.get("telephone", {}).get("fax", ""),
        "latitude": float(info["geoCode"]["latitude"]),
        "longitude": float(info["geoCode"]["longitude"]),
        "services": ", ".join(services),
        "hours": format_hours(attrs.get("StoreHours", "")),
        "full_address": ", ".join(part for part in address_parts if part),
    }


def fetch_json() -> dict:
    request = urllib.request.Request(
        ENDPOINT,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def write_csv(stores: list[dict], path: Path) -> None:
    fields = [
        "name",
        "sap_id",
        "identifier",
        "state",
        "city",
        "postal_code",
        "address_1",
        "address_2",
        "address_3",
        "full_address",
        "phone",
        "fax",
        "latitude",
        "longitude",
        "services",
        "hours",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: store.get(field, "") for field in fields} for store in stores)


def write_geojson(stores: list[dict], fetched_at: str, path: Path) -> None:
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

    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "metadata": {
                    "source": ENDPOINT,
                    "fetched_at": fetched_at,
                    "country_filter": "AU",
                    "store_count": len(stores),
                },
                "features": features,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    raw = fetch_json()
    RETAILER_DIR.mkdir(parents=True, exist_ok=True)
    raw_text = json.dumps(raw, indent=2)
    RAW_PATH.write_text(raw_text, encoding="utf-8")
    RETAILER_RAW_PATH.write_text(raw_text, encoding="utf-8")

    seen = set()
    stores = []
    for item in raw.get("physicalStoreList", []):
        if item["locationInfo"]["address"].get("country") != "AU":
            continue
        cleaned = clean_store(item)
        key = cleaned["sap_id"] or cleaned["identifier"]
        if key in seen:
            continue
        seen.add(key)
        stores.append(cleaned)

    stores.sort(key=lambda item: (item["state"], item["city"], item["name"]))
    write_csv(stores, CSV_PATH)
    write_csv(stores, RETAILER_CSV_PATH)
    write_geojson(stores, fetched_at, GEOJSON_PATH)
    write_geojson(stores, fetched_at, RETAILER_GEOJSON_PATH)

    by_state: dict[str, int] = {}
    for store in stores:
        by_state[store["state"]] = by_state.get(store["state"], 0) + 1

    print(f"Fetched {len(raw.get('physicalStoreList', []))} locations from OPSM.")
    print(f"Wrote {len(stores)} Australian stores.")
    print(", ".join(f"{state}: {count}" for state, count in sorted(by_state.items())))
    print(f"CSV: {CSV_PATH}")
    print(f"GeoJSON: {GEOJSON_PATH}")
    print(f"Retailer map data: {RETAILER_DIR}")


if __name__ == "__main__":
    main()
