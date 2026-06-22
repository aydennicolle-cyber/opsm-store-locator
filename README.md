# Store Locator Project

This repository publishes interactive store maps for Australian retail networks.

Current live map:

https://aydennicolle-cyber.github.io/opsm-store-locator/

## Files

- `index.html` is the root OPSM map kept for the current public share link.
- `opsm_stores.csv` and `opsm_stores.geojson` are the root OPSM exports.
- `retailers/opsm/` is the OPSM map in the reusable multi-retailer structure.
- `templates/map.html` is the starter map page for future retailers.
- `scripts/scaffold_retailer.py` creates a blank retailer folder from the template.
- `scripts/fetch_opsm_stores.py` refreshes OPSM from the public OPSM locator endpoint.

## Add A Retailer

```bash
python3 scripts/scaffold_retailer.py "Retailer Name"
```

Then replace `retailers/<slug>/stores.csv` and `retailers/<slug>/stores.geojson` with the cleaned store data.

## Refresh OPSM Data

```bash
python3 scripts/fetch_opsm_stores.py
```

The refresh pulls the OPSM locator response, filters to `country = AU`, removes duplicate store IDs, and rewrites the CSV and GeoJSON.
