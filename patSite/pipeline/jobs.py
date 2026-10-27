"""Daily jobs: sync games, grade finished picks, backtest, predict upcoming games."""
import logging
import time
from datetime import timedelta

import requests
from flask import current_app
from sqlalchemy import func

from patSite import db
from patSite.clock import today_et, utc_now
from patSite.Models import Game, ModelRun, Prediction
from patSite.pipeline import espn, features, model
from patSite.pipeline.odds import no_vig_probability, profit

log = logging.getLogger(__name__)


def sync_games(start=None, end=None, fetch=espn.fetch_scoreboard, pause=0.2):
    """Upsert games from ESPN, one day at a time, from start (default: just before the
    latest finished game, or DATA_START_DATE on an empty database) through tomorrow."""
    data_start = current_app.config["DATA_START_DATE"]
    if start is None:
        latest = db.session.query(func.max(Game.game_date)).filter(Game.completed.is_(True)).scalar()
        start = max(data_start, latest - timedelta(days=2)) if latest else data_start
    end = end or today_et() + timedelta(days=1)

    count = 0
    session = requests.Session()
    day = max(start, data_start)
    while day <= end:
        for data in espn.parse_scoreboard(fetch(day, session)):
            if data["game_date"] < data_start:
                continue
            _upsert_game(data)
            count += 1
        db.session.commit()
        if day.day == 1 or day == end:
            log.info("Synced through %s: %d games so far", day, count)
        day += timedelta(days=1)
        if pause:
            time.sleep(pause)
    for label, done in (("finished", True), ("upcoming", False)):
        synced = Game.query.filter(Game.completed.is_(done), Game.game_date >= start)
        priced = synced.filter(Game.home_ml.isnot(None)).count()
        log.info("%d of %d %s games since %s have moneylines", priced, synced.count(), label, start)
    return count


def backfill_odds(fetch=espn.fetch_summary, pause=0.2):
    """Look up moneylines for finished games that never had one (the scoreboard drops odds
    once a game ends). Each game is looked up once, whether or not odds turn up."""
    missing = (Game.query.filter(Game.completed.is_(True), Game.home_ml.is_(None),
                                 Game.odds_checked.is_(False))
               .order_by(Game.start_time).all())
    found = 0
    session = requests.Session()
    for i, game in enumerate(missing, 1):
        try:
            home_ml, away_ml = espn.parse_summary_moneylines(fetch(game.id, session))
        except espn.NotFound:
            log.warning("No ESPN summary for %s (%s at %s); skipping its odds",
                        game.id, game.away_team, game.home_team)
            home_ml = away_ml = None
        except espn.FeedError as exc:
            log.warning("%s; will retry on the next run", exc)
            continue
        if home_ml is not None and away_ml is not None:
            game.home_ml, game.away_ml = home_ml, away_ml
            found += 1
        game.odds_checked = True
        if i % 50 == 0:
            db.session.commit()
            log.info("Odds backfill: %d of %d games checked, %d lines found", i, len(missing), found)
        if pause:
            time.sleep(pause)
    db.session.commit()
    if missing:
        log.info("Odds backfill done: %d lines found for %d games", found, len(missing))
    return found


def _upsert_game(data):
    game = db.session.get(Game, data["id"]) or Game(id=data["id"])
    for key, value in data.items():
        # Keep the last known odds if the feed drops them after the game.
        if key in ("home_ml", "away_ml") and value is None:
            continue
        setattr(game, key, value)
    db.session.add(game)


def grade_predictions():
    pending = (Prediction.query.join(Game)
               .filter(Prediction.graded.is_(False), Game.completed.is_(True)).all())
    for pred in pending:
        home_won = pred.game.home_score > pred.game.away_score
        pred.correct = pred.pick == pred.game.winner
        if pred.bet_side:
            pred.profit = profit(pred.bet_odds, (pred.bet_side == "home") == home_won)
        pred.graded = True
    db.session.commit()
    return len(pending)


def _games_and_features():
    games = (Game.query.filter(Game.game_date >= current_app.config["DATA_START_DATE"])
             .order_by(Game.start_time, Game.id).all())
    rows = {row["game_id"]: row for row in features.compute(games)}
    return games, rows


def make_predictions():
    """Create or refresh picks for games that haven't started. Picks lock at tip-off.

    Value bets need market-blend weights from the latest backtest (run_backtest)."""
    run = ModelRun.query.order_by(ModelRun.created_at.desc(), ModelRun.id.desc()).first()
    weights = run.metrics.get("blend") if run else None
    games, rows = _games_and_features()
    train = [rows[g.id] for g in games if g.completed and model.eligible(rows[g.id])]
    if len(train) < model.MIN_TRAIN_GAMES:
        log.warning("Only %d training games; need %d before making picks", len(train), model.MIN_TRAIN_GAMES)
        return 0
    clf = model.fit(train)

    now, today = utc_now(), today_et()
    upcoming = [g for g in games
                if not g.completed and g.state == "pre" and g.game_date >= today and g.start_time > now
                and model.eligible(rows[g.id])]  # same burn-in rule as the backtest
    if not upcoming:
        return 0
    for game, home_prob in zip(upcoming, model.predict(clf, [rows[g.id] for g in upcoming])):
        pred = game.prediction or Prediction(game=game)
        pred.updated_at = now
        pred.home_prob = home_prob
        pred.pick = game.home_team if home_prob >= 0.5 else game.away_team
        pred.home_ml, pred.away_ml = game.home_ml, game.away_ml
        pred.market_home_prob = (no_vig_probability(game.home_ml, game.away_ml)
                                 if game.home_ml is not None and game.away_ml is not None else None)
        pred.combined_home_prob = (model.blend(weights, home_prob, game.home_ml, game.away_ml)
                                   if weights and pred.market_home_prob is not None else None)
        bet = model.value_bet(home_prob, pred.combined_home_prob, game.home_ml, game.away_ml, weights)
        pred.bet_side, pred.bet_odds, pred.bet_ev = bet if bet else (None, None, None)
        db.session.add(pred)
    db.session.commit()
    return len(upcoming)


def run_backtest():
    """Walk-forward backtest over all finished games since DATA_START_DATE; saved for the site."""
    games, rows = _games_and_features()
    finished = [rows[g.id] for g in games if g.completed and model.eligible(rows[g.id])]
    metrics = model.backtest(finished)
    if len(finished) >= model.MIN_TRAIN_GAMES:
        metrics["coefficients"] = model.coefficients(model.fit(finished))
    metrics["data_start"] = current_app.config["DATA_START_DATE"].isoformat()
    metrics["site_min_ev"] = model.MIN_EV
    db.session.add(ModelRun(created_at=utc_now(), metrics=metrics))
    db.session.commit()
    return metrics
