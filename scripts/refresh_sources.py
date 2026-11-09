#!/usr/bin/env python3
"""Bounded, zero-LLM source refresh. Collect in isolation; retain uncertain feeds."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/source_refresh_jobs.json"
STATUS = ROOT / "data/source_refresh_status.json"
RECEIPT_FIELDS = {"fetched_at", "verified_at"}
AUTO_FIELDS = RECEIPT_FIELDS | {"phone", "fax", "hours"}


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def timestamp(value):
    if not value:
        return None
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result.replace(tzinfo=result.tzinfo or timezone.utc)


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def identified(records):
    result = {}
    for row in records:
        identity = row.get("sap_id") or row.get("identifier") or row.get("id")
        if not identity or identity in result:
            raise ValueError("Missing or repeated source identifier")
        if not row.get("name") or not row.get("full_address"):
            raise ValueError("Missing store name or address")
        lat, lon = float(row["latitude"]), float(row["longitude"])
        au = -44.5 <= lat <= -9 and 112 <= lon <= 154.5
        nz = -48 <= lat <= -33.5 and 165 <= lon <= 179.5
        if not math.isfinite(lat + lon) or not (au or nz):
            raise ValueError("Invalid AU/NZ coordinates")
        country = row.get("country", "")
        if (country in ("AU", "Australia") and not au) or (country in ("NZ", "New Zealand") and not nz):
            raise ValueError("Coordinates conflict with source country")
        result[identity] = row
    if not result:
        raise ValueError("Empty source feed; existing data retained")
    return result


def equal(field, a, b):
    if field in {"latitude", "longitude"} and a and b:
        return float(a) == float(b)
    return str(a or "").strip() == str(b or "").strip()


def compare(old_rows, new_rows):
    old, new = identified(old_rows), identified(new_rows)
    edits = []
    for identity in sorted(old.keys() & new.keys()):
        fields = sorted(k for k in old[identity].keys() | new[identity].keys()
                        if k not in RECEIPT_FIELDS and not equal(k, old[identity].get(k), new[identity].get(k)))
        if fields:
            edits.append({"source_store_id": identity, "fields": fields})
    added, missing = sorted(new.keys() - old.keys()), sorted(old.keys() - new.keys())
    review = bool(added or missing or any(set(e["fields"]) - AUTO_FIELDS for e in edits))
    canonical = [{k: v for k, v in new[i].items() if k not in RECEIPT_FIELDS} for i in sorted(new)]
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    return {"before_count": len(old), "after_count": len(new), "added_ids": added,
            "missing_ids": missing, "edits": edits, "requires_review": review,
            "content_sha256": digest}


def due(job, state, now):
    last = timestamp(state.get("last_attempt_at"))
    days = job["interval_days"] if state.get("status") == "refreshed" else job.get("retry_days", 2)
    return last is None or now >= last + timedelta(days=days)


def collect(job, root, output, now, runner=subprocess.run):
    """All collector writes are disposable until every declared feed passes."""
    report = {"last_attempt_at": now.isoformat(), "status": "failed", "feeds": []}
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="retail-source-") as temporary:
        stage = Path(temporary)
        for name in ("scripts", "data", "retailers"):
            shutil.copytree(root / name, stage / name, ignore=shutil.ignore_patterns("__pycache__"))
        for path in root.glob("opsm_stores.*"):
            shutil.copyfile(path, stage / path.name)
        if (root / "node_modules").exists():
            (stage / "node_modules").symlink_to(root / "node_modules", target_is_directory=True)
        env = {**os.environ, "HEADLESS": "1", **job.get("env", {})}
        deadline = job.get("timeout_seconds", 240)
        import time
        started = time.monotonic()
        try:
            with (output / "collector.log").open("w") as log:
                for command in job["commands"]:
                    remaining = deadline - (time.monotonic() - started)
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(command, deadline)
                    runner(command, cwd=stage, env=env, check=True, timeout=remaining,
                           stdout=log, stderr=subprocess.STDOUT)
            for folder in job["folders"]:
                folder_path = Path("retailers") / folder
                comparison = compare(rows(root / folder_path / "stores.csv"), rows(stage / folder_path / "stores.csv"))
                # Prevent a collector returning cached/old provenance from claiming a new check.
                geo = read_json(stage / folder_path / "stores.geojson", {})
                snapshot = read_json(stage / folder_path / "source_snapshot.json", {})
                receipt = timestamp(snapshot.get("fetched_at") or geo.get("metadata", {}).get("fetched_at"))
                if receipt is None or abs((now - receipt).total_seconds()) > 86400:
                    raise ValueError("Collector did not produce a current source receipt")
                report["feeds"].append({"folder": folder, **comparison})
            review = any(f["requires_review"] for f in report["feeds"])
            report["status"] = "needs_review" if review else "refreshed"
            # Export only declared public collector files, never whole HTML responses or logs to git.
            for name in job["outputs"]:
                candidate = stage / name
                if not candidate.is_file() or candidate.is_symlink():
                    raise ValueError(f"Missing collector output: {name}")
            for name in job["outputs"]:
                candidate = stage / name
                destination = (output / "candidate" / name) if review else (root / name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(candidate, destination)
            if not review:
                report["last_success_at"] = now.isoformat()
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
            # Do not put raw remote errors/bodies or credentials into a public status file.
            report["status"] = "failed"
            report["error"] = type(error).__name__ + ": collection or validation failed; existing feed retained"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="Show due collectors without fetching or writing")
    parser.add_argument("--job", action="append", default=[], help="Select registered collector(s)")
    parser.add_argument("--force", action="store_true", help="Ignore due dates for selected collectors")
    parser.add_argument("--max-jobs", type=int, default=3)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    config = read_json(CONFIG)
    status = read_json(STATUS, {"version": 1, "jobs": {}})
    jobs = config["jobs"]
    unknown = set(args.job) - {j["id"] for j in jobs}
    if unknown:
        parser.error("Unknown job: " + ", ".join(sorted(unknown)))
    selected = [j for j in jobs if (not args.job or j["id"] in args.job)
                and (args.force or due(j, status["jobs"].get(j["id"], {}), now))]
    selected.sort(key=lambda j: (status["jobs"].get(j["id"], {}).get("last_attempt_at", ""), j.get("priority", 9), j["id"]))
    selected = selected[:max(0, min(args.max_jobs, 20))]
    if args.plan:
        print(json.dumps({"due_jobs": [j["id"] for j in selected], "ai_calls": 0}, indent=2))
        return
    output = ROOT / "output/source-refresh"
    for job in selected:
        previous = status["jobs"].get(job["id"], {})
        result = collect(job, ROOT, output / job["id"], now)
        # Keep the last true success when a later collection fails or needs review.
        status["jobs"][job["id"]] = {**previous, **result}
        print(job["id"], result["status"], flush=True)
        if os.environ.get("GITHUB_ACTIONS") and result["status"] != "refreshed":
            print(f"::warning::{job['id']}: {result['status']}; existing feed retained. See source-refresh-review.", flush=True)
    status.update(last_run_at=now.isoformat(), ai_calls=0,
                  run_url=os.environ.get("SOURCE_REFRESH_RUN_URL", ""))
    status["coverage"] = config["coverage"]
    STATUS.write_text(json.dumps(status, indent=2) + "\n")
    output.mkdir(parents=True, exist_ok=True)
    summary = ["# Source refresh", "", "No AI/API calls. Source checks do not establish new publication dates.", ""]
    for job in jobs:
        state = status["jobs"].get(job["id"], {})
        summary.append(f"- {job['id']}: {state.get('status', 'not_checked')}; last success: {state.get('last_success_at', 'none')}")
    summary.extend(["", "Uncertain changes are retained in the source-refresh-review artifact; live feeds remain unchanged.",
                    "Sources outside the registered jobs remain manual; see source_refresh_jobs.json coverage."])
    summary_text = "\n".join(summary) + "\n"
    (output / "summary.md").write_text(summary_text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write(summary_text)


if __name__ == "__main__":
    main()
