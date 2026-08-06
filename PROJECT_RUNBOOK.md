# Draft Assistant Project Runbook

## Current Location

Local checkout:

```text
D:\repos\ffbPlayerDraftingApp
```

Git remote:

```text
https://github.com/kjeffreys/ffbPlayerDraftingApp.git
```

Current working branch:

```text
codex/draft-assistant-v2
```

The app is a static React/Vite site. The backend is a local Python data pipeline. Private league history should stay local and out of deployed hosting.

Python dependencies intentionally live in `backend/requirements.txt`, not at the repo root. Static hosts such as Netlify may auto-install a root `requirements.txt`; keeping it under `backend/` prevents the frontend deploy from trying to build Python packages it does not need.

## Start Locally

From PowerShell:

```powershell
cd D:\repos\ffbPlayerDraftingApp
npm install
npm run dev -- --host 127.0.0.1
```

Open:

```text
http://127.0.0.1:5173/
```

Production-style local check:

```powershell
cd D:\repos\ffbPlayerDraftingApp
npm run build
npm run preview -- --host 127.0.0.1
```

## Deploy For Phone Access

The repo now includes `netlify.toml` with the expected static settings:

```text
Build command: npm run build
Publish directory: dist
```

Free Netlify path:

1. Log in to Netlify.
2. Add new project.
3. Import from GitHub.
4. Pick `kjeffreys/ffbPlayerDraftingApp`.
5. Use the settings from `netlify.toml`.
6. Keep private data out of git and out of Netlify.

Vercel is also suitable for this app because it is static, but this checkout is not currently linked to a Vercel project.

## What The Browser Uses

The frontend loads static JSON from `public/`:

```text
public/players.json
public/vany.json
public/passion.json
public/guillotine.json
public/champions.json
```

Those files contain:

```text
id, name, team, position, adp, vor, bye, ppg
```

They do not currently include source timestamps, confidence scores, source URLs, or mapping audit metadata.

## Data Pipeline Shape

The intended backend flow is:

1. Sleeper player pool for canonical player identities.
2. FantasyPros ADP and bye data.
3. FantasyPros preseason projections.
4. FantasyPros prior-season weekly scoring.
5. League-specific scoring weights.
6. Manual boosts and rookie mimic overrides.
7. VOR replacement-level calculation.
8. Copy final league JSON into `public/`.

Current trust warning:

The checked-in public JSON files are snapshots. Before a real 2026 draft, regenerate them and keep the dated backend artifacts plus logs so each number can be audited.

## Source Preflight

Before regenerating player values, check whether the external tables still look parseable:

```powershell
cd D:\repos\ffbPlayerDraftingApp
.\.venv\Scripts\python -m backend.cli sources check --scoring HALF --output local\source_manifest.json
```

If this command fails, do not refresh `public/*.json` yet. Inspect `local/source_manifest.json`, update URLs/table parsing/aliases, and rerun the check.
## Data Reliability Checklist

Before trusting a draft file:

1. Confirm every data source URL still returns the expected table.
2. Save raw/intermediate artifacts under a dated backend run folder.
3. Produce a source manifest with fetch time, URL, row count, and parse status.
4. Review fuzzy matches and add explicit aliases for suspicious names.
5. Review unmatched projected players, unmatched ADP players, and missing bye weeks.
6. Review rookies and mimic overrides manually.
7. Compare top 50 by VOR against ADP and expert consensus for obvious breakage.
8. Generate each league profile separately.
9. Copy each audited `players_final.json` into its matching `public/*.json`.
10. Build the app and spot-check the board before deploying.

## What Needs Hardening Next

Highest-value next work:

1. Add a repeatable `refresh-data` command that regenerates all league JSONs.
2. Add source manifests and audit reports.
3. Make fuzzy matching reviewable in a generated CSV.
4. Connect local league-history tendencies into the recommendation model.
5. Add a visible data timestamp/confidence panel in the app.

