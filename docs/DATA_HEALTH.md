# Data health and census methodology

The current store and place totals are observations, not targets. Coverage is described as complete only against the declared sources and the recorded cut-off date.

## Separate usability, freshness and place mapping

The overall **Operational** state describes named-network usability, not a complete
or independently verified census. A named-network record can be usable with a
stable ID, valid coordinates, a meaningful address and no evidence that it is
closed or duplicated. Source freshness is shown separately. Place-specific analysis
requires an accepted canonical place mapping; uncertain mappings remain in review.

Promoted mapping reviews and background discovery leads are separate populations.
Unpromoted leads do not count as manual-review failures or accepted stores. A zero
high-priority duplicate queue is not proof that no duplicates exist.

## Store and place model

`location_type` describes the physical tenancy. A separate canonical place relationship describes membership in a shopping centre or named retail precinct. A street-front store may therefore belong to a named high-street precinct without being misclassified as a shopping-centre tenancy.

Phone, services and tenancy area are optional. Completeness of locality, postcode,
status evidence and physical format is reported without converting unknowns into
facts. Being mapped does not independently verify current trading.

## Retail-environment coverage

The assembled retail-evidence summary is calculated after building the current
environment profiles. It includes captured directories and curated observations.
Its denominators are registered places and actual Shopping Centre records, not
an assumed complete national inventory.

- **Not researched for tenant mix:** no accepted listing evidence or captured-source
  research is recorded. Other evidence, such as optical membership, may still exist.
- **Partly researched:** some listing evidence or a captured source with unresolved
  records exists; the whole-place inventory is not established.
- **Complete source capture within the stated research scope:** the publisher's
  source was captured completely. The study boundary and held records remain
  visible. This does not establish complete occupancy or current trading.
- **Independent trading verification:** a separate recorded check, never inferred
  from a complete directory or a successful rebuild.

The older key-tenant table remains available as an explicitly labelled curated
subset. Bailey corridor retail-mix coverage counts corridors with accepted
non-optical listing evidence from the assembled sources. It measures whether
evidence exists, not its completeness or commercial significance.

Missing information and directory omission remain unknown. Only a separately
reviewed, scoped absence may establish that a feature is absent from that source.

## Freshness

Named official networks expire after 30 days. Community and secondary discovery sources expire after 90 days. A required source failure or partial capture prevents a current-source certification; it does not by itself make every existing named-network record unusable.

Source publication dates, reporting periods, dates checked and build dates are
distinct. A rebuild changes the build date, not the source evidence dates. Property
measures retain their individual sources. Differing reported values are retained
and withheld from a single-value comparison until their periods/scopes can be
reconciled; reading one source later does not automatically make its figure newer.
