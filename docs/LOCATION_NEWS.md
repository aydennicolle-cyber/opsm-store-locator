# Location news and history

The static app now displays one shared history in store profiles, place profiles,
Explore retail environments and Trends. `assets/location-news.js` is the reusable
renderer; `assets/location-news.css` holds its layout. It accepts the same public
JSON everywhere, so layout changes do not require changes to research records.

Location and store panels start with one compact latest story. Expand News & history
to browse and filter the full feed; collapsing restores the latest story. The wider
news page keeps the full feed visible. Cards avoid repeating a truncated headline
as the first sentence, and supporting evidence remains under Sources & history.

Dated news entries with a shared source URL and the same geographic relationship
can appear together as one article card, including when one entry has additional
corroboration. The display date is the report date, not a shared opening date.
Each entry retains its reported status, event ID, sources and evidence versions;
the underlying records are never merged by this presentation step. Different dates,
direct versus area relationships, database observations, metrics and undated sources
remain separate. A later update can therefore surface a store independently again.

## Data lifecycle

`data/location_news_records.json` is the reviewed public input. It starts empty.
`scripts/build_location_news.py` combines it with the existing public development
signals and writes `data/location_news.json`. The data-health build invokes it.
The four overlapping legacy development IDs are retained as aliases of their
research project IDs. An unchanged re-import does not add another revision.

An event has a stable ID, aliases, optional parent event, explicit relationships
and immutable evidence versions. Each version retains its attributed statements,
source links, publication date, recording date, timing, uncertainty and metrics.
Earlier evidence is not overwritten. Corrections append a version. Source checks
are separate and may record failure without advancing the last successful read.

Dates can be a year, month, day or unknown. Feed order uses the most recent known
publication date across the event history. Recording dates do not make an old
article appear newly published. A passed forecast date is not completion evidence.
Unknown publication dates remain visible after dated entries. Public metric
observations require a period, unit and definition; portfolio metrics remain at
portfolio scope. News does not automatically overwrite census/profile facts.

## Relationships and privacy

`direct_place` and `direct_store` require named place or operator/address evidence.
`area_place` and `area_store` indicate surrounding-area relevance. They never
change canonical store membership, counts or competition analysis. The nearest
store helper uses valid coordinates, the same country and network eligibility.
The relationship records the point source and precision in its basis and includes
straight-line distance where measured. Missing coordinates leave an explicit
geographic review; a national or portfolio story is not arbitrarily assigned to
the nearest store. All such entries remain accessible in Trends.

`location_news_schema.py` is a closed public contract at every nesting level.
Unexpected fields stop the export with an actionable field error. This protects
against accidentally copying private research objects, planning labels or notes.
It is not a requirement for precise dates or exhaustive fact checking. Statements
distinguish attributed reporting, database observations and context. Private
commercial implications and the research population remain in the separate
authorised workspace. Source attribution is not independent corroboration.

`network_events.json` remains a separate snapshot-difference channel. Additions,
removals and address/coordinate changes are labelled as database changes, not as
confirmed openings, closures or relocations. Canonical identity remaps are applied
to the comparison without discarding the raw snapshot IDs.

## Exact-batch review

Prepare a public-safe candidate outside this repository. Private rehearsal files
are not valid inputs to the public schema. Use:

```sh
python scripts/prepare_news_review.py --input /absolute/private/candidate-news.json --output /absolute/private/new-review-folder
```

The command validates identities, sources and nested fields, merges existing
project histories, packages the static app using the explicit file manifest and
scans the finished site. It creates a review manifest with a SHA-256 of the exact
news payload and pending approval status. The separate `site` folder contains only
public-safe assets. No repository research data is changed and nothing is deployed.
Only serve that `site` folder for review, never its private parent directory.

After explicit approval of that exact batch, reconcile the approved additions into
the public input, rebuild, run the repository checks and compare the generated
payload with the approved hash. Any content change requires a new review hash.
The preparation command does not grant publication permission, enable recurring
research or publish a website.

## Verification

Run all repository-required builds, Python tests, `node tests/test_intelligence.js`,
`node tests/test_location_news.js`, the other applicable JS suites and the privacy
scan. Package and scan the exact review site. Exercise store/place profiles, area
labels, history expansion, filters, no-news/load-failure states and narrow screens.
The raw research evidence and unresolved geographic decisions remain reviewable
outside the repository; illustrative fixtures belong only in tests.
