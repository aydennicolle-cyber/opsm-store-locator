# Retail environment exploration

Local pilot; no deployment is authorised. The public static application holds only public place, store and retailer evidence. Commercial cohorts, ranks, comparisons and hypotheses derived from them stay in a separate authenticated local companion outside this repository. There is no private endpoint or payload in the public app. Its ordinary saved searches use browser storage; do not put commercial selections there.

## Evidence and study boundary

The adapter reuses canonical places and remaps, accepted store-place memberships, current store certification, selected key tenants, captured destination directories, property classifications and existing demographic/access profiles. Raw source IDs, observations, source dates and URLs remain attached to every retail feature. A build date does not refresh source evidence.

Centre analysis uses the accepted canonical property and official centre directory. High-street analysis consistently uses the named street within its recorded locality: explicit street/frontage evidence and accepted optical memberships only. Broader precinct directory listings without street-address evidence are held outside this study, even if they were useful in the earlier precinct research. Side streets and nearby centres are not quietly added. This is an address-based study boundary, not a radius, parcel polygon or walking catchment. Existing map distance tools use straight-line distances and retain their separately labelled scopes.

Six selected street-address observations were added from local chamber directories and the City of Fremantle tourism retail map. They supplement the existing evidence without establishing a complete directory. Publication dates remain unknown where unstated. Directory listing does not independently verify current trading. Public evidence contains no commercial selection rationale.

Categories preserve combined source definitions. A health-and-beauty combined category is not silently split into two observations. Fashion subcategories additionally map to the broader fashion category. Retailer-name normalization is limited to case, accents, punctuation and ampersands; branch variants and distinct fascia are not silently merged. Brand presence counts once per location regardless of duplicate sources. Independent optical businesses retain their names and stable store IDs, and optical counts use distinct accepted outlets.

## Matching and comparisons

ALL requires every selected feature; ANY requires at least one selected feature. Both clauses apply together. Preferred features can require all (exact) or a specified minimum (partial). Partial matching never relaxes mandatory features. Duplicate selections count once. Unknown and conflicting evidence cannot satisfy a requirement. Only explicit reviewed absence establishes a missing feature; none is inferred from directory completeness or omission.

BN presence and other optical presence are independent filters. “No BN recorded” and “no other optical recorded” are distinct from verified absence; neither confirms a vacancy or an available leasing opportunity. Verified-absence filters remain usable but can legitimately return no results with the current evidence.

General group-comparison code accepts private inputs only in the separate companion. It reports present/all selected locations, unknowns, confirmed missing and present/known denominators. Unresolved or ineligible identities remain unknown rather than disappearing from the overall denominator. Format and GLA strata are explicit user choices; geography is not confused with industry centre class. Each feature contributes one presence per location. Counts are not occupied-tenancy shares or floor-area shares. Selective research and differences in centre size can explain observed differences. No association is causal or predictive, and Australian findings are not validated for New Zealand.

## Profiles and scope

Profiles separate physical scale, observed shopping purpose, tenant positioning, local importance and confidence. Unresearched importance remains unknown. Named owners/managers provide context without a quality bonus. Missing metrics say “not yet sourced.” Tenant-unit addresses are withheld from centre address fields unless a researched profile supplies a verified display address. Statistical areas, currencies, reference years and market-match basis remain visible. Source coverage never becomes confidence in commercial success.

The table and count share one applied search. Map mode retains its own filters; opening a place on the map does not transfer the search. Saved public hypotheses store criteria, not permanent scoring weights. Source evidence is re-evaluated whenever a search is opened.

## Verification

Run the required builds and tests in AGENTS.md, plus `node tests/test_environments.js` and the other JavaScript regression suites. Tests cover required/optional logic, duplicates, unknown versus absence, independent operator identity, denominator handling, scope holds, source references, tenant addresses and private-field rejection. The private companion separately verifies anonymous denial, origin checks, session revocation, encrypted save/reopen/update/delete and absence of external browser requests. Keep its screenshots and test artifacts outside this repository.

## Bounded directory captures

The authenticated companion can apply attributed full-directory captures through `scripts/retail_directory_overlay.py`. It preserves source IDs, capture totals, published category labels, scope holds and coming-soon/temporary-closure statuses. This generic adapter writes no datasets and reads no commercial selections. Captures and their private analysis remain outside this repository, behind the existing authentication and encryption boundary.

Directory extraction completeness and current-trading verification are separate fields. Published shopping and dining lists must both be captured, pagination must reconcile by unique source ID, and source-specific filters must be retained. Combined categories remain combined unless an explicit listing activity or previously attributed local category supports a narrower classification. Optical listings do not create general health/fashion co-tenant evidence merely through the focal store's presence. Independent ownership is not inferred from an unfamiliar name.

A reviewed absence may apply to a specifically checked feature in a complete centre directory. Its scope and receipt must be shown; it does not establish physical trading absence. Partial-directory omissions and unresolved street addresses remain unknown. High-street coverage is assessed against the declared address boundary and separately against the publisher's directory; neither certifies that all street premises are represented.

The private comparison defaults to complete centre captures, with known-data denominators, selected-location totals and unknowns shown together. Its full location matrix retains identity exceptions and locations excluded from that comparison. Search results distinguish documented matches, unresolved evidence and criteria contradicted by scoped absences. Fixed candidate IDs persist with saved private hypotheses. Public searches continue using public evidence only.
