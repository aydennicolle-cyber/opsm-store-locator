# Data health and census methodology

The current store and place totals are observations, not targets. Coverage is described as complete only against the declared sources and the recorded cut-off date.

## Certification states

- **Certified**: current evidence, complete critical fields, and an authoritative physical-format decision.
- **Provisional**: plausible record that needs evidence or classification review.
- **Stale**: its required source is outside the freshness policy.
- **Quarantined**: retained for audit but deliberately excluded from public analytics.
- **Closed**: verified historical location, excluded from the active census.

Every discovery lead must ultimately resolve to a certified record, duplicate, closed/relocated record, non-comparable business, or unsupported lead. Pending leads prevent discovery reconciliation from reaching 100%.

## Store and place model

`location_type` describes the physical tenancy. A separate canonical place relationship describes membership in a shopping centre or named retail precinct. A street-front store may therefore belong to a named high-street precinct without being misclassified as a shopping-centre tenancy.

Phone, services and tenancy area are optional. Store identity, active status, country/region, locality, postcode, complete address, coordinates, current source, physical format and any applicable place relationship are critical.

## Freshness

Named official networks expire after 30 days. Community and secondary discovery sources expire after 90 days. A required source failure or partial census prevents certification.
