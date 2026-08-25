# Fantasy Football Draft Assistant

A zero-budget draft cockpit for live fantasy football drafts. The app keeps private league data local, uses static hosting for the browser UI, and ranks players with VOR, ADP value, roster fit, tier dropoff, bye risk, manual adjustments, and league-specific tendencies.

## Run It

```powershell
npm install
npm run dev -- --host 127.0.0.1
```

Then open `http://127.0.0.1:5173/`.

For a production build:

```powershell
npm run build
```

## Draft-Day How To

- Pick the league first: `Default / Current`, `VANY`, `Passion`, `Guillotine (Legacy)`, `Passion Guillotine I - Jeffreys`, `Passion Guillotine I - Joanna`, or `Champions`.
- For Passion Guillotine I, use the Jeffreys and Joanna profiles as separate local sessions against the same Yahoo-derived player board.
- Use `Cockpit` for your private decision view. It shows the top recommendation, two backups, reasons, score components, and your roster snapshot.
- Use `Show Top 10 backups` when the top option is unavailable or you want a wider emergency list.
- Use `Board` when others can see your screen. This classic list hides recommendation reasons and looks like a normal ranked draft sheet.
- Press `Ctrl + .` to quickly toggle between `Board` and `Cockpit`.
- Mark picks with `Draft`. If `Picking for` is `Me`, that pick counts toward your roster and bye tracking.
- Switch `Picking for` to `Other` and enter a manager/team name to track the rest of the draft.
- Use `Undo` and `Redo` to correct mistakes.
- Use `Avoid`, `Boost`, `Fade`, and concern flags in Cockpit for last-minute injury, role, legal, playoff, bye, or personal-fade context.
- Use `Byes` to review your drafted players by bye week.
- Use `Export session` and `Import session` to move draft state between devices.

## Views

- `Board`: snoop-safe classic ranked list. It is still powered by the recommendation model, but only shows rank, player, team, position, bye, ADP, VOR, and draft action.
- `Cockpit`: private recommendation cockpit with Top 3, reasons, Top 10 drawer, manual flags, and roster context.
- `Details`: deeper working board with recommendation score and adjustment controls.
- `Byes`: your roster grouped by bye week.

Champions defaults to `Board` for in-person drafting. Online leagues default to `Cockpit`.

## Local History Tools

Private draft history stays local in `local/draft_history.sqlite`, which is ignored by git.

Create the database:

```powershell
python -m backend.cli history init
```

Create a manual CSV template:

```powershell
python -m backend.cli history template local\draft_history_template.csv
```

Import a manual CSV:

```powershell
python -m backend.cli history import-csv local\draft_history_template.csv --league vany --season 2025 --platform sleeper
```

Import Sleeper draft picks by draft ID:

```powershell
python -m backend.cli history import-sleeper --draft-id <draft_id> --league vany --season 2025
```

## Recommended Next Steps

- Import VANY history from Yahoo prior seasons and Sleeper last year into the local history store.
- Add Yahoo draft-result import once league IDs/OAuth details are available.
- Run simulated drafts against each league profile to tune recommendation weights.
- Add more explicit Champions/pick-trade context for the five-year league.
