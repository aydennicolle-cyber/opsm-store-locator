# Mac development handover

Updated 11 September 2026 for the current Optical Leasing Intelligence redesign.

This guide moves the complete **public application and development context** from the Windows checkout to a MacBook. GitHub is the source of truth for application code, public datasets, build scripts, tests, documentation and repository instructions. Keep the Windows copy until the Mac clone has passed the checks below.

## Current handover position

- Repository: `aydennicolle-cyber/opsm-store-locator`
- Development branch: `codex/decision-workflow-redesign`
- Live branch: `main`
- GitHub Pages deploys from `main`; pushing the development branch does not alter the live site.
- The development branch contains the decision-workflow redesign and the latest Stores, Locations, Opportunities, shortlist and candidate-comparison improvements.
- The final Windows validation on 11 September 2026 passed all required builds, 135 Python tests, JavaScript tests, the public privacy scan and `git diff --check`.

The latest generated census position is derived from the checked-in sources, not hard-coded targets:

- 1,503 canonical retail locations: 691 shopping centres and 812 high-street corridors;
- 2,151 accepted store-to-location memberships;
- 1,550 of 1,550 named-network stores usable, setting-classified and mapped to a retail location;
- no promoted store-identity or place-mapping exceptions;
- 319 of 691 shopping centres researched for property intelligence; and
- 376 property or centre-class research follow-ups still queued.

Source freshness is reported separately in Data Health. At the final Windows check it was 88.5%, so the build is operational but does not imply that every external source is current or every centre has complete property/co-tenancy research.

## What transfers through Git

A clone contains:

- the static GitHub Pages application (`index.html`, `assets/` and retailer pages);
- public source snapshots, reconciliation decisions and generated datasets;
- Python and Node build scripts;
- automated tests and privacy scanning;
- GitHub Pages workflow and lockfiles;
- `AGENTS.md`, `README.md` and this handover; and
- the repository history and remote configuration.

Git does not transfer uncommitted files. Before cloning the Mac, confirm the final development commit is visible on GitHub and the Windows working tree is clean.

## What deliberately stays outside the public repository

Do not commit or copy architecture-specific dependency and cache directories:

- `node_modules/`, `.pnpm-store/` and `.venv/`;
- Python bytecode and `.cache/market-intelligence/`; and
- the ignored root `opsm_store_locator_raw.json` duplicate.

The following also stay outside Git and must be handled separately if they are needed:

- browser-local saved views, corrections, locally created places and shortlist;
- GitHub credentials, Git identity and Codex conversation history;
- internal/client Word documents and generated handover outputs; and
- the separate private Optical Leasing Workspace, Bailey sales data, attachments, reports and encryption material.

The public repository must never contain private contacts, rents, lease terms, negotiation information or Bailey Nelson performance data.

## Export browser-local work before changing machines

Browser storage belongs to an exact origin. The live GitHub Pages site and each local address such as `http://127.0.0.1:8002` have separate storage.

For each origin that contains useful work:

1. Open **Locations** and export local store/location corrections and property corrections.
2. Open **Opportunities → Shortlist** and export the Summary CSV and Tenant CSV.
3. Use **Share view** and retain the sanitised link for useful filter/map states.
4. Keep the exported files outside the public repository until reviewed.

The current public browser-state keys are:

```text
bailey-leasing-place-corrections-v2
bailey-leasing-local-places-v1
bailey-leasing-property-corrections-v1
bailey-leasing-local-property-groups-v1
bailey-leasing-place-shortlist-v1
optical-leasing-saved-view
```

Corrections can be re-imported in the application. Shortlists are intentionally browser-local; the Summary and Tenant CSVs preserve their useful public evidence, while the locations can be re-bookmarked after opening the saved Share link.

Back up the private Optical Leasing Workspace separately through its own encrypted process. Do not place its backup inside this repository, a Git patch, a share URL or a public correction export.

## Clone the development branch on the Mac

1. Install current macOS updates and Apple command-line tools:

   ```bash
   xcode-select --install
   ```

2. Install GitHub Desktop and sign in to the account that can access the repository.
3. Install Homebrew from [brew.sh](https://brew.sh/), then install the CI-aligned runtimes:

   ```bash
   brew install python@3.12 node@22
   ```

4. Install Google Chrome if public retailer-locator refresh scripts will be used.
5. In GitHub Desktop choose **File → Clone Repository**, select `aydennicolle-cyber/opsm-store-locator`, and clone it to a normal local development folder.
6. In Terminal, enter the clone and switch to the handover branch:

   ```bash
   cd /path/to/opsm-store-locator
   git fetch origin
   git switch --track origin/codex/decision-workflow-redesign
   git status --short --branch
   ```

Do not use a downloaded repository ZIP as the development copy; a ZIP omits Git history, branches and remote configuration.

Optional one-time Git configuration:

```bash
git config --global core.autocrlf input
git config --global user.name "Your Name"
git config --global user.email "your-github-email@example.com"
```

## Install dependencies

From the repository root:

```bash
bash scripts/setup_mac.sh
source .venv/bin/activate
```

The helper creates the ignored Python environment, installs `requirements.txt`, enables pnpm through Corepack when needed and installs the locked Node dependencies. If Homebrew exposes versioned binaries outside the shell path, follow the path instructions printed by `brew info python@3.12` and `brew info node@22`, then rerun the helper.

## Validate the Mac clone

Run the repository-mandated checks:

```bash
python scripts/build_retail_places.py
python scripts/build_property_intelligence.py
python scripts/build_data_health.py
python -m unittest discover -s tests -v
node tests/test_intelligence.js
python scripts/scan_public_privacy.py
git diff --check
git status --short --branch
```

The build scripts can refresh generated timestamps. Review any resulting diff; never edit counts to reach a desired total and never discard unexplained data changes.

Preview the static app:

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and exercise Stores, Locations, Opportunities, Compare and Data Health. Check that:

- Stores filters and results both scroll after dragging the divider;
- Independent / Other optical appears first under Other brands and banners;
- Opportunity Explore and Shortlist modes both work;
- all saved shortlist locations are profiled and mapped;
- adding/removing a shortlist item takes one click and displays confirmation;
- candidate search, placement and comparison work; and
- the browser console contains no errors.

The optional full market refresh downloads external inputs and should not be used merely as a setup test:

```bash
python scripts/build_market_intelligence.py
```

## Development context for the next Codex task

Open the cloned folder as the Codex project. Start the first Mac task with:

> Continue Optical Leasing Intelligence development from `codex/decision-workflow-redesign`. Read `AGENTS.md`, `README.md` and `docs/MAC_HANDOVER.md`, inspect Git status and the latest commits, then verify the local preview before changing anything. Preserve the public/private data boundary and do not merge or publish without my approval.

The present product direction is a clear leasing decision workflow:

**Explore the network → identify locations → screen opportunities → build a shortlist → compare evidence → export a brief.**

Highest-value next development areas are:

1. continue simplifying the comparison workflow for selected stores and retail locations;
2. deepen shortlist comparison and client-ready multi-location briefs;
3. continue source-backed centre class, ownership/leasing and co-tenancy research;
4. refresh demographic and source-freshness coverage without inventing missing values; and
5. keep any Bailey performance configuration private and separate from the public lookalike screen.

## Completion checklist

- [ ] Development branch committed and visible on GitHub.
- [ ] Windows working tree clean after the branch push.
- [ ] Browser-local correction and shortlist exports saved where needed.
- [ ] Internal Word documents transferred separately using the ignored supplemental bundle.
- [ ] Private Optical Leasing Workspace backed up separately, if used.
- [ ] Repository cloned with GitHub Desktop on the Mac.
- [ ] `codex/decision-workflow-redesign` checked out on the Mac.
- [ ] Dependencies recreated with `scripts/setup_mac.sh`.
- [ ] Required builds, tests and privacy scan pass on the Mac.
- [ ] Local preview opens and the core interaction checklist passes.
- [ ] Windows checkout retained until the Mac copy is verified.
