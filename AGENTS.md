# Optical Leasing Intelligence repository instructions

This is an existing public AU/NZ optical retail census and site-screening application. Preserve its static GitHub Pages architecture and public-data boundary.

## Mandatory data rules

- Run the data-health build and all tests before treating generated datasets as publishable.
- Do not hard-code a desired final store or retail-place count. Counts must be derived from successfully reconciled sources.
- Preserve raw source identifiers and canonical ID remaps.
- Proximity may create a review candidate but must never establish shopping-centre or precinct membership.
- A named-network store may enter network and competition analysis when it has a stable ID, valid coordinates, a meaningful address and no evidence it is closed or duplicated. Show stale-source warnings separately.
- Place-specific analysis requires an accepted canonical place mapping. Uncertain mappings stay in the promoted review list and are not silently inferred.
- Raw, unpromoted discovery leads are background evidence and do not count as manual-review failures.
- Never invent store status, address, place membership, commercial metrics or missing demographics.
- Keep private leasing information out of this repository, generated files, URLs, reports and browser requests.
- Do not push, merge to `main`, publish or deploy without explicit user authorization.

## Required checks

```text
python scripts/build_retail_places.py
python scripts/build_property_intelligence.py
python scripts/build_data_health.py
python -m unittest discover -s tests -v
node tests/test_intelligence.js
python scripts/scan_public_privacy.py
```
