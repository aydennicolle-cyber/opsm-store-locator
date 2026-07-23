#!/usr/bin/env python3
"""Build Specsavers CSV and GeoJSON from a validated browser snapshot."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RETAILER_DIR = ROOT / "retailers" / "specsavers"
SNAPSHOT_PATH = RETAILER_DIR / "source_snapshot.json"
CSV_PATH = RETAILER_DIR / "stores.csv"
GEOJSON_PATH = RETAILER_DIR / "stores.geojson"
VALID_STATES = {"ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"}


def property_map(data: dict) -> dict:
    return {
        item.get("name", ""): item.get("value", "")
        for item in data.get("additionalProperty", [])
        if isinstance(item, dict)
    }


def clean_store(item: dict) -> dict:
    data = item["data"]
    address = data.get("address", {})
    geo = data.get("geo", {})
    properties = property_map(data)
    has_audiology = bool(properties.get("hasAudiology"))
    services = ["Optometry"]
    if has_audiology:
        services.append("Audiology")
    full_address = properties.get("formattedAddress", "")
    if not full_address:
        full_address = ", ".join(
            part
            for part in [
                address.get("streetAddress", ""),
                address.get("addressLocality", ""),
                address.get("addressRegion", ""),
                address.get("postalCode", ""),
            ]
            if part
        )
    return {
        "id": str(data.get("@id", "")),
        "name": data.get("name", item.get("list_name", "")),
        "status": "Active",
        "state": address.get("addressRegion", ""),
        "city": address.get("addressLocality", ""),
        "postal_code": address.get("postalCode", ""),
        "full_address": full_address,
        "phone": data.get("telephone", ""),
        "latitude": float(geo["latitude"]),
        "longitude": float(geo["longitude"]),
        "official_url": item["official_url"],
        "services": "; ".join(services),
        "audiology": str(has_audiology).lower(),
    }


def validate(stores: list[dict], snapshot: dict) -> None:
    expected = int(snapshot.get("list_count", 0))
    if expected < 350 or expected > 450:
        raise ValueError(f"Unexpected Specsavers store count: {expected}")
    if len(stores) != expected or snapshot.get("store_count") != expected:
        raise ValueError(f"Specsavers snapshot incomplete: {len(stores)} of {expected}")
    if len({store["id"] for store in stores}) != len(stores):
        raise ValueError("Duplicate Specsavers store IDs")
    for store in stores:
        if store["state"] not in VALID_STATES:
            raise ValueError(f"Invalid state for {store['name']}: {store['state']}")
        if not (-44.5 <= store["latitude"] <= -9.0 and 112.0 <= store["longitude"] <= 154.5):
            raise ValueError(f"Invalid coordinates for {store['name']}")
        if not store["official_url"] or not store["full_address"]:
            raise ValueError(f"Missing source metadata for {store['name']}")


def write_csv(stores: list[dict]) -> None:
    fields = [
        "id",
        "name",
        "status",
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
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: store.get(field, "") for field in fields} for store in stores)


def write_geojson(stores: list[dict], snapshot: dict) -> None:
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
                    "retailer": "Specsavers",
                    "source": snapshot["source_url"],
                    "fetched_at": snapshot["fetched_at"],
                    "store_count": len(stores),
                    "collection_method": snapshot.get("collection_method", ""),
                },
                "features": features,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    stores = [clean_store(item) for item in snapshot.get("stores", []) if item.get("ok")]
    stores.sort(key=lambda item: (item["state"], item["city"], item["name"]))
    validate(stores, snapshot)
    write_csv(stores)
    write_geojson(stores, snapshot)
    by_state: dict[str, int] = {}
    for store in stores:
        by_state[store["state"]] = by_state.get(store["state"], 0) + 1
    print(f"Wrote {len(stores)} Specsavers Australian stores.")
    print(", ".join(f"{state}: {count}" for state, count in sorted(by_state.items())))
    print(f"Data: {RETAILER_DIR}")


if __name__ == "__main__":
    main()
