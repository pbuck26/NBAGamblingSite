from datetime import date, datetime

import pytest

from patSite import db
from patSite.Models import Game, ModelRun, Prediction
from patSite.pipeline import jobs, model
from patSite.pipeline.odds import expected_value, payout
from tests.conftest import TODAY, finish_games
from tests.factories import fake_fetch, synthetic_season


def test_sync_keeps_only_2026_games(season):
    assert Game.query.count() == 6 * 80
    assert db.session.get(Game, "1") is None   # the Dec 31 game
    assert db.session.query(db.func.min(Game.game_date)).scalar() == date(2026, 1, 1)


def test_sync_is_idempotent_and_keeps_known_odds(season, app):
    day = date(2026, 2, 1)
    stripped = {day: []}
    for event in season[day]:
        event = {**event, "competitions": [{**event["competitions"][0], "odds": []}]}
        stripped[day].append(event)
    jobs.sync_games(start=day, end=day, fetch=fake_fetch(stripped), pause=0)
    assert Game.query.count() == 6 * 80
    assert Game.query.filter(Game.game_date == day, Game.home_ml.is_(None)).count() == 0


def test_backfill_odds_looks_up_each_finished_game_once(season):
    from tests.test_espn import SUMMARY_PICKCENTER
    no_odds = Game.query.filter(Game.completed.is_(True)).order_by(Game.start_time).limit(3).all()
    for g in no_odds:
        g.home_ml = g.away_ml = None
    db.session.commit()
    calls = []

    def fake_summary(event_id, session=None):
        calls.append(event_id)
        return SUMMARY_PICKCENTER if event_id == no_odds[0].id else {}

    assert jobs.backfill_odds(fetch=fake_summary, pause=0) == 1
    assert sorted(calls) == sorted(g.id for g in no_odds)   # only games missing odds
    assert (no_odds[0].home_ml, no_odds[0].away_ml) == (-380, 300)
    assert no_odds[1].home_ml is None and no_odds[1].odds_checked
    calls.clear()
    assert jobs.backfill_odds(fetch=fake_summary, pause=0) == 0
    assert calls == []                                      # never looked up twice


def test_backfill_odds_survives_missing_and_failing_summaries(season):
    from patSite.pipeline.espn import FeedError, NotFound
    gone, flaky = Game.query.filter(Game.completed.is_(True)).order_by(Game.start_time).limit(2).all()
    for g in (gone, flaky):
        g.home_ml = g.away_ml = None
    db.session.commit()

    def fake_summary(event_id, session=None):
        raise NotFound("404") if event_id == gone.id else FeedError("timed out")

    assert jobs.backfill_odds(fetch=fake_summary, pause=0) == 0
    assert gone.odds_checked             # a 404 is permanent: don't ask again
    assert not flaky.odds_checked        # a transient failure is retried next run


def test_predictions_only_for_games_that_have_not_started(season):
    assert jobs.make_predictions() == 12   # TODAY and tomorrow
    preds = Prediction.query.all()
    assert len(preds) == 12
    for p in preds:
        assert not p.game.completed and p.game.game_date >= TODAY
        assert p.pick == (p.game.home_team if p.home_prob >= 0.5 else p.game.away_team)
        assert p.market_home_prob is not None
        assert p.combined_home_prob is None and p.bet_side is None  # no backtest yet, so no bets


def test_picks_are_graded_once_games_finish(season, monkeypatch):
    jobs.make_predictions()
    finish_games(season, TODAY, monkeypatch)
    assert jobs.grade_predictions() == 6
    graded = Prediction.query.filter_by(graded=True).all()
    assert len(graded) == 6
    for p in graded:
        assert p.correct == (p.pick == p.game.home_team)   # every home team won 112-104
        assert p.profit is None   # no bets without a backtest
    assert jobs.grade_predictions() == 0   # nothing graded twice


def test_backtest_finds_the_signal_in_synthetic_data_and_is_saved(app, client, monkeypatch):
    # A bigger synthetic season than the shared fixture, so the result isn't noise.
    today = date(2026, 5, 29)   # season runs Jan 1 - May 30
    by_day = synthetic_season(date(2026, 1, 1), days=150, today=today, games_per_day=12)
    monkeypatch.setattr(jobs, "today_et", lambda: today)
    monkeypatch.setattr(jobs, "utc_now", lambda: datetime(2026, 5, 29, 16, 0))
    jobs.sync_games(fetch=fake_fetch(by_day), pause=0)

    metrics = jobs.run_backtest()
    assert metrics["games"] > 1000
    # Team strength drives these results, so a correct pipeline must beat a coin flip
    # in both picks and probabilities, and weight team strength positively.
    assert metrics["model"]["accuracy"] > 0.58
    assert metrics["model"]["log_loss"] < 0.68
    coefs = metrics["coefficients"]
    assert coefs["elo_diff"] + coefs["form_diff"] + coefs["season_margin_diff"] > 0
    assert metrics["games_with_odds"] == metrics["games"]
    assert [b["min_ev"] for b in metrics["betting"]] == list(model.BET_THRESHOLDS)
    assert ModelRun.query.one().metrics["games"] == metrics["games"]
    # These synthetic lines are built from the true probabilities, so the blend should
    # lean on the market far more than on the noisier model.
    blend = metrics["blend"]
    assert blend["market_weight"] > 0.5 > abs(blend["model_weight"])
    combined = metrics["vs_market"]["combined"]["log_loss"]
    assert combined < metrics["vs_market"]["model"]["log_loss"]

    # Live picks use the saved blend for bets.
    assert jobs.make_predictions() == 24
    for p in Prediction.query.all():
        assert p.combined_home_prob is not None
        if p.bet_side:
            prob = p.combined_home_prob if p.bet_side == "home" else 1 - p.combined_home_prob
            assert p.bet_ev == pytest.approx(expected_value(prob, p.bet_odds))
            assert p.bet_ev >= model.MIN_EV

    html = client.get("/performance").get_data(as_text=True)
    assert "Model + market combined" in html and "(the site's rule)" in html


def test_backtest_only_trains_on_earlier_days(season, monkeypatch):
    trained_through, predicted = [], []
    real_fit, real_predict = model.fit, model.predict

    def spy_fit(rows):
        trained_through.append(max(r["game_date"] for r in rows))
        return real_fit(rows)

    def spy_predict(clf, rows):
        predicted.append({r["game_date"] for r in rows})
        return real_predict(clf, rows)

    monkeypatch.setattr(model, "fit", spy_fit)
    monkeypatch.setattr(model, "predict", spy_predict)
    jobs.run_backtest()
    assert predicted
    for last_train_day, days in zip(trained_through, predicted):
        assert all(last_train_day < d for d in days)


def test_value_bet_guardrails():
    weights = {"market_weight": 1.0, "model_weight": 0.3, "intercept": 0.0}
    # Combined estimate sees value on the underdog and the model agrees: bet.
    assert model.value_bet(0.45, 0.45, -200, 170, weights)[0] == "away"
    # The blend gives the model no real weight: never bet.
    assert model.value_bet(0.45, 0.45, -200, 170, {**weights, "model_weight": -0.2}) is None
    assert model.value_bet(0.45, 0.45, -200, 170, {**weights, "model_weight": 0.004}) is None
    assert model.value_bet(0.45, 0.45, -200, 170, None) is None
    # Combined estimate likes the underdog but the model is MORE bullish on the favorite
    # than the market (0.70 > 0.64): that's a quirk of the blend, not model information.
    assert model.value_bet(0.70, 0.45, -200, 170, weights) is None


def test_choose_bet_rules():
    assert model.choose_bet(0.6, None, None) is None
    assert model.choose_bet(0.5, -110, -110) is None              # no edge after the vig
    side, odds, ev = model.choose_bet(0.45, -200, 170)            # model likes the underdog
    assert (side, odds) == ("away", 170) and ev > model.MIN_EV
    assert model.choose_bet(0.6, -700, 500) is None               # away is a longshot, home has no edge
