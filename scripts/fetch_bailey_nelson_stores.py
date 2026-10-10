#!/usr/bin/env python3
"""Fetch Bailey Nelson Australia stores from its public store pages."""

from __future__ import annotations

import csv
import html as html_lib
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from public_trading_status import infer_public_trading_status


ROOT = Path(__file__).resolve().parents[1]
RETAILER_DIR = ROOT / "retailers" / "bailey-nelson"
LIST_URL = "https://baileynelson.com.au/pages/optometrist-near-me"
USER_AGENT = "Mozilla/5.0 (compatible; Australian Optical Network Map/1.0)"
CSV_PATH = RETAILER_DIR / "stores.csv"
GEOJSON_PATH = RETAILER_DIR / "stores.geojson"
RAW_PATH = RETAILER_DIR / "source_snapshot.json"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.json_blocks: list[str] = []
        self._in_json = False
        self._json_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        if tag == "script" and values.get("type") == "application/ld+json":
            self._in_json = True
            self._json_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_json:
            self._json_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_json:
            self.json_blocks.append("".join(self._json_parts))
            self._in_json = False


def fetch_text(url: str, timeout: int = 45) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace"), response.geturl()


def store_urls(html_text: str) -> list[str]:
    parser = PageParser()
    parser.feed(html_text)
    urls = set()
    for href in parser.links:
        absolute = urllib.parse.urljoin(LIST_URL, href.split("?", 1)[0])
        path = urllib.parse.urlparse(absolute).path.rstrip("/")
        if "/pages/optometrist-" not in path or path.endswith("optometrist-near-me"):
            continue
        urls.add(f"https://baileynelson.com.au{path}")
    return sorted(urls)


def local_business(parser: PageParser) -> dict:
    for block in parser.json_blocks:
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            if isinstance(item, dict) and item.get("@type") == "Optician":
                return item
    raise ValueError("Optician structured data missing")


def map_coordinates(url: str) -> tuple[float, float, str]:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            _, resolved = fetch_text(url, timeout=45)
            exact = re.search(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", resolved)
            # The @ pair is the map camera, which can be kilometres from the
            # named store. Only use the business feature's explicit point.
            match = exact
            if not match:
                raise ValueError(f"Coordinates missing from resolved map URL: {resolved}")
            return float(match.group(1)), float(match.group(2)), resolved
        except Exception as error:  # pragma: no cover - retry path is network dependent
            last_error = error
            time.sleep(attempt + 1)
    raise RuntimeError(str(last_error))


def geocode_address(address: str) -> tuple[float, float, str]:
    query = urllib.parse.urlencode(
        {
            "format": "jsonv2",
            "countrycodes": "au",
            "limit": 1,
            "q": address,
        }
    )
    url = f"https://nominatim.openstreetmap.org/search?{query}"
    body, resolved = fetch_text(url)
    results = json.loads(body)
    if not results:
        raise ValueError(f"No geocoding result for {address}")
    return float(results[0]["lat"]), float(results[0]["lon"]), resolved


def normalise_state(value: str, postcode: str) -> str:
    aliases = {
        "NSE": "NSW",
        "Australian Capital Territory": "ACT",
        "New South Wales": "NSW",
        "Northern Territory": "NT",
        "Queensland": "QLD",
        "South Australia": "SA",
        "Tasmania": "TAS",
        "Victoria": "VIC",
        "Western Australia": "WA",
    }
    state = aliases.get(value.strip(), value.strip().upper())
    if state:
        return state
    if not postcode.isdigit():
        return ""
    number = int(postcode)
    if 800 <= number <= 999:
        return "NT"
    if 2600 <= number <= 2618 or 2900 <= number <= 2920:
        return "ACT"
    if 1000 <= number <= 2599 or 2619 <= number <= 2899 or 2921 <= number <= 2999:
        return "NSW"
    if 3000 <= number <= 3999 or 8000 <= number <= 8999:
        return "VIC"
    if 4000 <= number <= 4999 or 9000 <= number <= 9999:
        return "QLD"
    if 5000 <= number <= 5999:
        return "SA"
    if 6000 <= number <= 6999:
        return "WA"
    if 7000 <= number <= 7999:
        return "TAS"
    return ""


def visible_address(page_html: str) -> dict[str, str]:
    match = re.search(r"<address[^>]*>(.*?)</address>", page_html, re.IGNORECASE | re.DOTALL)
    if not match:
        return {}
    lines = [
        html_lib.unescape(re.sub(r"<[^>]+>", "", value)).strip()
        for value in re.findall(r"<div[^>]*>(.*?)</div>", match.group(1), re.IGNORECASE | re.DOTALL)
    ]
    lines = [line for line in lines if line]
    if not lines:
        return {}
    result = {"streetAddress": ", ".join(lines[:-1] or lines)}
    if len(lines) > 1:
        locality = re.match(r"^(.*?),\s*(ACT|NSW|NT|QLD|SA|TAS|VIC|WA),?\s*(\d{4})$", lines[-1])
        if locality:
            result.update(
                {
                    "addressLocality": locality.group(1),
                    "addressRegion": locality.group(2),
                    "postalCode": locality.group(3),
                }
            )
    return result


def australian_phone(page_html: str, structured_phone: str | None) -> str:
    """Use a published complete number; never repair a missing digit by guess."""
    def valid(value: str) -> bool:
        digits = re.sub(r"\D", "", value)
        return bool(re.fullmatch(r"(?:61[23478]\d{8}|0[23478]\d{8}|1[38]00\d{6}|13\d{4})", digits))

    supplied = (structured_phone or "").strip()
    if valid(supplied):
        return supplied
    candidates = {}
    for label in re.findall(r'<a\b[^>]*href=["\']tel:[^"\']*["\'][^>]*>(.*?)</a>', page_html, re.I | re.S):
        value = html_lib.unescape(re.sub(r"<[^>]+>", "", label)).strip()
        if valid(value):
            digits = re.sub(r"\D", "", value)
            key = "0" + digits[2:] if digits.startswith("61") else digits
            candidates[key] = value
    return next(iter(candidates.values())) if len(candidates) == 1 else ""


def clean_store(url: str) -> tuple[dict, dict]:
    page_html, resolved_page_url = fetch_text(url)
    parser = PageParser()
    parser.feed(page_html)
    structured = local_business(parser)
    map_links = [
        urllib.parse.urljoin(url, link)
        for link in parser.links
        if "maps.app.goo.gl" in link or "g.co/kgs/" in link or "google.com/maps" in link
    ]
    address = dict(structured.get("address", {}))
    for key, value in visible_address(page_html).items():
        if not address.get(key):
            address[key] = value
    state = normalise_state(address.get("addressRegion", ""), address.get("postalCode", ""))
    address_parts = [
        address.get("streetAddress", ""),
        address.get("addressLocality", ""),
        state,
        address.get("postalCode", ""),
    ]
    full_address = ", ".join(part for part in address_parts if part)
    preferred_map_links = sorted(
        map_links,
        key=lambda item: ("maps.app.goo.gl" not in item, "google.com/maps" not in item),
    )
    coordinate_source = "Official Google Maps link"
    if preferred_map_links:
        try:
            latitude, longitude, resolved_map_url = map_coordinates(preferred_map_links[0])
        except RuntimeError:
            latitude, longitude, resolved_map_url = geocode_address(full_address)
            coordinate_source = "OpenStreetMap Nominatim address fallback"
    else:
        latitude, longitude, resolved_map_url = geocode_address(full_address)
        coordinate_source = "OpenStreetMap Nominatim address fallback"
    offers = structured.get("makesOffer", [])
    services = []
    for offer in offers:
        item = offer.get("itemOffered", {}) if isinstance(offer, dict) else {}
        if item.get("@type") == "Service" and item.get("name"):
            services.append(item["name"])
    slug = urllib.parse.urlparse(url).path.rsplit("/", 1)[-1].replace("optometrist-", "")
    store = {
        "id": slug,
        "name": structured.get("name", f"Bailey Nelson {slug.replace('-', ' ').title()}"),
        "status": infer_public_trading_status(page_html, structured),
        "state": state,
        "city": address.get("addressLocality", ""),
        "postal_code": address.get("postalCode", ""),
        "full_address": full_address,
        "phone": australian_phone(page_html, structured.get("telephone")),
        "latitude": latitude,
        "longitude": longitude,
        "official_url": resolved_page_url,
        "services": "; ".join(dict.fromkeys(services)),
        "audiology": "false",
        "map_url": resolved_map_url,
        "coordinate_source": coordinate_source,
    }
    raw = {
        "source_url": url,
        "resolved_page_url": resolved_page_url,
        "map_url": preferred_map_links[0] if preferred_map_links else "",
        "resolved_map_url": resolved_map_url,
        "coordinate_source": coordinate_source,
        "structured_data": structured,
    }
    return store, raw


def validate(stores: list[dict], expected_count: int) -> None:
    if expected_count < 60 or expected_count > 90:
        raise ValueError(f"Unexpected Bailey Nelson link count: {expected_count}")
    if len(stores) != expected_count:
        raise ValueError(f"Expected {expected_count} stores, collected {len(stores)}")
    if len({store["id"] for store in stores}) != len(stores):
        raise ValueError("Duplicate Bailey Nelson store IDs")
    for store in stores:
        if store["state"] not in {"ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"}:
            raise ValueError(f"Invalid state for {store['name']}: {store['state']}")
        if not (-44.5 <= store["latitude"] <= -9.0 and 112.0 <= store["longitude"] <= 154.5):
            raise ValueError(f"Invalid coordinates for {store['name']}")


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
        "map_url",
        "coordinate_source",
    ]
    fields += sorted({key for store in stores for key in store} - set(fields))
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: store.get(field, "") for field in fields} for store in stores)


def write_geojson(stores: list[dict], fetched_at: str) -> None:
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
                    "retailer": "Bailey Nelson",
                    "source": LIST_URL,
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


def unlisted_prior_stores(stores: list[dict], prior: list[dict], prior_date: str) -> list[dict]:
    """A locator omission is not closure; retain dated previously known premises."""
    current_ids = {store["id"] for store in stores}
    retained = []
    for row in prior:
        if row["id"] not in current_ids:
            retained.append({**row, "fetched_at": row.get("fetched_at") or prior_date})
    return retained


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    list_html, _ = fetch_text(LIST_URL)
    urls = store_urls(list_html)
    stores: list[dict] = []
    raw_pages: list[dict] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(clean_store, url): url for url in urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                store, raw = future.result()
                stores.append(store)
                raw_pages.append(raw)
            except Exception as error:
                errors.append(f"{url}: {error}")
    if errors:
        raise RuntimeError("Bailey Nelson refresh aborted:\n" + "\n".join(sorted(errors)))
    stores.sort(key=lambda item: (item["state"], item["city"], item["name"]))
    raw_pages.sort(key=lambda item: item["source_url"])
    validate(stores, len(urls))

    prior_snapshot = json.loads(RAW_PATH.read_text()) if RAW_PATH.exists() else {}
    prior_rows = []
    if CSV_PATH.exists():
        with CSV_PATH.open(newline="") as handle:
            prior_rows = list(csv.DictReader(handle))
    retained = unlisted_prior_stores(stores, prior_rows, prior_snapshot.get("fetched_at", ""))
    if any(not row["fetched_at"] for row in retained):
        raise ValueError("Unlisted prior branch lacks an observation date; review before refresh")
    for row in retained:
        row["latitude"], row["longitude"] = float(row["latitude"]), float(row["longitude"])
    stores.extend(retained)
    stores.sort(key=lambda item: (item["state"], item["city"], item["name"]))
    retained_urls = {row["official_url"] for row in retained}
    old_sources = prior_snapshot.get("stores", []) + prior_snapshot.get("retained_unlisted_sources", [])
    retained_sources = [row for row in old_sources if row.get("source_url", row.get("official_url")) in retained_urls]

    RETAILER_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "source_url": LIST_URL,
        "fetched_at": fetched_at,
        "list_count": len(urls),
        "store_count": len(stores),
        "stores": raw_pages,
        "retained_unlisted_records": retained,
        "retained_unlisted_sources": retained_sources,
        "retained_unlisted_basis": "Locator omission does not establish closure. Preserve each prior observation date pending explicit reconciliation.",
    }
    RAW_PATH.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    write_csv(stores)
    write_geojson(stores, fetched_at)

    by_state: dict[str, int] = {}
    for store in stores:
        by_state[store["state"]] = by_state.get(store["state"], 0) + 1
    print(f"Wrote {len(stores)} Bailey Nelson Australian stores.")
    print(", ".join(f"{state}: {count}" for state, count in sorted(by_state.items())))
    print(f"Data: {RETAILER_DIR}")


if __name__ == "__main__":
    main()
