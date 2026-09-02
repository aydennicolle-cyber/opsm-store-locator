#!/usr/bin/env python3
"""Refresh bounded official locators for additional Australian optical networks.

The saved snapshots deliberately omit email addresses, opening hours and other
unneeded contact data. They retain official source IDs so later refreshes do not
create false openings or closures.
"""

from __future__ import annotations

import csv
import base64
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "OpticalLeasingIntelligence/1.0 (bounded public locator refresh)"
CSV_FIELDS = [
    "id", "name", "status", "country", "state", "city", "postal_code",
    "full_address", "phone", "latitude", "longitude", "official_url",
    "services", "audiology", "source_url",
]
GEORGE_MATILDA_COORDINATE_CORRECTIONS = {
    # The official locator currently places this ACT practice in Western
    # Australia. The replacement point is the mapped Tuggeranong Square address.
    "17216": {
        "latitude": -35.41995,
        "longitude": 149.070052,
        "evidence_url": "https://www.realcommercial.com.au/leased/property-tuggeranong-square-ground-level-310-anketell-street-tuggeranong-act-2900-5435150",
        "reason": "Official locator coordinate conflicts with the official ACT address; mapped property address used.",
    }
}
AU_STATE_CODES = {
    "australian capital territory": "ACT",
    "new south wales": "NSW",
    "northern territory": "NT",
    "queensland": "QLD",
    "south australia": "SA",
    "tasmania": "TAS",
    "victoria": "VIC",
    "western australia": "WA",
}


def fetch_text(url: str, referer: str = "") -> str:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def tidy(value: object) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def text_from_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", ", ", value or "", flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    return tidy(value).strip(" ,")


def parse_au_address(value: str, fallback_city: str = "") -> tuple[str, str, str, str]:
    address = tidy(value).strip(" ,")
    expanded = "|".join(re.escape(name) for name in AU_STATE_CODES)
    match = re.search(
        rf"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA|{expanded})\b\s*,?\s*(\d{{4}})\b",
        address,
        flags=re.IGNORECASE,
    )
    if not match:
        raise RuntimeError(f"Could not parse Australian state/postcode from: {address}")
    raw_state = match.group(1)
    state = AU_STATE_CODES.get(raw_state.lower(), raw_state.upper())
    postcode = match.group(2)
    prefix = address[:match.start()].rstrip(" ,")
    segments = [part.strip() for part in prefix.split(",") if part.strip()]
    city = segments[-1] if len(segments) > 1 else tidy(fallback_city)
    return address, city, state, postcode


def write_source(
    folder: str,
    source_url: str,
    records: list[dict],
    fetched_at: str,
    coordinate_corrections: list[dict] | None = None,
) -> None:
    target = ROOT / "retailers" / folder
    target.mkdir(parents=True, exist_ok=True)
    records.sort(key=lambda row: (row["state"], row["city"], row["name"], row["id"]))
    with (target / "stores.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in CSV_FIELDS} for row in records)
    snapshot = {
        "source_url": source_url,
        "fetched_at": fetched_at,
        "store_count": len(records),
        "scope": "Australia",
        "method": "Bounded official public store locator",
        "retained_fields": CSV_FIELDS,
        "excluded_fields": ["email", "opening_hours"],
        "source_ids": [row["id"] for row in records],
        "coordinate_corrections": coordinate_corrections or [],
    }
    (target / "source_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


class StoreDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.payload = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("data-stores") and not self.payload:
            self.payload = values["data-stores"] or ""


def george_and_matilda(fetched_at: str) -> tuple[str, list[dict]]:
    source_url = "https://georgeandmatilda.com.au/find-a-store/"
    parser = StoreDataParser()
    parser.feed(fetch_text(source_url))
    if not parser.payload:
        raise RuntimeError("George & Matilda locator did not expose data-stores")
    payload = json.loads(html.unescape(parser.payload))
    records = []
    for item in payload:
        address = tidy(item.get("address"))
        locality = ""
        parts = [part.strip() for part in address.split(",") if part.strip()]
        state = tidy(item.get("state")).upper()
        postcode = tidy(item.get("postcode"))
        if state in parts:
            state_index = parts.index(state)
            if state_index:
                locality = parts[state_index - 1]
        records.append({
            "id": tidy(item.get("id")),
            "name": tidy(item.get("title")),
            "status": "Active",
            "country": "Australia",
            "state": state,
            "city": locality,
            "postal_code": postcode,
            "full_address": address,
            "phone": tidy(item.get("phone")),
            "latitude": item.get("lat"),
            "longitude": item.get("lng"),
            "official_url": tidy(item.get("url")) or source_url,
            "services": "",
            "audiology": "false",
            "source_url": source_url,
        })
    corrections = []
    for record in records:
        correction = GEORGE_MATILDA_COORDINATE_CORRECTIONS.get(record["id"])
        if correction:
            record["latitude"] = correction["latitude"]
            record["longitude"] = correction["longitude"]
            corrections.append({"source_id": record["id"], **correction})
    return source_url, records, corrections


def wp_store_locator(source_url: str) -> list[dict]:
    base = urllib.parse.urlsplit(source_url)
    endpoint = f"{base.scheme}://{base.netloc}/wp-admin/admin-ajax.php"
    query = urllib.parse.urlencode({
        "action": "store_search",
        "lat": "-25.2744",
        "lng": "133.7751",
        "max_results": "500",
        "search_radius": "5000",
        "autoload": "1",
    })
    payload = json.loads(fetch_text(f"{endpoint}?{query}"))
    if isinstance(payload, dict):
        payload = payload.get("stores") or payload.get("results") or []
    records = []
    for item in payload:
        address_parts = [
            tidy(item.get("address")), tidy(item.get("address2")), tidy(item.get("city")),
            tidy(item.get("state")), tidy(item.get("zip")),
        ]
        full_address = ", ".join(part for part in address_parts if part)
        records.append({
            "id": tidy(item.get("id")) or slug(f"{item.get('store')} {full_address}"),
            "name": tidy(item.get("store")),
            "status": "Active",
            "country": "Australia",
            "state": tidy(item.get("state")).upper(),
            "city": tidy(item.get("city")),
            "postal_code": tidy(item.get("zip")),
            "full_address": full_address,
            "phone": tidy(item.get("phone")),
            "latitude": item.get("lat"),
            "longitude": item.get("lng"),
            "official_url": tidy(item.get("permalink")) or source_url,
            "services": "",
            "audiology": "false",
            "source_url": source_url,
        })
    return records


def stockist_1001() -> tuple[str, list[dict]]:
    source_url = "https://1001optometry.com.au/pages/store-locator"
    endpoint = "https://stockist.co/api/v1/u10172/locations/all"
    payload = json.loads(fetch_text(endpoint, source_url))
    records = []
    for item in payload:
        address = tidy(item.get("full_address")) or ", ".join(
            tidy(part) for part in (
                item.get("address_line_1"), item.get("address_line_2"), item.get("city"),
                item.get("state"), item.get("postal_code"), item.get("country"),
            ) if tidy(part)
        )
        custom_fields = {
            tidy(field.get("name")): tidy(field.get("value"))
            for field in item.get("custom_fields", [])
        }
        records.append({
            "id": tidy(item.get("id")),
            "name": f"1001 Optometry {tidy(item.get('name'))}",
            "status": "Active",
            "country": "Australia",
            "state": tidy(item.get("state")).upper(),
            "city": tidy(item.get("city")),
            "postal_code": tidy(item.get("postal_code")),
            "full_address": address,
            "phone": tidy(item.get("phone")),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "official_url": custom_fields.get("Find Out More") or source_url,
            "services": "",
            "audiology": "false",
            "source_url": source_url,
        })
    return source_url, records


def eyeq() -> tuple[str, list[dict]]:
    source_url = "https://www.eyeq.com.au/find-an-optometrist/"
    page = fetch_text(source_url)
    pattern = re.compile(
        r"<h4>(?P<name>.*?)</h4>.*?<h6[^>]*>.*?</h6>.*?"
        r"<h6[^>]*>(?P<address>.*?)</h6>.*?"
        r"<a[^>]+href=[\"'](?P<url>https://www\.eyeq\.com\.au/optometrist/[^\"']+)[\"'][^>]*>\s*View Profile\s*</a>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    records = []
    for match in pattern.finditer(page):
        name = text_from_html(match.group("name"))
        profile_url = html.unescape(match.group("url"))
        address, city, state, postcode = parse_au_address(
            text_from_html(match.group("address")), name
        )
        profile = fetch_text(profile_url)
        coordinate = re.search(r"!2d(1\d{2}\.\d+)!3d(-\d{1,2}\.\d+)", profile)
        if not coordinate:
            coordinate = re.search(
                r"data-lat=[\"'](-\d{1,2}\.\d+)[\"'][^>]+data-lon=[\"'](1\d{2}\.\d+)[\"']",
                profile,
            )
            latitude = coordinate.group(1) if coordinate else ""
            longitude = coordinate.group(2) if coordinate else ""
        else:
            longitude, latitude = coordinate.groups()
        records.append({
            "id": slug(urllib.parse.urlsplit(profile_url).path.rstrip("/").split("/")[-1]),
            "name": f"EyeQ Optometrists {name}",
            "status": "Active",
            "country": "Australia",
            "state": state,
            "city": city,
            "postal_code": postcode,
            "full_address": address,
            "phone": "",
            "latitude": latitude,
            "longitude": longitude,
            "official_url": profile_url,
            "services": "",
            "audiology": "false",
            "source_url": source_url,
        })
    return source_url, records


def laubman_and_pank() -> tuple[str, list[dict]]:
    source_url = "https://www.laubmanandpank.com.au/store-finder"
    page = fetch_text(source_url)
    row_pattern = re.compile(
        r"<tr>.*?views-field-title[^>]*>(?P<name>.*?)</td>.*?"
        r"class=['\"]map_data['\"][^>]+data-lat=[\"'](?P<lat>[^\"']+)[\"']"
        r"[^>]+data-log=[\"'](?P<lng>[^\"']+)[\"'].*?"
        r"href=[\"'](?P<url>/store/[^\"']+)[\"']",
        flags=re.IGNORECASE | re.DOTALL,
    )
    records = []
    for match in row_pattern.finditer(page):
        name = text_from_html(match.group("name"))
        profile_url = urllib.parse.urljoin(source_url, html.unescape(match.group("url")))
        profile = fetch_text(profile_url)
        def profile_field(field_name: str) -> str:
            field_match = re.search(
                rf"field--name-field-{re.escape(field_name)}.*?field__item[^>]*>(.*?)</div>",
                profile,
                flags=re.IGNORECASE | re.DOTALL,
            )
            return text_from_html(field_match.group(1)) if field_match else ""

        address_one = profile_field("address-one")
        if len(address_one) > 120:
            street_addresses = re.findall(
                r"\b\d+[A-Za-z/-]*\s+[^,]{2,80}\b(?:Street|Road|Avenue|Parade|Highway|Drive|Boulevard|Terrace|Place|Mall)\b",
                address_one,
                flags=re.IGNORECASE,
            )
            if street_addresses:
                address_one = street_addresses[-1]
        address_parts = [
            address_one, profile_field("address-two"),
            profile_field("suburb"), profile_field("state"), profile_field("postcode"),
        ]
        address_match = re.search(
            r"<div class=[\"']map-infowindow[\"'][^>]*>(.*?)</div>",
            profile,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if address_parts[0] and all(address_parts[2:]):
            raw_address = ", ".join(address_parts)
        elif address_match:
            raw_address = re.sub(r"[\r\n]+", ", ", address_match.group(1))
        else:
            raise RuntimeError(f"Laubman & Pank profile has no official address: {profile_url}")
        address, city, state, postcode = parse_au_address(text_from_html(raw_address), name)
        records.append({
            "id": slug(match.group("url").rstrip("/").split("/")[-1]),
            "name": name if "laubman" in name.lower() else f"Laubman & Pank {name}",
            "status": "Active",
            "country": "Australia",
            "state": state,
            "city": city,
            "postal_code": postcode,
            "full_address": address,
            "phone": profile_field("phone"),
            "latitude": match.group("lat"),
            "longitude": match.group("lng"),
            "official_url": profile_url,
            "services": "",
            "audiology": "false",
            "source_url": source_url,
        })
    return source_url, records


def provision() -> tuple[str, list[dict]]:
    source_url = "https://www.provision.com.au/search-results/"
    endpoint = "https://www.provision.com.au/wp-admin/admin-ajax.php"
    encoded_location = base64.b64encode(json.dumps({
        "lat": -25.2744, "lng": 133.7751, "address": "Australia"
    }).encode("utf-8")).decode("ascii")
    common = {
        "action": "search_and_go_elated_archive_adv_search_query",
        "location": encoded_location,
        "typeID": "",
        "keywords": "",
        "number": "12",
        "listingCategoryID": "",
        "listingTagID": "",
        "sort": "",
        "distance": "5000",
        "tax_query[clinical_service]": "",
        "tax_query[practice_facility]": "",
    }
    records_by_id = {}
    page = 1
    max_pages = 1
    while page <= max_pages:
        params = {
            **common,
            "nextPage": "" if page == 1 else str(page),
            "loadMoreFlag": "false" if page == 1 else "true",
        }
        request_url = f"{endpoint}?{urllib.parse.urlencode(params)}"
        payload = None
        for attempt in range(4):
            raw_payload = fetch_text(request_url, source_url)
            if not raw_payload.lstrip().startswith("{") and "{" in raw_payload:
                # The public endpoint occasionally prefixes a harmless image
                # warning for practices without a profile image.
                raw_payload = raw_payload[raw_payload.find("{"):]
            try:
                payload = json.loads(raw_payload)
                break
            except json.JSONDecodeError:
                if attempt == 3:
                    raise RuntimeError(
                        f"ProVision locator returned an invalid response for page {page}"
                    )
                time.sleep(attempt + 1)
        assert payload is not None
        max_pages = int(payload.get("maxNumPages") or 1)
        for item in payload.get("mapData", []):
            location = item.get("location") or {}
            address, city, state, postcode = parse_au_address(
                tidy(location.get("address")), tidy(item.get("title"))
            )
            source_id = tidy(item.get("id"))
            records_by_id[source_id] = {
                "id": source_id,
                "name": tidy(item.get("title")),
                "status": "Active",
                "country": "Australia",
                "state": state,
                "city": city,
                "postal_code": postcode,
                "full_address": address,
                "phone": "",
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
                "official_url": tidy(item.get("itemUrl")) or source_url,
                "services": "",
                "audiology": "false",
                "source_url": source_url,
            }
        page += 1
        time.sleep(0.15)
    return source_url, list(records_by_id.values())


def validate(label: str, records: list[dict]) -> None:
    if not records:
        raise RuntimeError(f"{label}: official locator returned no records")
    ids = [row["id"] for row in records]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{label}: duplicate official source IDs")
    for row in records:
        if row["state"] not in {"ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"}:
            raise RuntimeError(f"{label}: invalid state for {row['id']}: {row['state']}")
        latitude, longitude = float(row["latitude"]), float(row["longitude"])
        if not (-44.5 <= latitude <= -9.0 and 112.0 <= longitude <= 154.5):
            raise RuntimeError(f"{label}: invalid coordinates for {row['id']}")
        if not row["name"] or not row["full_address"] or not row["postal_code"]:
            raise RuntimeError(f"{label}: incomplete record {row['id']}")


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat()
    gm_url, gm_records, gm_corrections = george_and_matilda(fetched_at)
    sources = [
        ("George & Matilda", "george-and-matilda", gm_url, gm_records, gm_corrections),
        (
            "Eyecare Plus", "eyecare-plus", "https://www.eyecareplus.com.au/find-optometrist/",
            wp_store_locator("https://www.eyecareplus.com.au/find-optometrist/"), [],
        ),
        (
            "Optical Superstore", "optical-superstore",
            "https://opticalsuperstore.com.au/find-your-nearest-store/",
            wp_store_locator("https://opticalsuperstore.com.au/find-your-nearest-store/"), [],
        ),
    ]
    for label, folder, loader in (
        ("1001 Optometry", "1001-optometry", stockist_1001),
        ("EyeQ Optometrists", "eyeq-optometrists", eyeq),
        ("Laubman & Pank", "laubman-and-pank", laubman_and_pank),
        ("ProVision affiliation", "provision", provision),
    ):
        source_url, records = loader()
        sources.append((label, folder, source_url, records, []))
    for label, folder, source_url, records, coordinate_corrections in sources:
        validate(label, records)
        write_source(folder, source_url, records, fetched_at, coordinate_corrections)
        print(f"{label}: wrote {len(records)} official locations")


if __name__ == "__main__":
    main()
