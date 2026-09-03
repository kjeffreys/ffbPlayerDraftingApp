# Draft Assistant V3 Rebuild Plan

## Goal

Rebuild the live draft assistant around fast, trustworthy decisions without throwing away the useful v2 data work.

The v2 data pipeline, VOR math, Yahoo-derived player pool, and market consensus work are worth keeping. The reset should focus on app architecture, league separation, mobile usability, and visible trust signals.

## League Separation

Each league should have its own data folder and its own local session state. The app can reuse the same React components and scoring engine, but league facts should not be mixed.

Proposed shape:

```text
public/leagues/champions-2026/profile.json
public/leagues/champions-2026/players.json
public/leagues/champions-2026/keepers.json
public/leagues/champions-2026/pick-map.json
public/leagues/champions-2026/overrides.json
public/leagues/passion-guillotine-1/profile.json
public/leagues/passion-guillotine-1/players.json
public/leagues/passion-guillotine-1/overrides.json
```

A small registry can power the league selector, but it should only point to separate league folders. It should not become one mixed league configuration file.

Local draft sessions should be keyed by league and user profile, for example:

```text
draft-assistant-v3:champions-2026:kyle
draft-assistant-v3:passion-guillotine-1:kyle
draft-assistant-v3:passion-guillotine-1:joanna
```

That keeps another user or another league from damaging the active draft state.

## Data Model

The app should separate these concepts:

- League profile: Yahoo league id, scoring, roster slots, bench, playoffs, platform, draft type.
- Player board: generated rankings, VOR, market ranks, projections, byes, risk flags.
- Draft state: picks already made, current pick, drafted rosters, undo/redo history.
- Pick map: snake order plus traded picks and keeper-occupied slots.
- Keepers: pre-draft unavailable players assigned to managers and slots.
- Overrides: player boosts, fades, mimics, injury/risk notes, analyst signals.
- Manager tendencies: historical preferences and current-league observations.

## Scoring Engine

Move draft scoring out of the UI. The engine should be a pure function:

```text
players + league profile + draft state + pick map + overrides -> recommendations
```

Recommendations should expose the components separately:

- VOR
- market value
- next-pick availability
- tier cliff
- roster fit
- bye pressure
- injury/news risk
- upside/volatile-player adjustment
- keeper/dynasty/superflex adjustment
- manager tendency risk
- trusted analyst signal
- manual override

The UI should show the conclusion and the major reasons, not every component all the time.

## Overrides

Keep both override styles:

- Percent boosts/fades: useful when the player should be better or worse before VOR is recalculated.
- Player mimic rules: useful when saying a player has a plausible season like another player.

These should be league-specific. A Champions rookie/superflex boost should not automatically affect a guillotine redraft league.

Each override should produce an audit label in the app, such as:

```text
Upside +12%
Comp: Darnell Mooney
CBS value signal
Injury discount
Manual fade
```

## Trusted Analyst Signal

Add CBS Sports Richard/Jamey value-pick guidance as an advisory signal. It should not override Yahoo ADP, FantasyPros, VOR, or league rules by itself.

Use it as a visible nudge when it agrees with value:

```text
CBS value signal: +0.4 to +1.2
```

Use lower weight when it conflicts with hard data:

```text
CBS likes him, but market/risk does not support a reach.
```

## Mobile Live View

The default live-draft screen should be phone-first and should not require horizontal scrolling.

Primary layout:

- Current pick and next owned pick.
- Best pick.
- Two backup picks.
- Compressed next 8-12 rows.
- Roster needs.
- Bye pressure.
- Search and draft action.
- Undo.

Full board and audit views can exist, but they should be secondary.

## Visual Clarity

Use color and small bars to reduce cognitive load:

- Green: clear value or steal.
- Blue: positional cliff or scarce tier.
- Yellow: wait/watch, ambiguous timing, medium risk.
- Red: avoid, reach, severe risk, bad value.
- Gray: weak or missing data.

For each player row, prioritize:

```text
Name / team / position / bye
VOR
market rank or ADP
value delta
gone-by-next-pick risk
risk/upside chips
```

## Bye Policy

Bye weeks should be a pressure signal, not a hard penalty. The app should warn when bye clustering creates real lineup trouble, but it should not bury a materially better player just to avoid a duplicate bye.

Suggested behavior:

- No penalty for a duplicate bye by itself.
- Small warning when two same-position starters share a bye.
- Stronger warning only when the projected starting lineup for that week becomes impossible or meaningfully weak.
- Playoff value should matter more than regular-season bye neatness.

## Champions Open Items

The current Champions seed is in `draft_prep/leagues/champions-2026.seed.json`.

Still needed:

- Full traded-pick map beyond Kyle owning Chase's first- and second-round picks.
- Final keeper-slot interpretation if Yahoo assigns keepers to explicit draft slots.
- Confirmation that the second keeper column is the rookie/former-rookie franchise keeper.
- Any manager/team display names if they differ from the chat names.
