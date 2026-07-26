#!/usr/bin/env python3
"""Fetch New Zealand OPSM stores from its public store-locator endpoint."""

from __future__ import annotations

import csv
import json
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from fetch_opsm_stores import clean_store


ROOT = Path(__file__).resolve().parents[1]
RETAILER_DIR = ROOT / "retailers" / "opsm-nz"
ENDPOINT = (
    "https://www.opsm.co.nz/AjaxStoreLocatorSearch"
    "?storeId=10152&radius=5000&latitude=-41.2866&longitude=174.7756"
)
CSV_PATH = RETAILER_DIR / "stores.csv"
GEOJSON_PATH = RETAILER_DIR / "stores.geojson"
SNAPSHOT_PATH = RETAILER_DIR / "source_snapshot.json"
FIELDS = [
    "name",
    "sap_id",
    "identifier",
    "country",
    "state",
    "city",
    "postal_code",
    "full_address",
    "phone",
    "latitude",
    "longitude",
    "services",
    "hours",
    "official_url",
    "status",
    "audiology",
]
REGION_NAMES = {
    "AKL": "Auckland",
    "AUK": "Auckland",
    "BOP": "Bay of Plenty",
    "CAN": "Canterbury",
    "CHC": "Canterbury",
    "GIS": "Gisborne",
    "HAB": "Hawke's Bay",
    "MBH": "Marlborough",
    "MWT": "Manawatu-Whanganui",
    "NLS": "Nelson",
    "NTL": "Northland",
    "OTA": "Otago",
    "STL": "Southland",
    "TAR": "Taranaki",
    "WAI": "Waikato",
    "WLG": "Wellington",
}


def fetch_json() -> dict:
    request = urllib.request.Request(
        ENDPOINT,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/plain,*/*"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def normalise(store: dict) -> dict:
    cleaned = clean_store(store)
    cleaned["state"] = REGION_NAMES.get(cleaned["state"], cleaned["state"])
    cleaned.update(
        {
            "country": "New Zealand",
            "official_url": "https://www.opsm.co.nz/find-store",
            "status": "Active",
            "audiology": str("audiology" in cleaned["services"].lower()).lower(),
        }
    )
    return cleaned


def validate(stores: list[dict]) -> None:
    if not 45 <= len(stores) <= 75:
        raise ValueError(f"Unexpected OPSM New Zealand count: {len(stores)}")
    ids = [store["sap_id"] or store["identifier"] for store in stores]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate OPSM New Zealand store IDs")
    if Counter(store["country"] for store in stores) != {"New Zealand": len(stores)}:
        raise ValueError("Unexpected OPSM New Zealand country data")
    for store in stores:
        if not (-48 <= store["latitude"] <= -33.5 and 165 <= store["longitude"] <= 179.5):
            raise ValueError(f"Invalid OPSM New Zealand coordinates: {store['identifier']}")


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = fetch_json()
    stores = [
        normalise(item)
        for item in payload.get("physicalStoreList", [])
        if item["locationInfo"]["address"].get("country") == "NZ"
    ]
    stores.sort(key=lambda store: (store["state"], store["city"], store["name"]))
    validate(stores)
    RETAILER_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: store.get(field, "") for field in FIELDS} for store in stores)
    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [store["longitude"], store["latitude"]],
            },
            "properties": {
                field: store.get(field, "")
                for field in FIELDS
                if field not in {"latitude", "longitude"}
            },
        }
        for store in stores
    ]
    GEOJSON_PATH.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "metadata": {
                    "retailer": "OPSM",
                    "countries": ["New Zealand"],
                    "source_url": ENDPOINT,
                    "fetched_at": fetched_at,
                    "store_count": len(stores),
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
                "source_url": ENDPOINT,
                "fetched_at": fetched_at,
                "store_count": len(stores),
                "collection_method": "Official OPSM store-locator endpoint",
                "payload": payload,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(stores)} validated OPSM New Zealand stores")


if __name__ == "__main__":
    main()
