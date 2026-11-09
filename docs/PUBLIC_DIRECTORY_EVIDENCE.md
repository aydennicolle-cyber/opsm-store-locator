# Shared public directory evidence

The public map and the unified loopback map use the same permitted tenant evidence from `data/public_directory_captures.json`. The build does not open an encrypted workspace or read adjacent commercial files.

The input contains an allowlisted export of source-attributed publisher directories and accepted research-place identities. Historical source observation dates and native record identifiers are retained. Later captures supplement that export. Research selection, commercial labels, financial results, handover rows and local paths are not public input fields.

## Build and use

`scripts/public_directory_evidence.py` validates the input, adds accepted researched identities during the retail-place build, and applies tenant captures during the retail-environment build. The shared adapter reuses the directory overlay and optical evidence reconciler. Public profiles, retailer searches and tenant exports read these observations rather than reverting to the older selective tenant list.

Run all checks in `AGENTS.md` before publication. `tests/test_public_directory_evidence.py` covers private-field rejection, attributed identities, unknown coordinates, existing-identity protection and source-total reconciliation.

## Counting and uncertainty

- A complete centre capture means every available record in the documented official directory scope was extracted. It does not verify that every tenant is currently trading or reconcile the directory to physical occupied premises.
- A complete publisher list for a high street remains partial street coverage. Explicit street-boundary holds are retained. Neither proximity nor a publisher's wider neighbourhood list establishes membership.
- Source record counts reconcile to named records plus explicitly anonymous records. Street office and explicitly classified dining observations are anonymous counts. Unresolved activity or trading-hour evidence stays unknown.
- Native identifiers preserve multiple listings with the same name. Normalized brand presence, individual directory listings and census-linked optical outlets are separate measures.
- Directory optics supplement evidence; they do not create census stores or accepted place memberships automatically. Conflicts remain in the optical reconciliation display.
- A confirmed directory-scope absence needs an explicit dated review against a complete canonical-centre capture. A missing name, blocked request or partial list is unknown, not absence or closure.
- Accepted place identities without verified coordinates remain searchable, without a map pin, nearby-distance estimates or inferred demographic join. They are excluded from spatial lookalike rankings.
- Supplied commercial selections and private current-status evidence stay in the adjacent private analysis area. They are not served by this public adapter.

## Source provenance

Each capture records its source URLs, observation dates, available source total, capture method, declared scope, completeness and limitations. Each named record retains a source URL, native identifier, source categories, category basis and listing/scope status. Original private research captures and cumulative research ledgers remain intact outside this repository; only the independently publishable evidence subset is shared here.

Accepted research identities retain **all** identity source receipts in `retail_places.json` under `sources`, with the corresponding `observed_at` and any supplied publisher `source_date`. The identity's `reviewed_at` and `coordinate_source_url` remain separate. The primary `source_date` is null when the primary publisher date is unknown; it is never filled from the review date. Environment exports retain these receipts as `identity_sources`, `identity_reviewed_at` and `coordinate_source_url`.

## Public boundary and packaging

`public_directory_schema.py` defines closed schemas for the document, places, identity sources, captures, tenant records, native-ID objects, category receipts, verification histories and previous records, absence reviews, anonymous samples and hours counts. Unexpected fields fail validation, even on held or non-present listings. Duplicate JSON keys are rejected so a later key cannot hide content that remains in a raw download. The loader and standalone overlay both validate, and output projections select schema fields recursively instead of spreading input records. Generated directory branches are checked again after reconciliation.

Evidence dates must be valid ISO dates or timestamps. Publisher dates and imagery dates can retain month precision; native publisher update timestamps can retain Unix milliseconds. These checks do not refresh historical dates, convert unknown counts to zero, rewrite native identifiers, or infer current trading.

Source URLs require HTTPS, a public-form hostname or globally routable IP, no credentials and the standard HTTPS port. Local names, private/reserved/link-local/loopback addresses, numeric IP aliases and local paths fail validation. Known private research ID namespaces are rejected without imposing a publisher-ID naming convention.

Directory-scope absence additionally requires the **actual canonical place format** to be `Shopping Centre`, an audited complete `canonical centre` capture and an explicit dated feature review. `coverage.absence_eligible` expresses this prerequisite; it does not mark unreviewed features absent. A complete publisher capture for a street or precinct remains partial place coverage, irrespective of its capture label.

`scan_public_privacy.py` checks source captures and generated JSON/GeoJSON, CSV headers **and values**, and public text/browser files across `data`, `retailers` and `assets`. Directory evidence uses the same nested schema. Other datasets retain the broader private-field/reference checks.

The Pages workflow uses `package_public_site.py` and the exact file list in `scripts/public_site_files.json`. It no longer recursively publishes the entire data or retailer directory. The list includes runtime data, public downloads, the validated directory capture, brand assets and existing retailer maps/exports. New files need an explicit manifest change. Packaging refuses symlinks and an existing output directory, verifies the exact resulting file set and scans the prepared website before the upload step. To prepare and verify a local review bundle without deploying:

```sh
python scripts/package_public_site.py --output /tmp/optical-public-review
python scripts/scan_public_privacy.py --site /tmp/optical-public-review
```

Use a fresh output path. Run the required repository builds/tests first. `tests/test_public_directory_boundary.py` uses synthetic fixtures to cover each reported exploit value independently, nested field injection, provenance preservation, misleading completeness labels, generated hidden records, GeoJSON/CSV/report scanning, symlinks and website packaging.

These are offline structural controls. They do not resolve DNS, follow redirects, verify publisher ownership or prove that arbitrary free text is public. Source admission and changes to the schema or packaging manifest still require evidence review. No private commercial material is needed for these tests.

## Literal category and addressed-street enrichment

`directory_category_crosswalk.py` supplements existing classifications only where an explicit publisher activity label has a reviewed literal translation. It uses no brand list, commercial group or ownership assumption. Combined labels remain combined categories; vague labels remain unknown. Original source categories and previously attributed classifications are retained.

Addressed OpenStreetMap observations retain native object IDs, versions, edit dates and any explicit check-date tag. A radius can discover records but cannot establish membership: numbered street and locality tags must pass the existing study boundary, and separately managed centre premises or unresolved segment boundaries are held. A live map record is not verification of current trading. Unclassified activities remain unknown.

Street office and dining names are omitted. Additional count-only source samples are shown separately when overlap with earlier samples is unresolved; totals are not added. Only a fully explicit supported seven-day hours schedule is classified; unsupported schedules remain unknown. An explicit publisher brand tag can support a brand-search feature without creating another observation, outlet or operator.

Partial-source optical omissions are explained coverage differences: accepted census outlets remain linked even when an incomplete source does not list their operator. A complete capture of a street publisher page is still partial street coverage. Explicit identity or boundary holds, ambiguous same-operator branches and unmatched source listings remain review items. This does not verify trading or create new network outlets; raw linked/listed differences remain available.
