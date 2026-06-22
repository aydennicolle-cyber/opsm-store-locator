# Store Locator Project

This repository publishes interactive store maps for Australian retail networks.

Current live map:

https://aydennicolle-cyber.github.io/opsm-store-locator/

Retailer maps:

- OPSM root map: https://aydennicolle-cyber.github.io/opsm-store-locator/
- Rhythm x City Beach: https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/city-beach/
- Rhythm x Ozmosis: https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/ozmosis/

## Files

- `index.html` is the root OPSM map kept for the current public share link.
- `opsm_stores.csv` and `opsm_stores.geojson` are the root OPSM exports.
- `retailers/opsm/` is the OPSM map in the reusable multi-retailer structure.
- `templates/map.html` is the starter map page for future retailers.
- `scripts/scaffold_retailer.py` creates a blank retailer folder from the template.
- `scripts/fetch_opsm_stores.py` refreshes OPSM from the public OPSM locator endpoint.
- `scripts/fetch_city_beach_stores.py` refreshes City Beach from the public City Beach locator endpoint.
- `scripts/fetch_ozmosis_stores.py` refreshes Ozmosis from the public Stockinstore locator endpoint used by the Ozmosis store page.

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

## Refresh City Beach Data

```bash
python3 scripts/fetch_city_beach_stores.py
```

The refresh pulls the City Beach Australia locator response, filters to Australian stores, removes duplicate store IDs, and rewrites the Rhythm-branded City Beach CSV and GeoJSON.

## Refresh Ozmosis Data

```bash
python3 scripts/fetch_ozmosis_stores.py
```

The refresh pulls the Ozmosis Australia locator response, filters to Australian stores, removes duplicate store IDs, and rewrites the Rhythm-branded Ozmosis CSV and GeoJSON.
