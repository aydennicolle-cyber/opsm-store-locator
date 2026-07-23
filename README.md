# Australian Optical Retail Network

Public-source leasing and network comparison map for Australian optical retail.

Live map:

https://aydennicolle-cyber.github.io/opsm-store-locator/

Current validated network:

- OPSM: 335 stores
- Specsavers: 399 stores
- Bailey Nelson: 68 stores
- Combined: 802 stores

The original OPSM-only map remains at:

https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/opsm/

Other retailer maps remain separate from the optical analysis:

- City Beach: https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/city-beach/
- Ozmosis: https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/ozmosis/

## Map Functions

- Filter by retailer, state, location type, service, audiology, status, suburb or postcode.
- View nearest stores by brand, ten nearest stores and competitor counts within 500 m, 1 km, 2 km, 5 km and 10 km.
- Compare any two stores by straight-line distance.
- Drop a proposed leasing site anywhere on the map for the same proximity analysis.
- Review same-centre competitors only where a shared venue ID is supported by official naming or a reviewed override.
- Download the currently filtered network as CSV.
- View store totals by brand, state and location type, plus reviewed multi-brand and single-brand venues.

## Public Data

The combined schema is published in:

- `data/optical_stores.csv`
- `data/optical_stores.geojson`
- `data/optical_stores.meta.json`

Classification corrections are kept in `data/location_overrides.csv`. Low-confidence and unclassified stores are listed in `data/classification_review.csv` for manual review.

Only public store and venue information belongs in this repository. Do not add rent, lease expiry, turnover, sales performance, trading terms, internal contacts or private leasing notes.

## Refresh Data

Refresh OPSM from its public locator endpoint:

```bash
python3 scripts/fetch_opsm_stores.py
```

Refresh Bailey Nelson from its public store list, structured store pages and official map links:

```bash
python3 scripts/fetch_bailey_nelson_stores.py
```

Specsavers protects its raw endpoint, so refresh through its rendered public pages. This opens a controlled Chrome window and can take several minutes:

```bash
npm install
npm run fetch:specsavers
python3 scripts/build_specsavers_stores.py
```

Rebuild the combined network after refreshing any retailer:

```bash
python3 scripts/build_optical_network.py
python3 -m unittest discover -s tests -v
```

Each importer validates source counts, unique IDs, required fields and Australian coordinate bounds. A failed or incomplete refresh stops before replacing the last good snapshot.

## Classification Rules

Locations use four values:

- `Shopping Centre`
- `Main Street / Street-front`
- `Other`
- `Unclassified`

Classification uses official names and addresses. Proximity is never used to assign a shopping centre or shared venue. Reviewed corrections belong in `data/location_overrides.csv` so they survive future refreshes.

## Local Preview

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Then open http://127.0.0.1:8000/.

## Add Another Retailer Map

```bash
python3 scripts/scaffold_retailer.py "Retailer Name"
```

This creates `retailers/<retailer-name>/` from the reusable map template without adding the retailer to the optical comparison.
