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

The repo includes `netlify.toml` with the expected static settings:

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
public/data_status.json
```

The league files contain:

```text
id, name, team, position, adp, vor, bye, ppg, redraftEcr, superflexEcr, dynastyEcr
```

`public/data_status.json` tells the app whether the checked-in data is stale or draft-ready, when it was generated, and which source URLs powered the refresh.

## League Roster Updates

Today, league roster settings live in two places:

```text
backend/league_config*.json  Backend VOR and refresh pipeline settings
index.tsx                   Frontend league dropdown, roster targets, lineup notes, and public board labels
```

When a league changes its roster, update the matching backend config first, regenerate with `refresh-json`, then update the `LEAGUES` profile in `index.tsx` so the UI target counts and notes match the generated data.

For the next hardening pass, consolidate these into one generated `public/league_profiles.json` file so roster settings have a single source of truth. Until then, go league-by-league before draft season and confirm teams, starters, flex/superflex slots, bench spots, K/DEF, scoring, and draft platform.

## Refresh Draft Data

The current 2026 refresh path uses zero-budget public sources:

```text
ESPN fantasy endpoint: 2026 player pool, ADP, projections, team, position, injury flag
DynastyProcess CSV: expert rankings, bye weeks, redraft/superflex/dynasty context
FantasyPros weekly stats pages: prior-season weekly scoring history for floor/history modeling
```

Before regenerating player values, check whether the external inputs still look parseable:

```powershell
cd D:\repos\ffbPlayerDraftingApp
.\.venv\Scripts\python -m backend.cli sources check --scoring HALF --output local\source_manifest.json
```

If that passes, regenerate all public draft JSON files:

```powershell
cd D:\repos\ffbPlayerDraftingApp
.\.venv\Scripts\python -m backend.cli --date 2026-08-10 refresh-json
```

Use the actual run date in `YYYY-MM-DD` format. The command writes dated audit artifacts under `backend/data/<date>/` and updates the deployable static files under `public/`.


## Champions Model Notes

Champions uses the actual Yahoo lineup from the 2026 screenshot:

```text
QB, WR, WR, WR, WR, RB, RB, RB, TE, W/R/T, W/R/T, Q/W/R/T, K, DEF, 6 BN, IR
```

Backend VOR is calculated from starting lineup slots, including `FLEX` and `SUPERFLEX`, instead of pretending Champions has three mandatory QB slots. The cockpit still uses soft draft targets for roster construction: `QB 2, RB 5, WR 7, TE 2, K 1, DEF 1`; QB3 should be earned by value, tier risk, and availability instead of forced by config.

Champions also blends a small superflex/dynasty ECR signal into the model score and uses `superflexEcr` as the market rank for cockpit availability/tier/dropoff logic. Normal leagues continue to use ADP.

## Data Reliability Checklist

Before trusting a draft file:

1. Run `sources check` and confirm it passes.
2. Save raw/intermediate artifacts under a dated backend run folder.
3. Confirm `public/data_status.json` says `draft-ready` and has today/tournament-day timestamps.
4. Review source row counts in `backend/data/<date>/refresh_manifest.json`.
5. Review `backend/data/<date>/audits/history_match_review.csv` and add explicit aliases for suspicious names.
6. Review unmatched or projection-only rookies manually.
7. Review `backend/data/<date>/audits/top50_<league>.csv` for VOR vs ADP/ECR breakage.
8. Generate each league profile separately through `refresh-json`.
9. Build the app and spot-check the board before deploying.
10. Commit and push the refreshed data before relying on Netlify/Vercel.

## Audit Files

Each `refresh-json` run writes local-only audit artifacts under `backend/data/<date>/audits/`:

```text
history_match_audit.csv      Full direct/alias/fuzzy/unmatched history map audit
history_match_review.csv     Short review list: low-confidence fuzzy rows plus top-120 missing-history players
top50_<league>.csv           Per-league top 50 with VOR, ADP, ESPN rank, ECR, and history flags
integrity_report.json        Pass/fail report for row counts, missing fields, byes, match coverage, and league outputs
```

The refresh command will not write `public/data_status.json` as `draft-ready` if integrity issues are present. Warnings and review rows are preserved in the audit folder so you can decide whether to add aliases, accept rookie projection-only players, or manually adjust a player.

## Current Data Notes

As of the August 10, 2026 refresh, the pipeline produced 566 usable draft rows per league, matched 481 players to historical weekly scoring, used 2 ESPN 2025-history fallbacks, had 0 missing bye rows, and had 0 low-confidence fuzzy matches needing review. The review CSV still flags 5 top-120 players with no historical match, which are rookie/new-context review items: Jeremiyah Love, Carnell Tate, Jadarian Price, Jordyn Tyson, and Makai Lemon. DynastyProcess reported a `2026-08-07` scrape date.

## What Needs Hardening Next

Highest-value next work:

1. Add manager/league-history tendencies into the recommendation model.
2. Add a top-50 audit viewer in the app so the CSV can be reviewed without leaving the browser.
3. Add a one-command deploy checklist for Netlify/Vercel after data refresh.
