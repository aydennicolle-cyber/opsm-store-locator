"""Conservative address-result checks; a geocode never proves tenancy or trading.

Nominatim JSONv2 uses category (JSON used class). Its coordinates describe an
object centroid, so even an accepted building/POI result is approximate.
https://nominatim.org/release-docs/latest/api/Output/
"""
from __future__ import annotations

import math
import re
import unicodedata


CONTEXT_FIELDS = ("id", "name", "full_address", "country", "state", "city", "postal_code")
AU_STATES = {
    "australian capital territory": "act", "new south wales": "nsw",
    "northern territory": "nt", "queensland": "qld", "south australia": "sa",
    "tasmania": "tas", "victoria": "vic", "western australia": "wa",
}
STREET_WORDS = {
    "rd": "road", "st": "street", "ave": "avenue", "av": "avenue",
    "hwy": "highway", "pde": "parade", "dr": "drive", "cres": "crescent",
    "ct": "court", "tce": "terrace", "pl": "place", "ln": "lane",
}
BROAD_TYPES = {
    "country", "continent", "state", "region", "county", "administrative",
    "city", "town", "village", "hamlet", "suburb", "neighbourhood",
    "neighborhood", "quarter", "district", "city block", "municipality",
    "postcode", "postal code", "road", "street", "residential", "locality",
}


def normal(value: object) -> str:
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def street_normal(value: object) -> str:
    return " ".join(STREET_WORDS.get(word, word) for word in normal(value).split())


def contains(whole: str, part: str) -> bool:
    return bool(part) and f" {part} " in f" {whole} "


def region(value: object) -> str:
    value = normal(value)
    value = re.sub(r"\s+region$", "", value)
    return AU_STATES.get(value, value)


def context(record: dict) -> dict:
    return {key: str(record.get(key) or "").strip() for key in CONTEXT_FIELDS}


def without_unit(address: str) -> str:
    # Strip only a bounded unit token; the old [^,]+ pattern ate whole streets
    # when a source supplied "Shop G107 123 Main Road" without punctuation.
    return re.sub(
        r"^(?:(?:shop|suite|unit|level)\s+(?:[a-z]*\d+[a-z]*(?:[-/]\d+[a-z]*)?|ground|one|two)\b\s*[,/]?\s*|(?:lower\s+)?ground\s+floor\s*,?\s*)",
        "", address, count=1, flags=re.I,
    ).strip()


def rejection(result: dict, record: dict) -> str:
    """Return an actionable reason, or empty string for a premises match.

    These deliberately conservative checks can leave a real retailer unresolved.
    The caller must retain the lead for review instead of deleting the store or
    replacing its point with a broad location.
    """
    country = {"Australia": "au", "New Zealand": "nz"}.get(record.get("country"))
    if not country:
        return "unsupported country"
    try:
        lat, lon = float(result["lat"]), float(result["lon"])
    except (KeyError, ValueError, TypeError):
        return "missing or invalid coordinates"
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return "non-finite coordinates"
    within = (-44.5 <= lat <= -9 and 112 <= lon <= 154.5) if country == "au" else (
        -48 <= lat <= -33 and (165 <= lon <= 180 or -180 <= lon <= -175)
    )
    if not within:
        return "coordinates outside supported country bounds"
    address = result.get("address") or {}
    if not isinstance(address, dict) or address.get("country_code", "").lower() != country:
        return "country missing or conflicting"
    category = normal(result.get("category") or result.get("class"))
    kind = normal(result.get("type"))
    level = normal(result.get("addresstype"))
    if category in {"boundary", "highway", "natural", "waterway", "landuse"} or kind in BROAD_TYPES or level in BROAD_TYPES:
        # A residential *building* is a premise, unlike place=residential.
        if not (category == "building" and kind == "residential" and level not in BROAD_TYPES):
            return "administrative, street or broad area result"
    if category not in {"building", "shop", "amenity", "office", "healthcare", "tourism", "place"}:
        return "result is not an evidenced building, house or POI"
    if category == "place" and kind not in {"house", "houses", "isolated dwelling"}:
        return "place result is not a house"
    # Rank is supplementary only: the documented OSM categories vary. A fine
    # rank alone never establishes a numbered address or named premise.
    if result.get("place_rank") is not None:
        try:
            if int(result["place_rank"]) < 28:
                return "result rank is broader than premises"
        except (ValueError, TypeError):
            return "invalid result rank"
    expected_state = region(record.get("state"))
    actual_states = {region(address.get("state")), region(address.get("region"))} - {""}
    if country == "au":
        iso = str(address.get("ISO3166-2-lvl4") or "").lower()
        if iso.startswith("au-"):
            actual_states.add(iso[3:])
    if expected_state and actual_states != {expected_state}:
        return "state/region missing or conflicting"
    postcode = normal(record.get("postal_code"))
    actual_postcodes = {normal(part) for part in re.split(r"[;,]", str(address.get("postcode") or ""))} - {""}
    if postcode and actual_postcodes and postcode not in actual_postcodes:
        return "postcode conflict"
    locality = normal(record.get("city"))
    localities = {normal(address.get(key)) for key in (
        "city", "town", "village", "suburb", "municipality", "city_district", "neighbourhood"
    )} - {""}
    if not ((postcode and postcode in actual_postcodes) or (locality and locality in localities)):
        return "no corroborated postcode or locality"
    house = street_normal(address.get("house_number"))
    road = street_normal(address.get("road"))
    original = street_normal(without_unit(str(record.get("full_address") or "")))
    if house and road and contains(original, f"{house} {road}"):
        return ""
    numbered_street = re.search(
        r"\b\d+[a-z]?(?:[-/]\d+[a-z]?)?\s+[^,]+\b(?:road|rd|street|st|avenue|ave|highway|hwy|drive|dr|parade|pde|crescent|cres|court|ct|terrace|tce|place|pl|lane|ln)\b",
        without_unit(str(record.get("full_address") or "")), flags=re.I,
    )
    if house and road and numbered_street:
        return "numbered-street conflict; name alone cannot resolve a relocation"
    # A named building/centre may be an approximate reference only if the name
    # was already in the official premises context; a fallback query cannot
    # supply its own proof. Do not infer centre membership from this result.
    names = [result.get("name"), address.get(category), address.get("house_name")]
    for name in names:
        name = normal(name)
        if len(name.split()) >= 2 and name not in {"shopping centre", "shopping center", "eye care", "optical store", "medical centre"}:
            if contains(normal(record.get("name")), name) or contains(normal(record.get("full_address")), name):
                return ""
    return "no numbered-street or named-premises agreement"


def receipt_matches(receipt: dict, record: dict, cached: tuple) -> bool:
    result = receipt.get("result") or {}
    return bool(
        receipt.get("context") == context(record)
        and receipt.get("observed_at") and receipt.get("query")
        and not rejection(result, record)
        and str(result.get("lat")) == str(cached[1])
        and str(result.get("lon")) == str(cached[2])
    )
