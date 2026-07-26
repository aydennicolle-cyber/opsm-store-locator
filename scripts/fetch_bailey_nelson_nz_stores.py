#!/usr/bin/env python3
"""Fetch Bailey Nelson New Zealand stores from its public store pages."""

from __future__ import annotations

import csv
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from fetch_bailey_nelson_stores import PageParser, fetch_text, local_business, map_coordinates


ROOT = Path(__file__).resolve().parents[1]
RETAILER_DIR = ROOT / "retailers" / "bailey-nelson-nz"
LIST_URL = "https://baileynelson.co.nz/pages/optometrist-near-me"
CSV_PATH = RETAILER_DIR / "stores.csv"
GEOJSON_PATH = RETAILER_DIR / "stores.geojson"
SNAPSHOT_PATH = RETAILER_DIR / "source_snapshot.json"
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


def tidy(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" ,")


def store_urls(page_html: str) -> list[str]:
    parser = PageParser()
    parser.feed(page_html)
    urls = {
        urllib.parse.urljoin(LIST_URL, href.split("?", 1)[0])
        for href in parser.links
        if "/pages/optometrist-" in href and not href.rstrip("/").endswith("optometrist-near-me")
    }
    return sorted(urls)


def region_for(locality: str, full_address: str) -> str:
    value = f" {locality} {full_address} ".lower()
    rules = (
        ("Auckland", ("auckland", "albany", "botany", "east tamaki", "ponsonby", "takapuna", "mount albert")),
        ("Waikato", ("hamilton", "chartwell")),
        ("Wellington", ("wellington", "hutt central", "lower hutt")),
        ("Bay of Plenty", ("tauranga", "mount maunganui")),
        ("Canterbury", ("christchurch", "riccarton", "cashel street")),
        ("Otago", ("dunedin", "queenstown", "frankton")),
    )
    for region, terms in rules:
        if any(term in value for term in terms):
            return region
    raise ValueError(f"New Zealand region could not be assigned: {full_address}")


def geocode_address(address: str) -> tuple[float, float, str]:
    query = urllib.parse.urlencode(
        {"format": "jsonv2", "countrycodes": "nz", "limit": 1, "q": address}
    )
    url = f"https://nominatim.openstreetmap.org/search?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AU NZ Optical Network Map/2.0"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        results = json.load(response)
    if not results:
        raise ValueError(f"No geocoding result for {address}")
    return float(results[0]["lat"]), float(results[0]["lon"]), url


def clean_store(url: str) -> tuple[dict | None, dict]:
    page_html, resolved_url = fetch_text(url)
    parser = PageParser()
    parser.feed(page_html)
    business = local_business(parser)
    address = business.get("address") or {}
    map_links = [
        urllib.parse.urljoin(resolved_url, href)
        for href in parser.links
        if "maps.app.goo.gl" in href or "google.com/maps" in href
    ]
    address_parts = [
        address.get("extendedAddress", ""),
        address.get("streetAddress", ""),
        address.get("addressLocality", ""),
        address.get("addressRegion", ""),
        address.get("postalCode", ""),
    ]
    full_address = tidy(", ".join(part for part in address_parts if part))
    if not map_links:
        return None, {
            "official_url": resolved_url,
            "map_url": "",
            "resolved_map_url": "",
            "structured_data": business,
            "excluded_reason": "Coming Soon location has no confirmed map position",
        }
    if map_links:
        latitude, longitude, resolved_map = map_coordinates(map_links[0])
    else:
        latitude, longitude, resolved_map = geocode_address(full_address)
    name = tidy(business.get("name", ""))
    store = {
        "name": name,
        "id": urllib.parse.urlparse(url).path.rstrip("/").split("/")[-1],
        "country": "New Zealand",
        "state": region_for(address.get("addressLocality", ""), full_address),
        "city": tidy(address.get("addressLocality", "")),
        "postal_code": tidy(address.get("postalCode", "")),
        "full_address": full_address,
        "phone": tidy(business.get("telephone", "")),
        "latitude": latitude,
        "longitude": longitude,
        "official_url": resolved_url,
        "services": "Comprehensive eye tests, Prescription glasses, Sunglasses",
        "audiology": "false",
        "status": "Active",
    }
    snapshot = {
        "official_url": resolved_url,
        "map_url": map_links[0] if map_links else "",
        "resolved_map_url": resolved_map,
        "structured_data": business,
    }
    return store, snapshot


def validate(stores: list[dict]) -> None:
    if not 12 <= len(stores) <= 20:
        raise ValueError(f"Unexpected Bailey Nelson New Zealand count: {len(stores)}")
    ids = [store["id"] for store in stores]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate Bailey Nelson New Zealand store IDs")
    for store in stores:
        if not (-48 <= store["latitude"] <= -33.5 and 165 <= store["longitude"] <= 179.5):
            raise ValueError(f"Invalid Bailey Nelson New Zealand coordinates: {store['id']}")


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    list_html, _ = fetch_text(LIST_URL)
    urls = store_urls(list_html)
    if not 12 <= len(urls) <= 20:
        raise ValueError(f"Unexpected Bailey Nelson New Zealand public list count: {len(urls)}")
    stores = []
    snapshots = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(clean_store, url): url for url in urls}
        for future in as_completed(futures):
            store, snapshot = future.result()
            if store:
                stores.append(store)
            snapshots.append(snapshot)
    stores.sort(key=lambda store: (store["state"], store["city"], store["name"]))
    snapshots.sort(key=lambda item: item["official_url"])
    validate(stores)
    RETAILER_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(stores)
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
                    "retailer": "Bailey Nelson",
                    "countries": ["New Zealand"],
                    "source_url": LIST_URL,
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
                "source_url": LIST_URL,
                "fetched_at": fetched_at,
                "list_count": len(urls),
                "store_count": len(stores),
                "collection_method": "Official store list, Schema.org store pages and official map links",
                "stores": snapshots,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(stores)} validated Bailey Nelson New Zealand stores")


if __name__ == "__main__":
    main()
