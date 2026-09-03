# Australia + New Zealand Optical Leasing Intelligence

Public-source network, centre, demographic and site-selection intelligence for Australian and New Zealand optical retail.

Plain-English definitions used in the application are maintained in the [leasing intelligence glossary](docs/GLOSSARY.md).

Live map:

https://aydennicolle-cyber.github.io/opsm-store-locator/

Historical baseline captured in July 2026 (not a current completeness target):

- OPSM: 392 stores
- Specsavers: 461 stores
- Bailey Nelson: 82 stores
- Oscar Wylee: 131 stores
- Independent / Other optical: 425 community-mapped locations
- Combined: 1,491 locations (1,269 Australia; 222 New Zealand)

The local working draft now separates store usability, source freshness, location setting and canonical place mapping. As of 3 September 2026 it contains 2,151 unique stores, including 1,550 usable named-network stores, plus 691 canonical centres/plazas and 812 high-street corridors. All 1,550 named-network stores have an accepted location setting and place mapping, with no promoted mapping reviews outstanding. The 6,192 unpromoted map records remain background discovery leads rather than consultant review work.

These counts are generated, not hard-coded. `data/data_health.json` reports each health dimension separately and keeps 6,192 unpromoted discovery leads informational. Six core retailer groups are selected by default: OPSM, Specsavers, Bailey Nelson, Oscar Wylee, George & Matilda and Eyecare Plus. Smaller named groups remain optional filters in the same Network view; their markers appear from zoom level 8 to prevent national-map crowding. Independent/Other appears from zoom level 10.

The independent/other layer combines OpenStreetMap `shop=optician` discovery with 337 practices from ProVision's official public locator. ProVision is stored as a filterable affiliation rather than a retailer brand, and accepted identity remaps prevent duplicate practice pins. The broader independent layer remains non-exhaustive and is switched off by default in the two-country view.

The original OPSM-only map remains at:

https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/opsm/

Other retailer maps remain separate from the optical analysis:

- City Beach: https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/city-beach/
- Ozmosis: https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/ozmosis/

## Leasing Views

- **Network:** filter by country, region and retailer; preserve proximity analysis, same-centre checks, pair comparison and CSV export.
- **Places:** search shopping centres, plazas and high-street corridors by name, geography, canonical property group, leasing arrangement, centre class, portfolio overlap, retailer presence and mapping confidence; inspect every mapped optical tenant and its public relationship evidence.
- **Opportunity:** rank Bailey-free places separately by country and location setting using footprint similarity, whitespace, optical validation and public retail context. Save a browser-local place shortlist, export summary and key-tenant CSVs, and print a selected-place brief. Optional Bailey performance CSVs are read only in browser memory.
- **Trends:** review source dates, archived store snapshots and detected openings, closures or relocations.
- **Compare:** hold three or more public candidate sites in a fixed comparison tray.

The public map also provides:

- ABS SA2 demographic context and population-growth layers for Australia. The build validates every selected workbook column against its official header, preserves each indicator's reference year, suppresses unreliable rates for very small Census populations and clearly distinguishes equivalised household income from consumer spending. No consumer-spending dataset is currently loaded.
- Competitor saturation, reviewed centre and optional OpenStreetMap health, transport and parking layers.
- 1 km, 3 km, 5 km and 10 km catchment summaries using intersecting SA2-centroid estimates.
- A white-space score using market demand, competitive white space, centre strength, accessibility, network fit and format fit.
- Transparent lookalike components and screening completeness; Bailey-free places below 60% completeness remain browsable but sort below sufficiently evidenced places.
- Browser-local mapping corrections with public-safe CSV import/export. Corrections never enter share URLs or a server.
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
- `data/retailer_registry.json`
- `data/store_identity_remaps.csv`
- `data/provision_identity_remaps.csv`
- `data/provision_identity_review.csv`
- `data/sa2_market.geojson`
- `data/store_market_links.json`
- `data/retail_places.json`
- `data/store_place_memberships.csv`
- `data/place_id_remaps.csv`
- `data/place_review.csv`
- `data/lookalike_places.json`
- `data/place_tenants.json`
- `data/place_key_tenants.csv`
- `data/property_intelligence.json`
- `data/property_groups.csv`
- `data/property_group_aliases.csv`
- `data/asset_relationships.csv`
- `data/property_attributes.csv`
- `data/property_research_status.csv`
- `data/data_health.json`
- `data/brand_profiles.json`
- `data/network_events.json`
- `data/history/YYYY-MM-DD.json`
- `data/shopping_centres.csv`
- `data/centre_store_memberships.csv`
- `data/centre_recognition_review.csv`

Legacy centre outputs remain for compatibility. The application now reads the canonical `retail_places.json` and `store_place_memberships.csv` outputs. Shopping-centre membership uses explicit retailer/tenant naming, exact address evidence or reviewed public overrides; proximity creates candidates but never establishes membership by itself. High streets are grouped by normalized street and locality with 800 m indicative comparison catchments.

Low-confidence and unclassified stores are listed in `data/classification_review.csv`. `data/centre_recognition_review.csv` is a broader centre audit covering possible missed centres, missing venue names and duplicate centre IDs.

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
python3 scripts/fetch_opsm_nz_stores.py
```

Refresh Bailey Nelson from its public store list, structured store pages and official map links:

```bash
python3 scripts/fetch_bailey_nelson_stores.py
python3 scripts/fetch_bailey_nelson_nz_stores.py
```

Specsavers protects its raw endpoint, so refresh through its rendered public pages. This opens a controlled Chrome window and can take several minutes:

```bash
npm install
npm run fetch:specsavers
python3 scripts/build_specsavers_stores.py
npm run fetch:specsavers:nz
SPECSAVERS_COUNTRY=NZ python3 scripts/build_specsavers_stores.py
```

Refresh Oscar Wylee and the optional independent/other public layer:

```bash
python3 scripts/fetch_oscar_wylee_stores.py
npm run fetch:oscar-wylee:nz
python3 scripts/fetch_independent_optometrists.py
```

Refresh the additional official network locators:

```bash
python3 scripts/fetch_additional_optical_networks.py
python3 scripts/fetch_priority_optical_networks.py
python3 scripts/reconcile_provision_affiliations.py
python3 scripts/reconcile_priority_network_identities.py
```

Rebuild the combined network after refreshing any retailer:

```bash
python3 scripts/build_optical_network.py
python3 scripts/audit_centre_recognition.py
python3 scripts/build_market_intelligence.py
python3 scripts/build_retail_places.py
python3 scripts/build_property_intelligence.py
python3 scripts/build_data_health.py
```

The market-intelligence build uses official ABS Data by Region workbooks and SA2 boundaries for Australia and refreshes public centre profiles. It archives a trans-Tasman network snapshot only when census certification passes. New Zealand stores retain explicit Stats NZ coverage status and are never joined to Australian market data.

The co-tenancy programme preserves the fixed ten-centre Australian opportunity pilot selected on 3 September 2026 and derives its ongoing Bailey shopping-centre scope from accepted store-place memberships. Every currently mapped Bailey shopping centre has an initial official-source research pass. It records accepted optical memberships and researched key co-tenants; it is a key co-tenancy profile, not a complete centre directory. Research-started, accepted-anchor, multi-category and freshness coverage are reported separately in Data Health, with older or ambiguous evidence explicitly qualified.

The optional Growth & Development map layer is built from `data/growth_development_signals.csv`. It shows selective source-backed public signals with explicit status, timing, temporary and long-term implications. It is not a complete planning or construction pipeline, and early-stage proposals are never treated as committed projects. The broader public-data automation and manual/private gaps are declared in `data/intelligence_layer_register.csv`. The client walkthrough is documented in `docs/client-walkthrough.md`.

Run the complete public checks:

```bash
python3 -m unittest discover -s tests -v
node tests/test_intelligence.js
python3 scripts/scan_public_privacy.py
```

Each importer validates source counts, unique IDs, required fields and country coordinate bounds. A failed or incomplete refresh stops before replacing the last good snapshot. Review `data/network_events.json` before publishing changes.

Discover named shopping centres, markets and retail precinct leads without automatically publishing them:

```bash
python3 scripts/discover_retail_places.py
python3 scripts/build_data_health.py
```

Discovery candidates remain excluded from analytics until a source-backed disposition is recorded.

Independent/other optical records are © OpenStreetMap contributors and are available under the [Open Database License](https://www.openstreetmap.org/copyright).

## Classification Rules

Locations use four values:

- `Shopping Centre`
- `High Street`
- `Other`
- `Uncertain`

Classification uses official names and addresses. Proximity is never used to assign a shopping centre or shared venue.

The centre audit may use distance, matching names and verified centre addresses to find review candidates, but it never changes published classifications. Add a centre to `data/shopping_centres.csv` and its source-backed store memberships to `data/centre_store_memberships.csv` only after checking an official centre directory, retailer page or equivalent authoritative source. These reviewed memberships survive future retailer refreshes.

## Local Preview

Moving development from Windows to an Intel Mac? Follow the [Intel Mac development handover](docs/MAC_HANDOVER.md) before retiring the original checkout.

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Then open http://127.0.0.1:8000/.

## Add Another Retailer Map

```bash
python3 scripts/scaffold_retailer.py "Retailer Name"
```

This creates `retailers/<retailer-name>/` from the reusable map template without adding the retailer to the optical comparison.
