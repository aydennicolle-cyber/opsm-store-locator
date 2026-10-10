# Independent discovery and admission

Broader external location lists are discovery sources. A supplier's verification flag does not prove that a row represents a unique, currently trading optical retail practice. Source rows, identity decisions and admitted public stores are separate records.

## Local intake

Run `scripts/stage_independent_candidates.py` with a location-only CSV, a stable namespace and a local output directory. `output/` is ignored as local working material. Keep private source data outside the repository; explicitly ignore any alternative working directory before use:

```sh
python scripts/stage_independent_candidates.py --input /path/to/location-export.csv --namespace supplier-independent --output-dir output/independent-intake
```

The CSV must contain `id`, `name`, `country` (AU/NZ), `address`, `lat`, `lng` and `verified_optometry` (true/false/unreviewed). All AU/NZ rows are retained, including supplier rejections and invalid coordinates. Canada is outside this intake's scope. The command produces an immutable source snapshot, review queue, counts and a decision ledger. Suggestions never admit a store. Proximity cannot establish identity or place membership.

Keep source exports and all crosswalks in the ignored local output directory when moving devices. Do not commit them or expose commercial performance, leasing targets, rents or private contacts. Only independently checked public facts belong in published data.

Record decisions in `decisions.csv` using its generated header. Accepted new, Linked existing and Duplicate decisions require a canonical store that already exists in the public registry; Excluded and Needs review have no canonical assignment. Every decision needs a public evidence URL, reason, review date and the queue's source-record hash. A changed source row returns to review; re-running an unchanged file preserves decisions. Removed or unrecognised source IDs fail validation so historical decisions cannot silently disappear.

## Admission to the public network

New accepted public practices are maintained in `retailers/reviewed-independents/stores.csv`, separate from generated OSM and ProVision refreshes. Each has a stable ID, evidence of a physical optical retailer, a meaningful premises address, reviewed coordinates, public evidence URLs and a review date. Retail optometry, prescription eyewear, contact-lens and sunglasses stores are supported. A missing postcode/locality or an `Other`/`Uncertain` setting does not exclude a retailer. Clinical-only, mobile and online-only services require evidence of a physical retail outlet before admission. Review potential matches against the existing registry before adding a canonical ID.

Trading status is separate from address quality and setting. Publicly evidenced future premises can be mapped as `Opening Soon`, and uncertain trading can remain `Unknown`; neither enters current competition or place counts. `Active` and legacy `Mapped` records are eligible when their premises pass quality checks. `Mapped` is not a claim of freshly verified trading. Record coordinate confidence separately: a professional directory point can support a premises reference without proving an exact tenancy pin.

The trading-name category and corporate affiliation are separate. “Independent / Other optical” does not certify independent ownership. For example, Canberra Vision Care's official site identifies its Luxottica group membership, which is recorded as an affiliation.

A verified storefront can enter network analysis while its shopping-centre/high-street setting remains uncertain. Such records stay in the promoted classification review queue and cannot enter place-specific analytics. A numbered street address is not sufficient to infer setting. Accepted centre memberships require explicit public evidence in `data/store_place_overrides.csv`.

An owned website is optional. Leave `official_url` blank when none is verified, and retain an authoritative public directory URL separately. Identity, coordinate and trading-status evidence URLs remain mandatory; directory inclusion alone does not establish current trading. Use `Unknown` when that remains unresolved, so the premises can be mapped without entering current competition.

Source freshness is checked against each practice's own review date. Adding a newly discovered practice does not count as evidence of a business opening in the history dataset.

Existing names and addresses can be corrected through `data/store_public_fact_overrides.csv`. Each correction requires a public evidence URL, date and reason, and preserves the source store ID, raw source freshness and any unreviewed status. A separately reviewed status belongs in `data/store_status_overrides.csv`. Coordinate corrections and their confidence belong in `data/store_coordinate_overrides.csv`. A confirmed outlet may use an explicitly low-confidence centre reference while its exact tenancy pin is unresolved; distance estimates involving these references are approximate. The store detail shows these qualifications and dated fact corrections.

When repairing an existing retailer's address without sufficient setting evidence, record `Unclassified` in `data/location_overrides.csv`. The reviewed facts marker preserves that uncertainty through the place build and promotes it to the setting review queue.

## Broader discovery and local review

`discover_optical_coverage.py` collects broad OSM optical/optometrist/eyewear leads without centre, high-street, rating, website, postcode or opening-hours gates. `discover_healthpoint.py` collects the paginated NZ optometry directory; `discover_optometry_australia.py` collects Australian professional-directory leads and groups repeated practitioner entries. Their outputs are candidates, not admitted stores. Australia state searches often return exactly 50 practitioners: that source cannot establish complete coverage. Retain source dates, failures, duplicates and uncertainty rather than treating an inaccessible website as closure.

The local reconciliation builder preserves supplier IDs and source hashes, validates explicit decisions and proposes identity matches separately from confirmed links. Exact aliases reduce duplicate counting; proximity alone never confirms identity. Re-run the intake after adding manual decisions so its queue and summary stay current.

The full reconciliation output directory can also contain `decisions.csv` for explicit chain or other source-row reviews. Its fields are `source_id,source_record_hash,decision,canonical_store_id,canonical_record_hash,evidence_url,checked_at,reason,related_source_id`. A source or canonical identity change invalidates a previous link and requires a new review. Address-format matching does not refresh trading evidence. Conflicting shop numbers and possible relocations remain explicit review cases until supported.

Rebuild this local view with `python scripts/reconcile_luc_records.py --pack <local-pack-directory> --output-dir <ignored-reconciliation-directory>`, then `python scripts/build_local_coverage.py` for the configured local handover workspace. The latter reads the configured pack and output paths; it is not a public data-fetching step.

The current loopback server (`python scripts/serve_local.py --port 8001`) previews public assets only and blocks private outputs and local overlay endpoints. Earlier versions enabled a private supplier/pipeline layer; that interface is not enabled by the current server. Keep reconciliation payloads in the separate private workspace, and never copy them into public assets. The new authenticated retail-environment companion does not restore the supplier/pipeline interface.

The retained offline **Target appraisal & research queue** logic preserves supplied plan/backup flags, sequence, priority and format. Research order checks opening/status discrepancies first, then opening-plan sites, then backups, with unresolved place mappings first within each group. Canada and reported-open records remain in the underlying reconciliation but are excluded from the ANZ target queue. These are source records, not necessarily distinct new stores.

Appraisal joins existing public place, screening and co-tenant evidence only after an explicit dated place-mapping review. Automatic name matches remain reference pins. Nearest current BN and nearest other proposal are separate straight-line context measures, not membership decisions or sales-transfer estimates. Missing research generates follow-up items, not zero demand or an investment score. Proposed status never increases the public screening score. Research publicly identifiable places without disclosing the private target designation or commercial data to external services.

## Rebuild and validation

```sh
python scripts/build_optical_network.py
python scripts/build_market_intelligence.py --reuse-market-data
python scripts/build_retail_places.py
python scripts/build_property_intelligence.py
python scripts/build_data_health.py
python -m unittest discover -s tests -v
node tests/test_intelligence.js
python scripts/scan_public_privacy.py
```

The market-data reuse option keeps the existing ABS demographic feature values and relinks the current store list. It may perform public ABS point queries for coordinates outside the simplified polygons. It does not refresh demographic releases. Publication still requires the repository's checks and explicit authorization.
