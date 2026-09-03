# Intel Mac development handover

This guide moves the complete **public Optical Leasing Intelligence project** from the current Windows machine to an Intel-based 2020 MacBook Pro. The Git repository is the source of truth for the application, public datasets, build scripts, tests, documentation and repository-specific Codex instructions.

Do not retire or wipe the Windows checkout until the final commit is visible on GitHub, the Mac clone is clean, and the checks in this guide pass on the Mac.

## What the Git repository captures

The repository contains:

- the static GitHub Pages application (`index.html`, `assets/` and retailer pages);
- public source snapshots, canonical review decisions and generated public datasets;
- Python and Node data/build scripts;
- Python and JavaScript tests;
- the GitHub Pages workflow; and
- `AGENTS.md`, which gives Codex the project's public-data and verification rules.

A clone does **not** include uncommitted or untracked files. Immediately before this handover guide was created, the Windows checkout had a large unpublished change set on `main`, including these new untracked files:

- `data/place_suppressions.csv`
- `data/store_coordinate_overrides.csv`
- `data/store_identity_review.csv`
- `scripts/audit_store_identities.py`

They and all related modified generated data, scripts and tests must be reviewed, committed and pushed in the next release. Do not rely on the Mac clone until `git status --short` on Windows is empty after the push.

## What Git deliberately does not capture

Do not copy dependency or cache directories. The Mac must recreate them for its own architecture:

- `node_modules/` and `.pnpm-store/` — reinstall from `package.json` and `pnpm-lock.yaml`;
- `.venv/` and Python bytecode — recreate the virtual environment;
- `.cache/market-intelligence/` — roughly 82 MB of downloadable ABS/Stats NZ build inputs; the market build downloads them again when required; and
- root `opsm_store_locator_raw.json` — an ignored duplicate of the tracked `retailers/opsm/source_snapshot.json` (their SHA-256 hashes matched during this audit).

Git also does not capture GitHub credentials, Git identity, Codex conversations/settings, Chrome browser storage, or the separate private Optical Leasing Workspace.

## Before the final Windows push

### 1. Export browser-local public work

Browser storage belongs to a particular origin. Check every origin used for development, especially the live GitHub Pages URL and `http://127.0.0.1:8000`; their data is separate.

In the application:

1. Open **Places**.
2. Select **Export local corrections**.
3. Select **Export property corrections**.
4. Open **Opportunity** and export the shortlist Summary and Tenant CSVs if it contains saved places.
5. Select **Share** and save the resulting sanitised URL; it preserves the current public filters, candidate sites and map position.

Keep these exports outside the public repository until their contents have been reviewed. The two correction CSVs can be imported into the application on the Mac.

For a fuller public browser-state backup, open Chrome DevTools on the relevant application page, choose **Console**, paste the following, and press Return:

```javascript
const keys = [
  "bailey-leasing-place-corrections-v2",
  "bailey-leasing-local-places-v1",
  "bailey-leasing-property-corrections-v1",
  "bailey-leasing-local-property-groups-v1",
  "bailey-leasing-place-shortlist-v1",
  "optical-leasing-saved-view",
];
const backup = Object.fromEntries(keys.map((key) => [key, localStorage.getItem(key)]));
const link = Object.assign(document.createElement("a"), {
  href: URL.createObjectURL(new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" })),
  download: "optical-leasing-public-browser-state.json",
});
link.click();
```

Inspect that JSON before transferring it and never add private leasing information to it or commit it. To restore it, open the same application origin on the Mac, open DevTools Console, and run:

```javascript
const picker = Object.assign(document.createElement("input"), { type: "file", accept: ".json" });
picker.onchange = async () => {
  const backup = JSON.parse(await picker.files[0].text());
  Object.entries(backup).forEach(([key, value]) => {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  });
  location.reload();
};
picker.click();
```

### 2. Back up anything private separately

The private **Optical Leasing Workspace** is intentionally outside this public repository. If it has been used, create and retain its encrypted backup using that companion's own backup function. Its records, attachments, reports and encryption material must not be copied into this repository, a Git patch, a URL, or a public browser-state export. Confirm the companion's restore and macOS Keychain requirements before retiring the old machine.

### 3. Validate and push the public release

At handover preparation on 3 September 2026, the three required builds completed, the JavaScript tests passed and the privacy scan passed. The Python suite still reported two failures in the unpublished data work:

- property health reported 47 of 50 Bailey shopping-centre records researched; and
- the derived Bailey co-tenancy scope did not yet match its researched-centre metadata. The six canonical places without co-tenancy research were `place-au-nsw-broadway-shopping-centre`, `place-au-qld-macarthur-central`, `place-au-qld-mt-gravatt-westfield`, `place-au-sa-port-adelaide-plaza`, `place-au-wa-claremont-quarter` and `place-au-wa-joondalup-lakeside-s-city`.

These are release blockers, not Mac compatibility problems. Resolve them with source-backed review decisions and co-tenancy research before the final push; do not weaken the tests, infer memberships from proximity, or alter counts to make the checks pass.

From the repository root, use the active Python environment and run:

```bash
python scripts/build_retail_places.py
python scripts/build_property_intelligence.py
python scripts/build_data_health.py
python -m unittest discover -s tests -v
node tests/test_intelligence.js
python scripts/scan_public_privacy.py
git diff --check
git status --short
```

Review all changes, including generated data and `data/network_events.json`. Then commit and push through GitHub Desktop or Git. Pushing `main` triggers the GitHub Pages workflow, so confirm both the commit and successful workflow on GitHub.

After pushing:

```bash
git fetch origin
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

The status must be clean and the two commit hashes must match. Pushing or deploying requires explicit user authorisation; Codex must not do either automatically.

## Set up the Intel Mac

The project has no Apple Silicon-only dependency. Its Python dependency is pure Python and the Node lockfile includes the normal optional macOS package, so an Intel Mac is supported. Reinstall dependencies rather than copying them from Windows.

1. Install current macOS updates.
2. Install Apple's command-line developer tools:

   ```bash
   xcode-select --install
   ```

3. Install GitHub Desktop and sign in to the GitHub account that can access `aydennicolle-cyber/opsm-store-locator`.
4. Install Homebrew for Intel Mac from [brew.sh](https://brew.sh/), then install the repository's CI-aligned runtimes:

   ```bash
   brew install python@3.12 node@22
   ```

5. Install Google Chrome if public store locators will be refreshed. The Playwright fetch scripts already recognise Chrome's standard macOS application path.
6. In GitHub Desktop choose **File → Clone Repository**, select `aydennicolle-cyber/opsm-store-locator`, and clone it to a normal local development folder. Do not clone from a downloaded ZIP because a ZIP has no Git history or remote configuration.

In Terminal, enter the clone and confirm it is the pushed revision:

```bash
cd /path/to/opsm-store-locator
git switch main
git pull --ff-only
git status --short --branch
git rev-parse HEAD
```

Configure Mac line endings and commit identity once if needed:

```bash
git config --global core.autocrlf input
git config --global user.name "Your Name"
git config --global user.email "your-github-email@example.com"
```

Replace the example identity with the identity attached to the GitHub account.

## Install project dependencies

From the repository root:

```bash
bash scripts/setup_mac.sh
source .venv/bin/activate
```

The setup helper creates the ignored `.venv`, installs `requirements.txt`, enables pnpm through Corepack when needed, and installs the locked Node dependencies. It expects Python 3.12 and Node 22. If Homebrew exposes versioned binaries outside the current shell path, follow the `brew info python@3.12` and `brew info node@22` instructions, then rerun it.

## Verify the clone before continuing development

Run the repository-mandated publishability checks:

```bash
python scripts/build_retail_places.py
python scripts/build_property_intelligence.py
python scripts/build_data_health.py
python -m unittest discover -s tests -v
node tests/test_intelligence.js
python scripts/scan_public_privacy.py
git status --short
```

The three builds can update generated timestamps or datasets. Review any resulting diff rather than discarding it automatically. Counts must always be derived from reconciled sources and must never be edited to reach a desired target.

Preview the static site:

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Exercise Network, Places, Opportunity, Trends and Compare, and check the browser console for errors.

The optional full market refresh downloads its cache on first use and requires network access:

```bash
python scripts/build_market_intelligence.py
```

Do not run public fetch/refresh scripts merely as a setup test: they contact external sources and may replace tracked snapshots after validation.

## Resume with Codex on the Mac

Open the cloned repository as the Codex project. At the beginning of the first task, ask Codex to read `AGENTS.md`, `README.md` and this handover, then inspect `git status` and the latest commit before changing anything. The repository instructions and code will transfer; the current Windows task transcript, global Codex preferences, installed plugins and machine credentials may not.

Use a fresh `codex/` branch for new work unless deliberately continuing on `main`. Never put private leasing material into the public project or its browser requests.

## Completion checklist

- [ ] Browser-local correction CSVs exported from every used origin.
- [ ] Sanitised share URL and any useful shortlist CSVs saved.
- [ ] Optional public browser-state JSON inspected and transferred privately.
- [ ] Private companion backup handled separately, if applicable.
- [ ] Required builds, tests and privacy scan passed on Windows.
- [ ] All intended modified and new files committed.
- [ ] Final commit visible on GitHub and Pages workflow successful.
- [ ] Windows checkout clean; `HEAD` equals `origin/main`.
- [ ] Mac clone created with GitHub Desktop, not a ZIP.
- [ ] Mac dependencies recreated with `scripts/setup_mac.sh`.
- [ ] Required checks passed on Mac and resulting diff reviewed.
- [ ] Local preview opened successfully.
- [ ] Windows machine retained until the Mac copy is verified.
