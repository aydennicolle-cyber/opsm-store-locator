# OPSM Australia Store Locator

This folder contains a local map and export of Australian OPSM retail stores.

Live map, once GitHub Pages has published:

https://aydennicolle-cyber.github.io/opsm-store-locator/

## Files

- `index.html` is the interactive map.
- `opsm_stores.csv` is the spreadsheet-friendly export.
- `opsm_stores.geojson` is the map data.
- `scripts/fetch_opsm_stores.py` refreshes the data from OPSM's public locator endpoint.

## Refresh Data

```bash
python3 scripts/fetch_opsm_stores.py
```

The refresh pulls the OPSM locator response, filters to `country = AU`, removes duplicate store IDs, and rewrites the CSV and GeoJSON.
