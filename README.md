# Australian Optical Leasing Intelligence

Public-source network, centre, demographic and site-selection intelligence for Australian optical retail.

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

## Leasing Views

- **Network:** preserve retailer filters, proximity analysis, same-centre checks, pair comparison and CSV export.
- **Centres:** search reviewed centre entities and inspect public ownership, management, GLA, visitation, trade-area and redevelopment data where sourced.
- **Opportunity:** drop candidate sites, apply brand profiles and compare transparent component scores.
- **Trends:** review source dates, archived store snapshots and detected openings, closures or relocations.
- **Compare:** hold three or more public candidate sites in a fixed comparison tray.

The public map also provides:

- ABS SA2 demographic demand and population-growth layers.
- Competitor saturation, reviewed centre and optional OpenStreetMap health, transport and parking layers.
- 1 km, 3 km, 5 km and 10 km catchment summaries using intersecting SA2-centroid estimates.
- A white-space score using market demand, competitive white space, centre strength, accessibility, network fit and format fit.
- Renormalised scoring when components are unavailable, with results marked unreliable below 70% coverage.
- Saved local views and sanitised share URLs that preserve public filters, candidates and map position.
- A printable client brief and filtered public CSV.
- View nearest stores by brand, ten nearest stores and competitor counts within 500 m, 1 km, 2 km, 5 km and 10 km.
- Compare any two stores by straight-line distance.
- Review same-centre competitors only where a shared venue ID is supported by official naming or a reviewed override.

## Public Data

The combined schema is published in:

- `data/optical_stores.csv`
- `data/optical_stores.geojson`
- `data/optical_stores.meta.json`
- `data/sa2_market.geojson`
- `data/store_market_links.json`
- `data/centres.json`
- `data/brand_profiles.json`
- `data/network_events.json`
- `data/history/YYYY-MM-DD.json`

Classification corrections are kept in `data/location_overrides.csv`. Low-confidence and unclassified stores are listed in `data/classification_review.csv` for manual review.

Store-area fields distinguish `NLA`, `GLA`, `GFA` and `Estimated footprint`, and remain blank unless supported by a dated source in `data/public_area_overrides.csv`. A whole-building footprint is never presented as confirmed tenancy area.

Only public store, venue and market information belongs in this repository. Do not add rent, lease expiry, turnover, sales performance, trading terms, private contacts, inspection notes or negotiations.

## Private Companion

The separate **Optical Leasing Workspace** is installed outside this public repository. It binds to `127.0.0.1`, encrypts private records and attachments using a macOS Keychain key, and makes no external browser requests.

It includes candidate records, a lease register, landlord and agent relationships, interaction commitments, critical-date alerts, local spreadsheet import, encrypted backup/restore and private printable briefs. It starts with synthetic records only.

Private data and reports must stay in that companion. Alerts are workflow aids and are not a substitute for legal review.

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
python3 scripts/build_market_intelligence.py
```

The market-intelligence build uses official ABS Data by Region workbooks and SA2 boundaries, refreshes public centre profiles, joins all stores to SA2 and archives the successful network snapshot.

Run the complete public checks:

```bash
python3 -m unittest discover -s tests -v
node tests/test_intelligence.js
```

Each importer validates source counts, unique IDs, required fields and Australian coordinate bounds. A failed or incomplete refresh stops before replacing the last good snapshot. Review `data/network_events.json` before publishing changes.

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
