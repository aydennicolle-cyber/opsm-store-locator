#!/usr/bin/env python3
"""Stage an external AU/NZ optometry CSV without promoting supplier flags.

The output is a local review queue with immutable source snapshots and an explicit
decision ledger. It never writes to the published network or accepts proximity
as identity/place evidence. A rerun updates suggestions while preserving decisions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

from audit_store_identities import distance_metres, normalized
from reviewed_independents import public_url

ROOT = Path(__file__).resolve().parents[1]
DECISION_FIELDS = ["candidate_id", "source_record_hash", "decision", "canonical_store_id", "evidence_url", "reviewed_at", "reason"]
DECISIONS = {"Accepted new", "Linked existing", "Duplicate", "Excluded", "Needs review"}
FIELDS = [
    "candidate_id", "source_record_id", "source_record_hash", "source_verified", "country", "name", "address", "suburb", "postcode", "latitude", "longitude",
    "suggested_store_id", "suggested_store_name", "suggestion_basis", "distance_m",
    "review_status", "canonical_store_id", "evidence_url", "reviewed_at", "reason",
]


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    # Replace only after complete validation and serialization.
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    temp.replace(path)


def candidate_rows(source: list[dict], namespace: str) -> list[dict]:
    result = []
    seen = set()
    for row in source:
        if not {"id", "name", "country", "address", "lat", "lng", "verified_optometry"} <= row.keys():
            raise ValueError("Expected location-only CSV with source ID, name, country, address, coordinates and verified_optometry")
        if not row["id"] or row["id"] in seen:
            raise ValueError(f"Missing or duplicate source ID: {row['id']}")
        seen.add(row["id"])
        if row["country"] not in {"AU", "NZ"}:
            continue
        if row["verified_optometry"] not in {"true", "false", "unreviewed"}:
            raise ValueError(f"Unknown source verification flag: {row['id']}")
        # Invalid coordinates remain in the review queue and cannot produce
        # geographic suggestions. Supplier data must not disappear silently.
        candidate = {
            "candidate_id": f"{namespace}:{row['id']}", "source_record_id": row["id"],
            "source_verified": row["verified_optometry"], "country": row["country"],
            "name": row["name"], "address": row["address"], "suburb": row.get("suburb", ""),
            "postcode": row.get("postcode", ""), "latitude": row["lat"], "longitude": row["lng"],
        }
        candidate["source_record_hash"] = hashlib.sha256(json.dumps(candidate, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        result.append(candidate)
    return result


def valid_point(row: dict) -> bool:
    try:
        lat, lon = float(row["latitude"]), float(row["longitude"])
    except (TypeError, ValueError):
        return False
    bounds = (-44.5, -9, 112, 154.5) if row["country"] in {"AU", "Australia"} else (-48, -33.5, 165, 179.5)
    return math.isfinite(lat) and math.isfinite(lon) and bounds[0] <= lat <= bounds[1] and bounds[2] <= lon <= bounds[3]


@lru_cache(maxsize=15000)
def name_key(value: str) -> str:
    return normalized(value)


def suggest(row: dict, stores: list[dict]) -> dict:
    blank = dict(suggested_store_id="", suggested_store_name="", suggestion_basis="No supported identity suggestion", distance_m="")
    if not valid_point(row):
        return {**blank, "suggestion_basis": "Invalid source coordinates; verify before use"}
    country = "Australia" if row["country"] == "AU" else "New Zealand"
    candidates = []
    name = name_key(row["name"])
    for store in stores:
        if store["country"] != country:
            continue
        other = name_key(store["name"])
        same_name = bool(name and name == other)
        distance = distance_metres(row, store)
        if distance > 500 and not same_name:
            continue
        similarity = SequenceMatcher(None, name, other).ratio()
        # A nearby optician with a different identity is not a match.
        if similarity < 0.78:
            continue
        basis = "Same name; review address and coordinate discrepancy" if same_name and distance > 500 else "Similar name and nearby point; public identity evidence required"
        candidates.append((not same_name, -similarity, distance, store["store_id"], store["name"], basis))
    if not candidates:
        return blank
    candidates.sort()
    _, _, distance, key, title, basis = candidates[0]
    return dict(suggested_store_id=key, suggested_store_name=title, suggestion_basis=basis, distance_m=f"{distance:.1f}")


def apply_decisions(rows: list[dict], decisions: list[dict], store_ids: set[str]) -> list[dict]:
    by_id = {row["candidate_id"]: row for row in rows}
    seen = set()
    for item in decisions:
        key = item.get("candidate_id", "")
        if key not in by_id or key in seen or item.get("decision") not in DECISIONS:
            raise ValueError(f"Unknown/duplicate candidate or invalid decision: {key}")
        seen.add(key)
        if not public_url(item.get("evidence_url", "")) or not item.get("reason", "").strip():
            raise ValueError(f"Decision lacks public evidence and reason: {key}")
        try:
            reviewed = date.fromisoformat(item.get("reviewed_at", ""))
        except ValueError as exc:
            raise ValueError(f"Invalid decision date: {key}") from exc
        if reviewed > date.today():
            raise ValueError(f"Decision date is in the future: {key}")
        canonical = item.get("canonical_store_id", "")
        if item["decision"] in {"Accepted new", "Linked existing", "Duplicate"} and canonical not in store_ids:
            raise ValueError(f"Decision target is not an admitted canonical store: {key} -> {canonical}")
        if item["decision"] in {"Excluded", "Needs review"} and canonical:
            raise ValueError(f"Unaccepted candidate cannot have a canonical assignment: {key}")
        if item.get("source_record_hash") != by_id[key]["source_record_hash"]:
            by_id[key].update(review_status="Needs review", canonical_store_id="", evidence_url=item["evidence_url"], reviewed_at=item["reviewed_at"], reason="Source record changed since the recorded decision; recheck identity, address and coordinates")
            continue
        by_id[key].update(review_status=item["decision"], canonical_store_id=canonical, evidence_url=item["evidence_url"], reviewed_at=item["reviewed_at"], reason=item["reason"])
    return rows


def stage(source_path: Path, output: Path, namespace: str, stores_path: Path, decisions_path: Path | None = None) -> dict:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", namespace):
        raise ValueError("Use a stable source namespace containing lowercase words/digits")
    # Local supplier review material must not accidentally become a public asset.
    try:
        output.resolve().relative_to((ROOT/"output").resolve())
    except ValueError as exc:
        raise ValueError("Stage external supplier records under the ignored project output directory") from exc
    source = candidate_rows(read_csv(source_path), namespace)
    stores = read_csv(stores_path)
    decisions_path = decisions_path or output/"decisions.csv"
    decisions = read_csv(decisions_path) if decisions_path.exists() else []
    rows = []
    for row in source:
        rows.append({**row, **suggest(row, stores),
                     "review_status": "Source rejected" if row["source_verified"]=="false" else "Pending",
                     "canonical_store_id": "", "evidence_url": "", "reviewed_at": "",
                     "reason": "Supplier flag is discovery evidence; independent public review required"})
    rows = apply_decisions(rows, decisions, {r["store_id"] for r in stores})
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    summary = {"source_namespace": namespace, "source_sha256": digest, "source_rows_au_nz": len(rows),
               "by_country": dict(Counter(r["country"] for r in rows)),
               "source_verification": dict(Counter(r["source_verified"] for r in rows)),
               "review_status": dict(Counter(r["review_status"] for r in rows)),
               "remaining_supplier_verified": sum(r["source_verified"]=="true" and r["review_status"] in {"Pending","Needs review"} for r in rows),
               "method": "Name and distance produce suggestions only. Explicit evidenced decisions required. No network/publication writes."}
    output.mkdir(parents=True, exist_ok=True)
    snapshot = output/f"source-{digest}.csv"
    if not snapshot.exists():
        snapshot.write_bytes(source_path.read_bytes())
    if not decisions_path.exists():
        write_csv(decisions_path, [], DECISION_FIELDS)
    write_csv(output/"review_queue.csv", rows, FIELDS)
    (output/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT/"output"/"independent-intake")
    parser.add_argument("--stores", type=Path, default=ROOT/"data"/"optical_stores.csv")
    parser.add_argument("--decisions", type=Path)
    args = parser.parse_args()
    print(json.dumps(stage(args.input, args.output_dir, args.namespace, args.stores, args.decisions), indent=2))


if __name__ == "__main__":
    main()
