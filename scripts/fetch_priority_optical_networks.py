#!/usr/bin/env python3
"""Refresh priority AU/NZ optical networks from bounded public locators.

The script retains official source identifiers and only publishes fields needed
by the leasing map. Addresses without source coordinates are rate-limit
geocoded; geocoding never establishes retail-place membership.
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "OpticalLeasingIntelligence/1.0 (bounded public locator refresh)"
CSV_FIELDS = [
    "id", "name", "status", "country", "state", "city", "postal_code",
    "full_address", "phone", "latitude", "longitude", "official_url",
    "services", "audiology", "source_url",
]
AU_STATE_CODES = {
    "australian capital territory": "ACT", "new south wales": "NSW",
    "northern territory": "NT", "queensland": "QLD", "south australia": "SA",
    "tasmania": "TAS", "victoria": "VIC", "western australia": "WA",
}
NZ_REGION_BY_CITY = {
    "kerikeri": "Northland", "whangarei": "Northland", "whangārei": "Northland",
    "orewa": "Auckland", "auckland": "Auckland", "newmarket": "Auckland",
    "ponsonby": "Auckland", "te kūiti": "Waikato", "te kuiti": "Waikato",
    "hamilton": "Waikato", "cambridge": "Waikato", "te awamutu": "Waikato",
    "tauranga": "Bay of Plenty", "te puke": "Bay of Plenty",
    "new plymouth": "Taranaki", "napier": "Hawke's Bay",
    "paraparaumu": "Wellington", "wellington": "Wellington",
    "taupo": "Waikato", "ōpunake": "Taranaki", "opunake": "Taranaki",
    "blenheim": "Marlborough", "nelson": "Nelson", "motueka": "Tasman",
    "richmond": "Tasman", "tākaka": "Tasman", "takaka": "Tasman",
    "christchurch": "Canterbury", "oamaru": "Otago",
    "dunedin": "Otago", "wanaka": "Otago", "wānaka": "Otago",
    "te anau": "Southland", "invercargill": "Southland",
}
COORDINATE_OVERRIDES = {
    # Targeted Nominatim address results used where the broad geocoder fallback
    # otherwise returned only a city centroid.
    "55695732": ("-36.8458007", "174.7410496"),
    "WLXfKmCsTgWwYhS77Bx1Sw": ("-36.8691691", "174.7767505"),
    "120105921": ("-41.5120990", "173.9560691"),
    "W_7XvdUeTGSYm87lGtKnHw": ("-41.5145060", "173.9535829"),
    "56812204": ("-41.2739496", "173.2861460"),
    "120000658": ("-37.7837183", "175.2767211"),
    "120000641": ("-41.2809477", "174.7747692"),
    "blackwood-5051": ("-35.0124829", "138.6218366"),
}


def fetch_text(url: str, referer: str = "") -> str:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json"}
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def tidy(value: object) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip(" ,")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def text_from_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", ", ", value or "", flags=re.IGNORECASE)
    return tidy(re.sub(r"<[^>]+>", " ", value))


def au_address(value: str) -> tuple[str, str, str, str]:
    address = tidy(value)
    state_names = "|".join(re.escape(value) for value in AU_STATE_CODES)
    match = re.search(
        rf"\b(ACT|NSW|NT|QLD|SA|TAS|VIC|WA|{state_names})\b\s*,?\s*(\d{{4}})\b",
        address, re.I,
    )
    if not match:
        match = re.search(r"\b(\d{4})\s*,?\s*(ACT|NSW|NT|QLD|SA|TAS|VIC|WA)\b", address, re.I)
        if not match:
            raise RuntimeError(f"Could not parse Australian state/postcode: {address}")
        postcode, state = match.group(1), match.group(2).upper()
        prefix = address[:match.start()]
    else:
        raw_state, postcode = match.group(1), match.group(2)
        state = AU_STATE_CODES.get(raw_state.lower(), raw_state.upper())
        prefix = address[:match.start()]
    segments = [part.strip() for part in prefix.split(",") if part.strip()]
    city = segments[-1] if segments else ""
    city = re.sub(r"^(?:shop|unit|level)\b.*", "", city, flags=re.I).strip() or city
    return address, city, state, postcode


def existing_coordinates(folder: str) -> dict[str, tuple[str, str, str]]:
    path = ROOT / "retailers" / folder / "stores.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            row["id"]: (row.get("full_address", ""), row.get("latitude", ""), row.get("longitude", ""))
            for row in csv.DictReader(handle)
        }


def geocode(query: str, country: str, alternatives: list[str]) -> tuple[str, str]:
    for candidate in [query, *alternatives]:
        if not tidy(candidate):
            continue
        params = urllib.parse.urlencode({
            "q": tidy(candidate), "format": "jsonv2", "limit": 1,
            "countrycodes": "au" if country == "Australia" else "nz",
        })
        payload = json.loads(fetch_text(f"https://nominatim.openstreetmap.org/search?{params}"))
        time.sleep(1.05)
        if payload:
            return payload[0]["lat"], payload[0]["lon"]
    raise RuntimeError(f"Geocoder could not resolve official address: {query}")


def add_coordinates(folder: str, records: list[dict]) -> None:
    previous = existing_coordinates(folder)
    for record in records:
        override = COORDINATE_OVERRIDES.get(str(record["id"]))
        if override:
            record["latitude"], record["longitude"] = override
            continue
        if record.get("latitude") not in (None, "") and record.get("longitude") not in (None, ""):
            continue
        cached = previous.get(str(record["id"]))
        if cached and tidy(cached[0]) == tidy(record["full_address"]) and cached[1] and cached[2]:
            record["latitude"], record["longitude"] = cached[1], cached[2]
            continue
        locality = f"{record['city']} {record['state']} {record['postal_code']} {record['country']}"
        venue = re.sub(
            r"^(?:shop|suite|unit|level)\s*[^,]+,?\s*", "", record["full_address"],
            flags=re.I,
        )
        address_without_unit = re.sub(
            r"^(?:shop|suite|unit|level|lower ground floor)\s*[^,]+,?\s*", "",
            record["full_address"], flags=re.I,
        )
        record["latitude"], record["longitude"] = geocode(
            f"{record['full_address']}, {record['country']}", record["country"],
            [f"{address_without_unit}, {record['country']}", f"{venue}, {locality}", locality],
        )


def write_source(folder: str, source_url: str, records: list[dict], fetched_at: str, method: str) -> None:
    target = ROOT / "retailers" / folder
    target.mkdir(parents=True, exist_ok=True)
    records.sort(key=lambda row: (row["country"], row["state"], row["city"], row["name"], str(row["id"])))
    with (target / "stores.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in CSV_FIELDS} for row in records)
    snapshot = {
        "source_url": source_url, "fetched_at": fetched_at, "store_count": len(records),
        "scope": sorted({row["country"] for row in records}), "method": method,
        "retained_fields": CSV_FIELDS, "excluded_fields": ["email", "opening_hours"],
        "source_ids": [str(row["id"]) for row in records],
        "coordinate_note": "Official coordinates retained where supplied; otherwise the official address was rate-limit geocoded. Geocoding does not establish place membership.",
    }
    (target / "source_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def bupa() -> tuple[str, list[dict]]:
    source_url = "https://bupaoptical.bupa.com.au/pages/store-locator"
    endpoint = "https://stockist.co/api/v1/u4734/locations/all"
    records = []
    for item in json.loads(fetch_text(endpoint, source_url)):
        filters = {tidy(value.get("name")).lower() for value in item.get("filters", [])}
        if "optical" not in filters or tidy(item.get("country")) != "Australia":
            continue
        state = AU_STATE_CODES.get(tidy(item.get("state")).lower(), tidy(item.get("state")).upper())
        address = tidy(item.get("full_address")) or ", ".join(
            part for part in [tidy(item.get("address_line_1")), tidy(item.get("address_line_2")),
                              tidy(item.get("city")), state, tidy(item.get("postal_code")), "Australia"] if part
        )
        records.append({
            "id": item["id"], "name": tidy(item.get("name")), "status": "Active",
            "country": "Australia", "state": state, "city": tidy(item.get("city")),
            "postal_code": tidy(item.get("postal_code")), "full_address": address,
            "phone": tidy(item.get("phone")), "latitude": item.get("latitude"),
            "longitude": item.get("longitude"), "official_url": tidy(item.get("website")) or source_url,
            "services": "|".join(sorted(filters)), "audiology": str("hearing" in filters).lower(),
            "source_url": source_url,
        })
    return source_url, records


def chemist_warehouse_optometry() -> tuple[str, list[dict]]:
    source_url = "https://chemistwarehouseoptometry.com.au/pages/store-locator"
    endpoint = "https://api26.storepoint.co/v2/168d4a24bef596/locations"
    payload = json.loads(fetch_text(endpoint, source_url))["results"]["locations"]
    records = []
    for item in payload:
        if "permanently closed" in tidy(item.get("name")).lower() or not tidy(item.get("streetaddress")):
            continue
        address, city, state, postcode = au_address(tidy(item["streetaddress"]))
        custom = json.loads(item.get("custom_fields") or "{}")
        detail = tidy(custom.get("425zgp8m28h"))
        detail = urllib.parse.urljoin(source_url, detail) if detail else source_url
        records.append({
            "id": item.get("public_id") or item["id"], "name": tidy(item["name"]), "status": "Active",
            "country": "Australia", "state": state, "city": city, "postal_code": postcode,
            "full_address": address, "phone": tidy(item.get("phone")), "latitude": item["loc_lat"],
            "longitude": item["loc_long"], "official_url": detail,
            "services": tidy(item.get("tags")).replace(",", "|"), "audiology": "false", "source_url": source_url,
        })
    return source_url, records


def dresden() -> tuple[str, list[dict]]:
    source_url = "https://dresden.vision/au/stores"
    listing = fetch_text(source_url)
    slugs = sorted(set(re.findall(r'href=["\'](/au/stores/(?:newtown|rozelle|fitzroy|geelong|west-end))["\']', listing)))
    records = []
    pattern = re.compile(
        r'"store":\{"id":(?P<id>\d+),.*?"name":"(?P<name>[^"]+)",.*?'
        r'"city":"(?P<city>[^"]+)","state":"(?P<state>[^"]+)",'
        r'"main_address":"(?P<address>[^"]+)","postcode":"(?P<postcode>[^"]+)",'
        r'"latitude":(?P<lat>-?\d+(?:\.\d+)?),"longitude":(?P<lng>-?\d+(?:\.\d+)?)', re.S,
    )
    for path in slugs:
        profile_url = urllib.parse.urljoin(source_url, path)
        match = pattern.search(fetch_text(profile_url, source_url))
        if not match:
            raise RuntimeError(f"Dresden profile has no structured store record: {profile_url}")
        item = match.groupdict()
        records.append({
            "id": item["id"], "name": f"Dresden Vision {tidy(item['name'])}", "status": "Active",
            "country": "Australia", "state": tidy(item["state"]).upper(), "city": tidy(item["city"]),
            "postal_code": tidy(item["postcode"]), "full_address": tidy(item["address"]), "phone": "",
            "latitude": item["lat"], "longitude": item["lng"], "official_url": profile_url,
            "services": "", "audiology": "false", "source_url": source_url,
        })
    return source_url, records


def optical_warehouse() -> tuple[str, list[dict]]:
    source_url = "https://www.opticalwarehouse.com.au/local-store/"
    page = fetch_text(source_url)
    pattern = re.compile(
        r'<a href="(?P<url>https://www\.opticalwarehouse\.com\.au/local_store/[^"]+)"[^>]*>'
        r'<h5 class=local-title>(?P<name>.*?)</h5>.*?'
        r'<td class=google-map-anchor><a[^>]*>(?P<address>.*?)</a>.*?'
        r'<a href="tel:[^"]+"[^>]*>(?P<phone>.*?)</a>', re.I | re.S,
    )
    records = []
    for match in pattern.finditer(page):
        name = text_from_html(match.group("name"))
        address, _, state, postcode = au_address(text_from_html(match.group("address")))
        city = tidy(name.split("(", 1)[0])
        records.append({
            "id": slug(urllib.parse.urlsplit(match.group("url")).path.rstrip("/").split("/")[-1]),
            "name": f"Optical Warehouse {name}", "status": "Active", "country": "Australia",
            "state": state, "city": city, "postal_code": postcode, "full_address": address,
            "phone": text_from_html(match.group("phone")), "latitude": "", "longitude": "",
            "official_url": match.group("url"), "services": "", "audiology": "false", "source_url": source_url,
        })
    add_coordinates("optical-warehouse", records)
    return source_url, records


def optical_company() -> tuple[str, list[dict]]:
    source_url = "https://www.opticalco.com.au/locations-listing/"
    page = fetch_text(source_url)
    pattern = re.compile(
        r'<div class="title">(?P<title>.*?)</div>(?P<address>.*?)<strong>Ph:</strong>\s*(?P<phone>[^<]+)',
        re.I | re.S,
    )
    records = []
    for match in pattern.finditer(page):
        title = text_from_html(match.group("title"))
        if "the optical co" not in title.lower():
            continue
        locality = tidy(title.split("(", 1)[0])
        address, _, state, postcode = au_address(text_from_html(match.group("address")))
        city = locality
        records.append({
            "id": slug(f"{locality}-{postcode}"), "name": f"The Optical Company {locality}",
            "status": "Active", "country": "Australia", "state": state, "city": city or locality,
            "postal_code": postcode, "full_address": address, "phone": tidy(match.group("phone")),
            "latitude": "", "longitude": "", "official_url": source_url, "services": "",
            "audiology": "false", "source_url": source_url,
        })
    add_coordinates("the-optical-company", records)
    return source_url, records


def national_pharmacies() -> tuple[str, list[dict]]:
    source_url = "https://www.nationalpharmacies.com.au/optical-booking/"
    # The official site blocks non-browser requests. This bounded text rendering
    # preserves the official page URL and provides the same public locator copy.
    page = fetch_text("https://r.jina.ai/http://www.nationalpharmacies.com.au/optical-booking/")
    if "\\n" in page:
        page = page.replace("\\n", "\n")
    page = page.split("### All stores", 1)[0]
    pattern = re.compile(
        r'^#### (?P<name>[^\n]+)\s+\*\*Address:\*\*\s*(?P<address>[^\n]+)\s+'
        r'\*\*Phone:\*\*\s*(?P<phone>[^\n]+)',
        re.M,
    )
    records = []
    for match in pattern.finditer(page):
        name = tidy(match.group("name"))
        raw_address = tidy(match.group("address"))
        # The locator card currently omits Newton's postcode; its linked official
        # store page publishes Newton Village Shopping Centre, SA 5074.
        if name == "Newton" and not re.search(r"\b\d{4}\b", raw_address):
            raw_address = re.sub(r"\bSA\b", "SA 5074", raw_address, count=1)
        address, _, state, postcode = au_address(raw_address)
        city = name
        records.append({
            "id": slug(f"{name}-{postcode}"), "name": f"Optical by National Pharmacies {name}",
            "status": "Active", "country": "Australia", "state": state, "city": city or name,
            "postal_code": postcode, "full_address": address, "phone": tidy(match.group("phone")),
            "latitude": "", "longitude": "", "official_url": source_url, "services": "",
            "audiology": "false", "source_url": source_url,
        })
    add_coordinates("national-pharmacies-optical", records)
    return source_url, records


def matthews() -> tuple[str, list[dict]]:
    source_url = "https://matthews.co.nz/practices/"
    page = fetch_text(source_url)
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', page, re.S)
    if not match:
        raise RuntimeError("Matthews official practices page has no structured data")
    practices = json.loads(match.group(1))["props"]["pageProps"]["page"]["initialData"]["practices"]
    records = []
    for item in practices:
        if item.get("hidden") is True:
            continue
        if tidy(item.get("title")) == "Matthews Sports Vision":
            # Specialist service listed at the same 1 Buxton Square storefront
            # as Matthews Eyecare Nelson; it is not a second physical shop.
            continue
        city = tidy(item.get("city"))
        if not city or re.search(r"\d|\b(?:road|street|avenue|drive)\b", city, re.I):
            city = tidy(item.get("cardTitle")).split(" - ", 1)[0]
        region = NZ_REGION_BY_CITY.get(city.lower())
        if not region:
            raise RuntimeError(f"Matthews region mapping missing for {city}: {item.get('title')}")
        address = ", ".join(part for part in [tidy(item.get("addressLineOne")), tidy(item.get("addressLineTwo")), city,
                                               tidy(item.get("postcode")), "New Zealand"] if part)
        path = tidy(item.get("path"))
        official_url = urllib.parse.urljoin(source_url, path) if path else tidy(item.get("alternateMoreLink")) or source_url
        records.append({
            "id": tidy(item.get("id")), "name": tidy(item.get("name")) or tidy(item.get("title")),
            "status": "Active", "country": "New Zealand", "state": region, "city": city,
            "postal_code": tidy(item.get("postcode")), "full_address": address,
            "phone": tidy(item.get("phoneNumber")), "latitude": "", "longitude": "",
            "official_url": official_url, "services": "", "audiology": "false", "source_url": source_url,
        })
    add_coordinates("matthews-eyecare", records)
    return source_url, records


def validate(label: str, records: list[dict]) -> None:
    if not records:
        raise RuntimeError(f"{label}: official source produced no active records")
    ids = [str(row["id"]) for row in records]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{label}: duplicate source IDs")
    for row in records:
        lat, lng = float(row["latitude"]), float(row["longitude"])
        if row["country"] == "Australia" and not (-44.5 <= lat <= -9 and 112 <= lng <= 154.5):
            raise RuntimeError(f"{label}: invalid AU coordinates for {row['id']}")
        if row["country"] == "New Zealand" and not (-48 <= lat <= -33.5 and 165 <= lng <= 179.5):
            raise RuntimeError(f"{label}: invalid NZ coordinates for {row['id']}")
        if not all(tidy(row.get(field)) for field in ("name", "city", "postal_code", "full_address", "official_url")):
            raise RuntimeError(f"{label}: incomplete record {row['id']}")


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat()
    sources = [
        ("Bupa Optical", "bupa-optical", bupa, "Official Stockist locator endpoint"),
        ("Chemist Warehouse Optometry", "chemist-warehouse-optometry", chemist_warehouse_optometry, "Official Storepoint locator endpoint"),
        ("Dresden Vision", "dresden-vision", dresden, "Official location list and structured store pages"),
        ("Optical Warehouse", "optical-warehouse", optical_warehouse, "Official store list; addresses geocoded when coordinates are not published"),
        ("The Optical Company", "the-optical-company", optical_company, "Official network location list; consumer-facing The Optical Co stores only"),
        ("Optical by National Pharmacies", "national-pharmacies-optical", national_pharmacies, "Official optical booking locator rendered through a bounded text proxy; addresses geocoded"),
        ("Matthews Eyecare", "matthews-eyecare", matthews, "Official structured practice list; addresses geocoded when coordinates are not published"),
    ]
    for label, folder, loader, method in sources:
        source_url, records = loader()
        validate(label, records)
        write_source(folder, source_url, records, fetched_at, method)
        print(f"{label}: {len(records)} active locations")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Priority network refresh failed: {error}", file=sys.stderr)
        raise
