# Passion Guillotine I Draft Prep Packet

League: Passion Guillotine League I  
League ID: 602515  
Teams: Jeffreys and Blitz Squad Joanna  
Draft: Wednesday, August 26, 2026 at 8:15pm EDT

## League Facts From Yahoo

- 18 teams, 13 rounds, 1 minute per pick.
- Roster: QB, 2 RB, 2 WR, TE, 2 W/R/T flex, 5 bench, IR.
- No K and no DEF.
- Scoring starts Week 1.
- 0.5 PPR, 4-point passing TD, -1 interception, -2 fumble lost.
- Custom bonuses: +1 for 40+ yard completion, 40+ yard run, and 40+ yard reception.
- Waivers: $1000 FAB, 2-day waivers, 1-day waivers for players dropped by guillotine elimination.
- Draft order is not set yet; Yahoo says it is randomly determined about 30 minutes before draft.

## Config Maintenance Note

Last year had one generic guillotine setup. This year should be tracked as Passion-specific guillotine profiles:

- `passion-guillotine-1`: current Yahoo league 602515.
- `passion-guillotine-2`: reserve this name if a second Passion guillotine league opens.
- Keep last year's generic `guillotine` history separate so old roster/draft data does not pollute the 2026 Passion leagues.

## What We Are Optimizing For

This is not a normal fantasy draft. The first job is to survive Week 1. The second job is to survive long enough to use FAB after eliminated teams release better players.

The right model is:

1. Estimate fair value without ADP.
2. Use ADP as timing and cost.
3. Ask whether the player helps the actual roster you are drafting.

ADP is not a talent grade. ADP is the market's expected acquisition price.

## Shared Draft Labels

Use these labels instead of static green/yellow/red:

- `Buy Ahead`: our fair value is meaningfully earlier than ADP and the role/risk picture supports taking him a little early.
- `Fair At Cost`: value and market are aligned; draft for roster fit.
- `Risk Discount Needed`: the market still likes the player, but unresolved injury, legal/discipline, or Week 1 availability risk means he should slide in guillotine.
- `Let Fall`: good player, but the room is already paying for most of the upside.
- `Discount With Reason`: the price is attractive, but injury, role, games projected, or team context explains the fall.
- `Trap`: story/name/market price is ahead of the likely usable role.
- `Late Only`: Yahoo has weak or no usable ADP signal; review late, but do not chase.

## Last-Minute News Overlay: August 25, 2026

I reviewed the current board against Yahoo status flags and current public player news for draft-relevant injury, Week 1, and discipline situations. The app now has explicit `Risk Discount Needed` notes for the players where ADP/projection alone can mislead you.

- Puka Nacua: elite player, but groin/psoas practice absence plus possible short suspension risk means no #2 overall guillotine click.
- Christian McCaffrey: return-to-practice news is positive, but unspecified tightness still deserves a small first-round uncertainty discount.
- Ashton Jeanty and Jeremiyah Love: both have ankle-driven Week 1 uncertainty. Treat discounts as explained risk, not free value.
- Breece Hall: reports are optimistic for Week 1, but the groin injury is recent enough to break ties away from him at full price.
- Josh Jacobs: groin plus unresolved discipline/suspension review. Do not treat as a normal RB anchor.
- Malik Nabers: positive practice progress, but ACL/meniscus ramp and contact status still make him a discount-only pick.
- George Kittle: activated from PUP, but Achilles ramp/age risk makes him a risky TE price in guillotine.
- Chuba Hubbard and Tyler Warren: soft-tissue flags; draft only when the price accounts for risk.
- Alvin Kamara and Jordyn Tyson: expected missed time makes them traps for Week 1 survival.
- Travis Etienne Jr., Chris Olave, Mike Washington Jr., and MarShawn Lloyd: notable role/contingency beneficiaries from the same injury news, but Lloyd/Washington remain late contingency plays.

Sources checked before this overlay: Yahoo player/injury news, FantasyPros player pages/news, NBC Rotoworld player news, NFL.com, ESPN-linked reports, CBS, and team/beat reports surfaced through current search.

## Joanna Mode

Joanna needs fast narrative decisions:

- Can I start this player in Week 1?
- Is the discount real or explained by risk?
- Is the role clear enough for a guillotine lineup?
- Does the note say "do not chase"?

If the clock is low, Joanna should draft the highest fair-rank player who fits the roster and is not labeled `Trap`, unless the roster has a specific emergency need.

## Jeffreys Mode

Jeffreys gets the full surface:

- Fair rank
- ADP delta
- VOR
- Week 1 projection
- Risk tags
- Roster fit
- Late-round tag
- Joanna note for fast sanity checking
- Jeffreys note for model reasoning

Your old projection/floor idea is still useful, but ADP should be a separate timing layer. The arbitrage win is not "draft everyone below ADP"; it is "draft the players whose fall is over-discounted, and pass on the falls that are justified."

## Why Late Review Matters In An 18-Team League

Yes, reviewing teams and late players is worth it. This league drafts 234 players before waivers. The later rounds are where the board gets noisy and the room starts clicking familiar names.

Late tags:

- `Playable now`: can plausibly fill a Week 1 lineup hole.
- `Hidden floor`: boring, but role/volume is clearer than nearby names.
- `Contingent upside`: needs a depth-chart change, injury ahead, or role growth.
- `Stash only`: interesting, but not a Week 1 survival answer.
- `Bench clog risk`: likely to sit without enough upside.

## Draft-Day Workflow

Use one live tracker, but separate sessions for Jeffreys and Joanna:

1. Open the app profile for the team you are drafting.
2. Mark every drafted player.
3. When one of you picks, switch `Picking for` to `Me`; otherwise mark other picks as `Other`.
4. Use the workbook for quick narrative checks, especially Week 1 Watch and Late Rounds.
5. If the timer is under 15 seconds, pick the highest fair-rank non-trap who fits the roster.

## Week 1 Rule

Do not let an exciting uncertain player beat a boring startable player unless the roster already has enough stable starters. In guillotine, a luxury stash can be a Week 1 liability.
