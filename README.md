# Australia + New Zealand Optical Leasing Intelligence

Public-source network, centre, demographic and site-selection intelligence for Australian and New Zealand optical retail.

Planning a map for another industry? The [shared location data and industry map handover](docs/MULTI_INDUSTRY_HANDOVER.md) describes a separate AU/NZ place-data foundation, independent Car Wash and Surf applications, source extraction boundaries and a [starter prompt](docs/MULTI_INDUSTRY_STARTER_PROMPT.md). This is a proposed migration; the current optical application remains unchanged.

The local pilot now opens on **Explore locations**: a filterable candidate table with required ALL/ANY features, exact or minimum-count preferred matches, independent BN/other-optical filters, evidence profiles and editable saved hypotheses. Select a feature by retailer name or category. Unknown data cannot satisfy a required condition. Coverage is shown separately from match strength; no commercial prediction is made. **More → Network & data coverage** retains inventory charts. Map mode uses its own filters, as stated beside the results. Existing map, shortlist and site comparisons remain available.

Public evidence is adapted by `scripts/build_retail_environments.py`, also run after certification by `scripts/build_data_health.py`. See [retail environment methodology](docs/RETAIL_ENVIRONMENTS.md). Commercial group selections and their derived hypotheses belong only in the separate authenticated private companion, outside this repository. The public application never fetches that companion.

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

The local working draft separates store usability, source freshness, location setting and canonical place mapping. Read current counts and build dates from `data/data_health.json`; the application derives displayed totals from the loaded census. A rebuild reconciles the checked-in evidence and does not imply that every retailer source was newly checked. Stale-source warnings remain separate from network usability, and uncertain place mappings remain review work.

The working layout uses Map and Site planning, with Trends and Data Health under More. Site planning has one scrolling sidebar with Discover, Shortlist and Compare modes, retaining the previous opportunity/compare link identifiers. Explore opportunity carries a mapped retail place directly into Compare; existing-place selections retain the canonical place ID and reference coordinates. Add location or map point can select another mapped centre/corridor or a new point for area-based analysis. Exports and nested resizable panes are omitted from the planning sidebar. Candidate columns offer Remove candidate, and Clear candidates removes the entire manual shortlist. Map has separate Stores and Retail places search modes. Search/Apply (or Enter) applies pending edits; each visible layer retains its own applied filters when switching modes. Results cover all matching records, independently of the map viewport. Fit results moves the map explicitly. Browse all results opens a grouped, paginated right-hand panel; Back to results restores list position and focus. Old network/centres share links remain supported, and new links also retain public layer visibility. Retail-place pins cluster at wider zoom levels for readability; these visual groups do not establish shared place membership. The coverage link beside the build date opens the source and mapping checks. Destination details include the enriched directory research where available. These are local changes until explicitly published.

The independent/other layer combines OpenStreetMap `shop=optician` discovery, 337 practices from ProVision's official public locator, and individually reviewed public practice additions. ProVision is stored as a filterable affiliation rather than a retailer brand, and accepted identity remaps prevent duplicate practice pins. The broader independent layer remains non-exhaustive and is switched off by default in the two-country view. See [independent discovery and admission](docs/INDEPENDENT_INTAKE.md) for the separate supplier review queue, evidence requirements and rebuild steps.

The original OPSM-only map remains at:

https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/opsm/

Other retailer maps remain separate from the optical analysis:

- City Beach: https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/city-beach/
- Ozmosis: https://aydennicolle-cyber.github.io/opsm-store-locator/retailers/ozmosis/

## Leasing Views

- **Network:** filter by country, region and retailer; preserve proximity analysis, same-centre checks, pair comparison and CSV export.
- **Places:** search shopping centres, plazas and high-street corridors by name, geography, canonical property group, leasing arrangement, centre class, portfolio overlap, retailer presence and mapping confidence; inspect every mapped optical tenant and its public relationship evidence.
- **Opportunity:** retain the earlier public screening components, separately by country and location setting, alongside saved place shortlists and candidate comparison. These are exploratory screens, not predicted commercial results. Use Explore locations for user-defined retail patterns.
- **Trends:** review source dates, archived store snapshots and detected openings, closures or relocations.
- **Site planning → Compare:** hold three or more public candidate sites in a comparison tray, remove individual candidates or clear the shortlist.

The public map also provides:

- ABS SA2 demographic context and population-growth layers for Australia. The build validates every selected workbook column against its official header, preserves each indicator's reference year, suppresses unreliable rates for very small Census populations and clearly distinguishes equivalised household income from consumer spending. No consumer-spending dataset is currently loaded.
- Competitor saturation, reviewed centre and optional OpenStreetMap health, transport and parking layers.
- 1 km, 3 km, 5 km and 10 km catchment summaries using intersecting SA2-centroid estimates.
- A white-space score using market demand, competitive white space, centre strength, accessibility, network fit and format fit.
- Legacy lookalike components and screening completeness remain in Site planning. The primary Explore locations table uses explicit feature criteria and sorts by preferred matches, then name.
- Browser-local mapping corrections with public-safe CSV import/export. Corrections never enter share URLs or a server.
- Saved local views and sanitised share URLs that preserve public filters, candidates and map position.
- A printable client brief and filtered public CSV.
- View nearest stores by brand, ten nearest stores and competitor counts within 500 m, 1 km, 2 km, 5 km and 10 km.
- Add two stores from their detail panels to Compare to see straight-line distance; no separate drawing mode is used. Candidate comparisons also show distances between shortlisted sites.
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

## Saved comparisons

Site planning → Compare offers named browser-local snapshots under **Save / open comparisons**. Each save creates a separate group; editing or clearing the active selection does not alter saved groups. Opening a group retains the previous selection for a session-only restore. Saved groups preserve public candidate coordinates, canonical place IDs and screening settings; scores and area summaries are recomputed from current loaded evidence. Browser storage is specific to this origin and is not a cross-device backup.

Compare connects selected candidate points with optional dotted straight-line links. Hover, tap or keyboard activation reveals distances; a text list provides the same pairs. Fit selection frames the group. The summary deduplicates containing statistical areas before reporting their available population totals; those whole-area totals are not enclosed-polygon or customer-catchment estimates. Comparison names and saved-group metadata are not put into share URLs.

## Private Companion

The retail-environment pilot has a separate authenticated local companion outside this public repository. It binds to `127.0.0.1`, encrypts commercial inputs and saved hypotheses with AES-256-GCM using a macOS Keychain key, and loads no external scripts or map tiles. All analysis responses require authentication; a hidden panel is not the protection boundary.

Earlier handover notes describe a broader **Optical Leasing Workspace** with lease registers, relationships and alerts. That runnable installation was not located during this pilot. The pilot reuses the existing offline private analysis directory and security approach without claiming to restore those broader features.

Private inputs, comparisons, derived hypotheses and QA screenshots stay outside this repository. The companion's local README explains startup and the one-time login code. It provides no remote hosting or authenticated public deployment.

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

The priority-network importer accepts address geocodes only when structured country, state/region and locality/postcode evidence agrees with the original numbered address or named premises. Broad administrative and street points, conflicting addresses and ambiguous results require review. It writes unresolved public leads to `output/priority-geocoding-reviews/` and leaves that retailer's existing source feed intact. A cached geocode is reused only with a matching `geocoding_evidence.json` receipt; its original observation date is retained. Source-supplied coordinates and explicit legacy overrides remain separate inputs requiring their own quality review. Accepted geocodes are approximate points and do not prove trading status or centre membership.

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

The co-tenancy programme preserves the fixed ten-centre Australian opportunity pilot selected on 3 September 2026 and derives its ongoing Bailey shopping-centre scope from accepted store-place memberships. Newly added centres can await their first official-source research pass; Data Health exposes these gaps. It records accepted optical memberships and researched key co-tenants; it is a key co-tenancy profile, not a complete centre directory. Research-started, accepted-anchor, multi-category and freshness coverage are reported separately in Data Health, with older or ambiguous evidence explicitly qualified.

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

The captured Queensland Health spectacle-dispenser directory is supplementary public discovery evidence in `data/discovery/qld_health_dispensers.json`. Re-run `python3 scripts/reconcile_qld_dispensers.py` after a census rebuild to refresh its candidate comparisons. The report preserves source rows and hashes, flags incomplete premises and possible visiting services, and never admits stores or assigns centre membership. A missing match is a research lead, not proof of an omitted retailer; scheme participation does not establish complete Queensland coverage.

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
python3 scripts/serve_local.py --port 8001
```

Then open http://127.0.0.1:8001/.

For a local preview of the public tool, use `python3 scripts/serve_local.py --port 8001` and open http://127.0.0.1:8001/. The server blocks private outputs and does not serve pipeline or performance overlays. Keep private review artifacts outside this repository and browser. See [independent discovery and admission](docs/INDEPENDENT_INTAKE.md) for evidence rules and the broader discovery workflow.

## Add Another Retailer Map

```bash
python3 scripts/scaffold_retailer.py "Retailer Name"
```

This creates `retailers/<retailer-name>/` from the reusable map template without adding the retailer to the optical comparison.

### Population counts and boundary evidence

The market layer now retains the published 2021 population baseline and the actual 2021–2025 change in residents. Negative growth remains negative; missing counts remain missing. `scripts/enrich_market_population.py --population-workbook .cache/market-intelligence/abs-population.xlsx` adds these fields only when every existing 2025 value agrees with the original ABS workbook. It never reconstructs counts from rounded percentages.

Map polygons are generalised display geometry and can leave boundary gaps or overlaps. `python scripts/refresh_market_point_links.py` checks public place gaps/overlaps and Australian BN branch points against the official ABS ASGS2021 point-intersection service, caching evidence in `data/market_point_links.json`. A unique authoritative match takes precedence in the tool and builds; unresolved authoritative responses remain missing. Evidence is bound to the actual coordinate and cannot migrate to a moved point. This identifies a containing resident area, not a customer catchment, centre membership or demographic forecast.
