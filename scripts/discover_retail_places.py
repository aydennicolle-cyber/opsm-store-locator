#!/usr/bin/env python3
"""Recall-first OSM discovery of named AU/NZ retail places for human reconciliation."""

from __future__ import annotations

import csv
import http.client
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DISCOVERY_DIR = DATA / "discovery"
QUEUE_PATH = DATA / "discovery_candidates.csv"
RUN_PATH = DISCOVERY_DIR / "retail_place_discovery_run.json"
OVERPASS_URLS = [
    os.environ.get("OVERPASS_URL", "https://overpass-api.de/api/interpreter"),
    "https://overpass.kumi.systems/api/interpreter",
]
FIELDS = [
    "candidate_id", "entity_type", "proposed_name", "country", "state", "locality",
    "source_name", "source_url", "discovered_at", "review_status", "disposition",
    "canonical_id", "reviewed_at", "evidence_notes",
]


def overpass(query: str) -> dict:
    payload = urllib.parse.urlencode({"data": query}).encode()
    last_error: Exception | None = None
    for attempt in range(2):
        endpoint = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
        request = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"User-Agent": "Optical leasing intelligence retail-place census/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, http.client.IncompleteRead) as error:
            last_error = error
            time.sleep(3 + attempt * 4)
    raise RuntimeError(f"Retail-place discovery failed: {last_error}")


def query_country(code: str) -> tuple[dict, list[dict]]:
    selectors = (
        'nwr["name"]["shop"="mall"]',
        'nwr["name"]["landuse"="retail"]',
        'nwr["name"]["amenity"="marketplace"]',
        'nwr["name"]["building"~"retail|commercial"]["shops"]',
        'nwr["name"]["highway"="pedestrian"]',
    )
    elements = {}
    runs = []
    for selector in selectors:
        print(f"{code}: querying {selector}", flush=True)
        try:
            payload = overpass(
                f"""
                [out:json][timeout:45];
                area["ISO3166-1"="{code}"][admin_level="2"]->.country;
                {selector}(area.country);
                out center tags qt;
                """
            )
        except RuntimeError as error:
            runs.append({"selector": selector, "status": "failed", "error": str(error)})
            print(f"{code}: failed {selector}: {error}", flush=True)
            continue
        found = payload.get("elements", [])
        runs.append({"selector": selector, "status": "complete", "records": len(found)})
        print(f"{code}: received {len(found)} records", flush=True)
        for element in found:
            elements[(element["type"], element["id"])] = element
    return {"elements": list(elements.values())}, runs


def place_type(tags: dict) -> str:
    if tags.get("amenity") == "marketplace":
        return "Market"
    if tags.get("highway") == "pedestrian":
        return "Named retail precinct lead"
    if tags.get("shop") == "mall":
        return "Shopping centre"
    if tags.get("landuse") == "retail":
        return "Retail centre or precinct lead"
    return "Named retail place lead"


def main() -> None:
    discovered_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    existing = {}
    if QUEUE_PATH.exists():
        with QUEUE_PATH.open(newline="", encoding="utf-8") as handle:
            existing = {row["candidate_id"]: row for row in csv.DictReader(handle)}
    total = 0
    country_runs = []
    for code, country in (("AU", "Australia"), ("NZ", "New Zealand")):
        raw, selector_runs = query_country(code)
        (DISCOVERY_DIR / f"retail_places_osm_{code.lower()}.json").write_text(
            json.dumps({"fetched_at": discovered_at, **raw}, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        country_runs.append({"country": country, "code": code, "selectors": selector_runs})
        for element in raw.get("elements", []):
            tags = element.get("tags", {})
            name = str(tags.get("name", "")).strip()
            point = element.get("center", element)
            if not name or point.get("lat") is None or point.get("lon") is None:
                continue
            candidate_id = f"osm-place-{code.lower()}-{element['type']}-{element['id']}"
            if candidate_id not in existing:
                existing[candidate_id] = {
                    "candidate_id": candidate_id,
                    "entity_type": "retail_place",
                    "proposed_name": name,
                    "country": country,
                    "state": tags.get("addr:state", ""),
                    "locality": tags.get("addr:suburb") or tags.get("addr:city") or tags.get("addr:town", ""),
                    "source_name": "OpenStreetMap retail-place discovery",
                    "source_url": f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
                    "discovered_at": discovered_at,
                    "review_status": "Pending",
                    "disposition": "",
                    "canonical_id": "",
                    "reviewed_at": "",
                    "evidence_notes": f"{place_type(tags)}; coordinates {point['lat']},{point['lon']}; lower-authority discovery lead only",
                }
            total += 1
    with QUEUE_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(existing.values(), key=lambda row: row["candidate_id"]))
    failed = sum(run["status"] != "complete" for country in country_runs for run in country["selectors"])
    completed = sum(run["status"] == "complete" for country in country_runs for run in country["selectors"])
    run_status = "complete" if failed == 0 else "partial"
    RUN_PATH.write_text(
        json.dumps(
            {
                "fetched_at": discovered_at,
                "status": run_status,
                "completed_queries": completed,
                "failed_queries": failed,
                "discovered_records": total,
                "queue_records": len(existing),
                "countries": country_runs,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(
        f"Discovered {total} OSM retail-place leads; queue now contains {len(existing)} candidates; "
        f"run status {run_status} ({completed} complete, {failed} failed)",
        flush=True,
    )


if __name__ == "__main__":
    main()
