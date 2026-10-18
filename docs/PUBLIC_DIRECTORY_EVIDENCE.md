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
