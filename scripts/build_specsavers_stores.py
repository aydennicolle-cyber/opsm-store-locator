#!/usr/bin/env python3
"""Build Specsavers CSV and GeoJSON from a validated browser snapshot."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COUNTRY_CODE = os.environ.get("SPECSAVERS_COUNTRY", "AU").upper()
IS_NZ = COUNTRY_CODE == "NZ"
COUNTRY_NAME = "New Zealand" if IS_NZ else "Australia"
RETAILER_DIR = ROOT / "retailers" / ("specsavers-nz" if IS_NZ else "specsavers")
SNAPSHOT_PATH = RETAILER_DIR / "source_snapshot.json"
CSV_PATH = RETAILER_DIR / "stores.csv"
GEOJSON_PATH = RETAILER_DIR / "stores.geojson"
VALID_STATES = {"ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"}
NZ_REGION_ALIASES = {
    "AUK": "Auckland",
    "Auckland": "Auckland",
    "BOP": "Bay of Plenty",
    "Bay of Plenty": "Bay of Plenty",
    "CAN": "Canterbury",
    "Canterbury": "Canterbury",
    "GIS": "Gisborne",
    "Gisborne": "Gisborne",
    "HKB": "Hawke's Bay",
    "Hawke's Bay": "Hawke's Bay",
    "MBH": "Marlborough",
    "Marlborough": "Marlborough",
    "MWT": "Manawatu-Whanganui",
    "Manawatu-Wanganui": "Manawatu-Whanganui",
    "Manawatu-Whanganui": "Manawatu-Whanganui",
    "NSN": "Nelson",
    "Nelson": "Nelson",
    "NTL": "Northland",
    "Northland": "Northland",
    "OTA": "Otago",
    "Otago": "Otago",
    "STL": "Southland",
    "Southland": "Southland",
    "TAS": "Tasman",
    "Tasman": "Tasman",
    "TKI": "Taranaki",
    "Taranaki": "Taranaki",
    "WKO": "Waikato",
    "Waikato": "Waikato",
    "WGN": "Wellington",
    "Wellington": "Wellington",
    "WTC": "West Coast",
    "West Coast": "West Coast",
}
NZ_LOCALITY_REGIONS = {
    "Ashburton": "Canterbury",
    "Auckland": "Auckland",
    "Blenheim": "Marlborough",
    "Christchurch": "Canterbury",
    "Dunedin": "Otago",
    "Flat Bush": "Auckland",
    "Gisborne": "Gisborne",
    "Hamilton": "Waikato",
    "Hastings": "Hawke's Bay",
    "Invercargill": "Southland",
    "Kerikeri": "Northland",
    "Levin": "Manawatu-Whanganui",
    "Manukau City Centre": "Auckland",
    "Masterton": "Wellington",
    "Mount Albert": "Auckland",
    "Napier": "Hawke's Bay",
    "Nelson": "Nelson",
    "New Lynn": "Auckland",
    "New Plymouth": "Taranaki",
    "Pakuranga": "Auckland",
    "Palmerston North": "Manawatu-Whanganui",
    "Paraparaumu": "Wellington",
    "Porirua": "Wellington",
    "Queenstown": "Otago",
    "Rangiora": "Canterbury",
    "Richmond": "Tasman",
    "Rotorua": "Bay of Plenty",
    "Tauranga": "Bay of Plenty",
    "Taupo": "Waikato",
    "Thames": "Waikato",
    "Timaru": "Canterbury",
    "Upper Hutt": "Wellington",
    "Wellington": "Wellington",
    "Whakatane": "Bay of Plenty",
    "Whanganui": "Manawatu-Whanganui",
    "Whangarei": "Northland",
}


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
    region = address.get("addressRegion", "")
    if IS_NZ:
        region = NZ_REGION_ALIASES.get(region, region)
        if not region or region == "New Zealand":
            region = NZ_LOCALITY_REGIONS.get(address.get("addressLocality", ""), "")
    return {
        "id": str(data.get("@id", "")),
        "name": data.get("name", item.get("list_name", "")),
        "status": "Active",
        "country": COUNTRY_NAME,
        "state": region,
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
    minimum, maximum = (45, 75) if IS_NZ else (350, 450)
    if expected < minimum or expected > maximum:
        raise ValueError(f"Unexpected Specsavers store count: {expected}")
    if len(stores) != expected or snapshot.get("store_count") != expected:
        raise ValueError(f"Specsavers snapshot incomplete: {len(stores)} of {expected}")
    if len({store["id"] for store in stores}) != len(stores):
        raise ValueError("Duplicate Specsavers store IDs")
    for store in stores:
        if IS_NZ:
            if store["state"] not in set(NZ_REGION_ALIASES.values()):
                raise ValueError(f"Invalid region for {store['name']}: {store['state']}")
            if not (-48 <= store["latitude"] <= -33.5 and 165 <= store["longitude"] <= 179.5):
                raise ValueError(f"Invalid coordinates for {store['name']}")
        else:
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
    print(f"Wrote {len(stores)} Specsavers {COUNTRY_NAME} stores.")
    print(", ".join(f"{state}: {count}" for state, count in sorted(by_state.items())))
    print(f"Data: {RETAILER_DIR}")


if __name__ == "__main__":
    main()
