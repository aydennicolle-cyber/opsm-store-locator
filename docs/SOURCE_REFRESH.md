# Automatic public source refresh

The `Refresh public sources` GitHub Actions workflow runs daily at 19:37 UTC
(06:37 Sydney during daylight saving; 05:37 otherwise), and can be run manually
from the Actions tab. A push changing the workflow, runner or job register also
starts a run. It requires no AI key, Firecrawl account, paid scraping service or
persistent server. Existing source collectors may still be blocked by publishers.
GitHub-hosted runner usage remains subject to the account's Actions limits.

## What updates automatically

`data/source_refresh_jobs.json` defines 13 collector jobs, commands, explicit
output files, timeouts and intervals. At most three due jobs run each day.
Core locators and City Beach/Ozmosis run on a seven-day interval; grouped and
browser collectors run on a fourteen-day interval. Unchecked jobs run first;
failed/review jobs have a two-day backoff. Due dates measure attempts, not success.

Each collector runs in a disposable copy. The runner compares the complete CSV
against the current source feed using stable source IDs. Empty/duplicate feeds,
invalid coordinates, missing addresses, stale receipts, process failures and
timeouts preserve existing files. It adopts only feeds with unchanged identities
and no changes beyond phone, fax, hours and source receipt dates. Any added or
missing ID, changed address/name/coordinates/status/services, or other changed
field holds that entire collector's output for review. Missing listings never
establish a closure. Grouped collectors are all-or-nothing.

Only declared public output files can be copied back. The workflow rebuilds the
canonical network, places, property intelligence and Data Health, runs all Python
unit tests plus application checks, and scans for private data before committing.
An unexpected concurrent main-branch update rejects the push; it never forces it.
The reusable Pages workflow then checks and publishes the current main branch.
This explicit call is necessary because a push made with GITHUB_TOKEN does not
normally start another push-triggered workflow.

## Review and failures

Open `source-refresh.html` from the map's **Automatic source updates** link.
`data/source_refresh_status.json` records each job's last attempt, result, adopted
success and per-feed added/missing IDs and changed fields. This monitoring status
does not rewrite publication dates or accepted centre memberships.

The latest run links to an Actions artifact named `source-refresh-review`, retained
for 30 days. Candidate files and collector logs are in this artifact rather than
the live website. A collection failure is recorded in status while other sources
continue. A failed build/test/privacy scan prevents *all* publication for that run;
use the failed Actions run and artifact to diagnose it. A successful workflow does
not mean every source collector succeeded: inspect the per-job report.

For a candidate requiring review, ask Codex to inspect the artifact's changed
public evidence and compare it with main, preserve missing stores until closure
is corroborated, reconcile identities and accepted place mappings, and run the
repository's full checks before applying reviewed files. Do not blindly copy a
whole candidate over the live feeds. An unresolved candidate is collected again
after its retry interval, so artifact expiry does not approve or discard a change.

## Local commands

```bash
python scripts/refresh_sources.py --plan
python scripts/refresh_sources.py --job opsm-au --force --max-jobs 1
```

A normal run writes monitoring status even when collection fails. It does not
commit or publish. Before local publication, rebuild and run all checks in
AGENTS.md; if a source was adopted also run `build_optical_network.py` first.

## Boundaries

The job register explicitly lists unautomated sources: ABS/Stats NZ ingestion,
centre-directory/property research, place memberships, OSM discovery, reviewed
independents and eyewear networks without maintained collectors. Their existing
source freshness remains unchanged. Separate shared-place, Car Wash and Surf
repositories were not available through the connected GitHub installation and
are not automatically updated by this workflow. City Beach and Ozmosis here are
feeds inside the optical repository, not a claim that the Surf tool is connected.

Changedetection.io can supplement this system for selected directory or news
pages needing change alerts. It is not required for the current workflow and no
instance, subscription or AI summarisation was enabled. A future integration
must preserve the same source identity, review and shared-release boundaries.
