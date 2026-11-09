# Local foundation repairs — 25 October 2026

Completed the bounded first-priority repair scope. Nothing was pushed, merged,
published or deployed. The local preview is http://127.0.0.1:8038/.

## Place identities

The nine-case register is `FOUNDATION_REPAIR_CASES.json`. Eight duplicate place
records were consolidated: 1,549 places became 1,541. These are observed results,
not target counts. All 3,088 store membership rows retain their original store IDs;
the original optical CSV and GeoJSON are byte-identical to the pre-goal baseline.
Previous place IDs resolve through remaps; old names and retired coordinate reviews
remain recorded. No store membership was assigned from proximity.

| Case | Result |
|---|---|
| Huonville | One Main Street corridor; Main Road retained as an alias, following user review. |
| Napier | Emerson/Emeson and missing-locality records consolidated using published locality and reviewed spelling evidence. |
| Birkenhead Point | Brand Outlet and Outlet Centre consolidated; both businesses and shop addresses retained. |
| HomeCo | Keysborough and Peninsula localities/addresses connected; Knoxfield updated to JLL's Harvey Norman Centre name; Rutherford remains a distinct, explicitly name-unverified place. |
| Murray Street | Wonthaggi and Colac identified from operator addresses; distinct stable IDs preserved. |
| Pakington Street | Newtown and Geelong West retained separately; three extra records reassigned by published addresses; Pakington Strand remains a centre. |
| Elsternwick | One corridor with both Glen Huntly/Glenhuntly spellings, following user review. |
| Rooke Street | Mall retained separately; user explicitly left its exact boundary unresolved. |
| Crown Street | Wider street, public mall and Wollongong Central remain distinct. Official directory and matching phone establish OPSM's centre membership. |

Manual decisions are identified separately from official-source checks. The user
subsequently authorised best-judgement resolution without unnecessary questions.
Rutherford's uncertain branding is visible; no speculative Home + Life merger was
made. Crown Street's wider-street point remains an approximate display reference,
not a surveyed extent or independently reviewed road geometry.

## Evidence now reaches the tool

Castle Towers previously showed no floor area, tenancy count or annual visits in
Explore despite stored evidence. It now shows 110,329 m², 223 reported tenancies and
18.6 million annual visits, with the original per-measure sources and dates.
The same process applies across places, rather than patching one profile.

Conflicting reports are retained and explicitly excluded from single-value
comparisons: floor area at Penrith, Indooroopilly, Ocean Keys and Royal Randwick,
and tenancy count at Penrith. Different figures may describe different periods or
scopes; no first-value-wins rule remains for these measures.

Ed.Square's profile and actual downloaded Summary CSV now use the supported centre
address rather than the optical shop-unit address. Address receipts separate
publication dates, general record dates and address-check dates. Unknown dates
remain unknown. Raw source addresses remain preserved. Supported canonical address
reviews also reach profiles; a tenant unit is not stripped to invent a centre address.

Explore and map searches recognise retained aliases. Place-summary exports include
aliases, address evidence, metric source reports and conflict explanations.

## Coverage means what it says

The assembled evidence currently covers 178 of 1,541 places. There are 103 complete
centre-source captures among 800 actual shopping-centre records, plus two other
complete source captures. No place is claimed to have independent current-trading
verification from these captures.

All 31 Bailey street corridors have some accepted non-optical listing evidence;
this is not complete tenant coverage. The older curated table's 3/31 result remains
visible as a labelled subset (9.7%), not as the total assembled research coverage.
Not researched, partly researched, complete source capture within scope and
independent trading checks are separate. Missing data and directory omissions do
not become verified absence. Rebuild dates do not refresh source checks.

## Verification and limits

All required builders, 396 Python tests, eight JavaScript suites, source privacy
scan, manifest-based local packaging with packaged privacy validation, and git diff
whitespace check passed. Details are in `FOUNDATION_REPAIR_VERIFICATION.json`.
The final alias/address changes were checked by rebuilding the dependent data-health
and environment outputs and rerunning the tests and packaging checks.

Browser checks covered Castle Towers metrics/source dates, Penrith conflicts,
Ed.Square's Explore and map addresses, the actual downloaded summary export,
Keysborough's address-check date, retained Elsternwick spelling search and the
coverage panel's denominators and legacy wording. Passing tests does not establish
real-world trading accuracy.

This was a targeted repair, not a national census, full optical refresh or shared
multi-industry database implementation. Many places still lack tenant research or
supported addresses. Current trading, unresolved mall extents and conflicting
historical property measurements remain explicit limitations.
