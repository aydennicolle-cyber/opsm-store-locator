"""Keep physical-record quality, current competition and location setting separate."""
import math
import re

CURRENT_STATUSES = {"Active", "Mapped"}  # Mapped retains its last-known/unverified label.


def valid_store_point(row):
    try:
        lat, lon = float(row["latitude"]), float(row["longitude"])
    except (KeyError, TypeError, ValueError):
        return False
    bounds = (-44.5, -9, 112, 154.5) if row.get("country") == "Australia" else (-48, -33.5, 165, 179.5)
    return math.isfinite(lat) and math.isfinite(lon) and bounds[0] <= lat <= bounds[1] and bounds[2] <= lon <= bounds[3]


def meaningful_address(row):
    address = str(row.get("full_address", "")).strip()
    # A postcode/locality alone is not a storefront address. Neither a missing
    # postcode nor an unclassified retail setting is itself a disqualification.
    return bool(len(address) >= 10 and re.search(r"\d", address) and re.search(r"[A-Za-z]", address)
                and address not in {"Australia", "New Zealand"}
                and (re.search(r"\b(?:street|streets|st|sts|road|roads|rd|rds|avenue|ave|lane|ln|drive|driveway|dr|way|walk|place|pl|parade|pde|highway|hwy|square|quay|terrace|tce|circuit|court|crescent|boulevard|boulevarde|blvd|broadway|kingsway|strand|esplanade|mall|plaza|centre|center|westfield|community health|shop|suite|suites|level|unit)\b", address, re.I)
                     or row.get("identity_reviewed") == "true"
                     or re.match(r"^\d{1,3}[A-Za-z]?\s+\S+", address)))


def current_competitor(row):
    return row.get("status") in CURRENT_STATUSES
