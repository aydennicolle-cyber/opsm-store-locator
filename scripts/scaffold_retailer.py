#!/usr/bin/env python3
"""Create a new retailer folder for the Store Locator project."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "map.html"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "retailer"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/scaffold_retailer.py \"Retailer Name\"")
        raise SystemExit(2)

    name = " ".join(sys.argv[1:]).strip()
    slug = slugify(name)
    folder = ROOT / "retailers" / slug
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "index.html").write_text(
        TEMPLATE.read_text(encoding="utf-8").replace("{{RETAILER_NAME}}", name),
        encoding="utf-8",
    )

    csv_path = folder / "stores.csv"
    if not csv_path.exists():
      with csv_path.open("w", newline="", encoding="utf-8") as handle:
          writer = csv.DictWriter(
              handle,
              fieldnames=[
                  "name",
                  "id",
                  "state",
                  "city",
                  "postal_code",
                  "full_address",
                  "phone",
                  "latitude",
                  "longitude",
                  "services",
              ],
          )
          writer.writeheader()

    geojson_path = folder / "stores.geojson"
    if not geojson_path.exists():
        geojson_path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "metadata": {"retailer": name, "store_count": 0},
                    "features": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    print(f"Created {folder}")
    print(f"Map path: retailers/{slug}/index.html")
    print(f"Future URL: https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/{slug}/")


if __name__ == "__main__":
    main()
