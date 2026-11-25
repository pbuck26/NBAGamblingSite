# Line-correction model: design

Date: 2026-11-25. Status: awaiting approval.

## Intent

The site owner wants the site's picks to have a real betting edge. The October backtest showed the
current model can't beat the DraftKings closing line (log loss 0.548 vs 0.510 on 358
games) and adds almost nothing on top of it, so more team-strength statistics won't help:
the line already prices them.

The new approach starts from the line and learns small, consistent corrections from
inputs the line may underweight. The owner picked "approach 2 + 3": blind-spot features
(schedule and travel, motivation, public money, the line's own recent errors, variance)
plus referee and player-availability features.

## Goals

- A second-stage model that takes the market's no-vig probability as its starting point
  and learns corrections from new feature groups, using only information available
  before tip-off.
- An honest test of whether any of it beats the line, with uncertainty shown, judged on
  games the model was never tuned on.
- Bets flagged only when the corrected model has recently beaten the line out of sample.
- The daily job collects the new data and the site shows the new evaluation.

## Non-goals

- Spreads, totals or player props as bet types (moneyline only; spread and total are
  used as inputs).
- A redesign of the homepage. The homepage keeps its current layout; the per-game
  numbers come from the new model.
- Using ESPN's BPI prediction in the model now: it only exists before tip-off, so there
  is no history to test it on. It is collected from now on for a later test.

## Anti-goals (failure even if it "works")

- Any feature that uses information not available before the bet is placed.
- Tuning anything on the holdout games, or quietly re-running the holdout until it looks
  good.
- Reporting a profitable backtest without its uncertainty, or hiding failed feature
  groups. Results are reported whatever they show.
- Breaking an already-deployed database.

## Constraints

- About 900 finished games since 2026-01-01; data must stay 2026-only.
- ESPN is the only source (scoreboard + per-game summary). Recon on real payloads:
  - Scoreboard: national-TV broadcasts (`broadcasts[].market == "national"`), periods
    (overtime when > 4), venue; for upcoming games, opening and current lines for the
    moneyline, spread and total.
  - Summary of a finished game: opening and closing moneyline, spread and total
    (`pickcenter`), referees (`gameInfo.officials`), full player box scores (minutes,
    started, did-not-play, points, rebounds, assists, +/-).
  - The summary's injury list shows *current* injuries, not injuries as of that game, so
    it can't be used historically. Upcoming games' injury lists are current and usable.
  - Referees were not yet listed for today's games in the morning; they may appear later
    in the day.
- Free hosting: the web app must stay light (no numpy/scikit-learn in web workers).
- Existing tables must not change shape (no migrations in the project yet), so new data
  goes in new tables that `create_all` adds on startup.

## Approaches considered

1. **More team-strength features in the current model.** Easiest; rejected because the
   line already prices this kind of information (shown by the October backtest).
2. **Line-correction model with blind-spot features.** Chosen.
3. **Approach 2 plus referees and player availability.** Chosen as the second part.

## Design

### Data

New table `game_details` (one row per game, keyed by game id), filled from the
scoreboard during sync and from each game's summary once it finishes:

- opening and closing moneylines, spread and total (closing values stay in `games` too)
- national TV flag, number of periods, venue city
- referees (list of names)
- player lines per team: player id, name, minutes, started, did not play, points,
  rebounds, assists, +/-
- for upcoming games only: the injury report snapshot and ESPN's BPI probability, as of
  the latest pre-game sync

The existing odds backfill becomes a general "finished-game details" step: one summary
request per finished game, done once.

### Features (all computed from earlier games plus pre-game information)

- **Schedule and travel:** distance flown since last game, time zones crossed, visiting
  Denver or Utah (altitude) without coming from altitude, games in the last 4 and 6
  nights, length of the current road trip, first game home after a long trip, overtime
  in the previous game. Uses a static table of the 30 arenas (location, time zone,
  elevation).
- **Motivation:** late-season tanking (poor record after March 1), late-season standing
  incentives (out of contention, or top seed safely locked), playoff game. Needs a static
  conference map; standings come from results.
- **Public money:** national-TV game combined with which side is the favorite.
- **The line's own errors:** for each team, the average of (result − market probability)
  over its last 10 games and over the season, shrunk toward zero.
- **Line movement:** change in no-vig probability from open to close (close-anchored model
  only).
- **Variance:** the gap between the win probability implied by the spread (scaled by the
  total) and by the moneyline.
- **Referees:** the crew's average home-team residual (result − market probability) from
  their earlier games, heavily shrunk.
- **Player availability:** share of each team's recent production (last 10 games) from
  rotation players who don't play. Historically, "doesn't play" comes from the box score
  (lineups are confirmed before tip, so this is known by the closing line). Live, it comes
  from players listed Out or Doubtful on the injury report (Questionable and Day-To-Day
  count as available; *builder's call*). Also a "top-two player missing" flag.
- **Existing model:** the current team-strength model's disagreement with the market,
  using only its walk-forward (out-of-sample) predictions for each game.

### Model

- Stage 1 stays as is (team-strength logistic regression).
- Stage 2, new: logistic regression with the market's log-odds as a fixed offset, so with
  no corrections it reproduces the market exactly. It learns an L2-regularized
  correction from standardized features, including the market's own log-odds (to capture
  any favorite-longshot bias). Fitted with scipy (already installed with scikit-learn).
- Two anchors: one on the opening line (no line-movement feature; models betting when
  picks post in the morning) and one on the closing line. Games missing an opening line
  are left out of the opening-anchored model.
- Live picks use the opening-anchored model applied to the line at the time of the daily
  run (close to the opening line in the morning). *Builder's call, made in design; the owner can
  switch it if they bet near tip-off.*
- All feature groups stay in the model. Only the regularization strength is chosen, on
  the development period, then frozen. The per-group table is for information; no groups
  are dropped based on it, to avoid tuning by selection. *Builder's call.*

### Evaluation

- **Development period:** games from 2026-01-01 to the end of the 2025-26 season.
  Walk-forward (each day predicted by a model fitted only on earlier days).
- **Holdout:** the 2026-27 season through 2026-11-24 (about 250 games). Run once, after
  the settings are frozen; reported whatever it shows. The window is fixed.
- **Forward:** games from 2026-11-25 on, predicted walk-forward by the daily job as they
  happen. The performance page shows development, holdout and forward separately.
  *Builder's call.*
- **Metrics:** log loss and Brier vs the market (the main test of edge), with bootstrap
  intervals; flat-stake return at the opening and closing price; closing-line value (did
  bets placed at the open get a better price than the close); a per-feature-group table
  showing what each group adds.
- With ~250 holdout games only a large edge would show clearly. The site's live record
  keeps accumulating the real evidence.

### Betting rule

Flag a bet only when the corrected model expects at least +3% at the posted price, odds
are no longer than +400, and the corrected model has beaten the market's log loss over
its last 200 out-of-sample predictions. This replaces the "model weight ≥ 0.1" rule.

### Site

- Performance page: corrected model vs market (development and holdout), the
  feature-group table, closing-line value, and open vs close returns.
- Homepage unchanged in layout; "Model" shows the corrected probability.

## Left to the builder

- Exact shrinkage constants, the arena coordinates table, how "rotation player" and
  "production" are defined, the bootstrap details, and the code layout.
- Exact definition of "late-season contention" from standings.
- How the live job handles referees missing at the morning run (treat as unknown =
  neutral).
