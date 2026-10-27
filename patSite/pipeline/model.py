"""Win-probability model, market blend, betting rule and walk-forward backtest.

Two stages:
1. A logistic regression on pre-game features predicts the home team's chance.
2. A second logistic regression combines that prediction with the betting market's
   no-vig probability, fitted on earlier out-of-sample predictions. Its weights say how
   much the model adds beyond the market. Bets are chosen from this combined estimate,
   so a model that is merely less sharp than the market doesn't generate fake "value".
"""
import math
from statistics import mean

import numpy as np
from sklearn.linear_model import LogisticRegression

from patSite.pipeline.odds import expected_value, no_vig_probability, profit

FEATURES = ("home_court", "elo_diff", "form_diff", "season_margin_diff",
            "rest_diff", "home_b2b", "away_b2b")
MIN_TEAM_GAMES = 10     # skip games until both teams have this much history
MIN_TRAIN_GAMES = 200   # don't fit a model on fewer games than this
MIN_BLEND_GAMES = 150   # out-of-sample predictions with odds needed before betting
MIN_MODEL_WEIGHT = 0.1  # the model's weight in the blend must be at least this to bet at all
MIN_EV = 0.03           # flag a bet only if expected return at the posted odds is +3% or better
MAX_ODDS = 400          # skip longshots, where small errors swamp the edge
BET_THRESHOLDS = (0.0, MIN_EV, 0.06)
CALIBRATION_BUCKETS = ((0.5, 0.55), (0.55, 0.6), (0.6, 0.65), (0.65, 0.7), (0.7, 0.8), (0.8, 1.01))


def eligible(row):
    return row["min_games"] >= MIN_TEAM_GAMES


def has_odds(row):
    return row["home_ml"] is not None and row["away_ml"] is not None


def _matrix(rows):
    return np.array([[row[f] for f in FEATURES] for row in rows], dtype=float)


def fit(rows):
    # home_court acts as the intercept, so neutral-site games get no home edge.
    clf = LogisticRegression(C=1.0, fit_intercept=False, max_iter=1000)
    return clf.fit(_matrix(rows), np.array([row["label"] for row in rows]))


def predict(clf, rows):
    return clf.predict_proba(_matrix(rows))[:, 1].tolist()


def coefficients(clf):
    return {name: round(float(c), 4) for name, c in zip(FEATURES, clf.coef_[0])}


def _logit(p):
    p = min(max(p, 0.01), 0.99)
    return math.log(p / (1 - p))


def fit_blend(results):
    """Weights for combining market and model, from out-of-sample results with odds."""
    X = [[_logit(no_vig_probability(r["home_ml"], r["away_ml"])), _logit(r["prob"])] for r in results]
    clf = LogisticRegression(C=1.0, max_iter=1000).fit(np.array(X), np.array([r["label"] for r in results]))
    return {"market_weight": float(clf.coef_[0][0]), "model_weight": float(clf.coef_[0][1]),
            "intercept": float(clf.intercept_[0]), "games": len(results)}


def blend(weights, model_prob, home_ml, away_ml):
    """Combined home win probability."""
    z = (weights["intercept"]
         + weights["market_weight"] * _logit(no_vig_probability(home_ml, away_ml))
         + weights["model_weight"] * _logit(model_prob))
    return 1 / (1 + math.exp(-z))


def choose_bet(home_prob, home_ml, away_ml, min_ev=MIN_EV):
    """(side, odds, ev) for the side worth betting at these odds, or None."""
    if home_ml is None or away_ml is None:
        return None
    best = None
    for side, prob, odds in (("home", home_prob, home_ml), ("away", 1 - home_prob, away_ml)):
        if odds > MAX_ODDS:
            continue
        ev = expected_value(prob, odds)
        if ev >= min_ev and (best is None or ev > best[2]):
            best = (side, odds, ev)
    return best


def value_bet(model_prob, combined_prob, home_ml, away_ml, weights, min_ev=MIN_EV):
    """The bet to flag, if any: (side, odds, ev). Two guardrails keep the blend from
    betting on quirks of the market line rather than on the model's information:
    the model must carry real weight in the blend, and the model itself must favor the
    bet side more than the market does."""
    if not weights or weights["model_weight"] < MIN_MODEL_WEIGHT or combined_prob is None:
        return None
    bet = choose_bet(combined_prob, home_ml, away_ml, min_ev)
    if not bet:
        return None
    market = no_vig_probability(home_ml, away_ml)
    model_edge = model_prob - market if bet[0] == "home" else market - model_prob
    return bet if model_edge > 0 else None


def backtest(rows):
    """Predict each day's games using only earlier days, then score the predictions.

    rows: completed, eligible feature rows. Both the model and the market blend are refit
    every day on earlier games only. Bets are settled at the latest line in the data
    (usually the closing line), the hardest price to beat.
    """
    rows = sorted(rows, key=lambda r: r["game_date"])
    results = []
    for day in sorted({r["game_date"] for r in rows}):
        train = [r for r in rows if r["game_date"] < day]
        if len(train) < MIN_TRAIN_GAMES:
            continue
        priced_history = [r for r in results if has_odds(r)]
        weights = fit_blend(priced_history) if len(priced_history) >= MIN_BLEND_GAMES else None
        todays = [r for r in rows if r["game_date"] == day]
        for row, prob in zip(todays, predict(fit(train), todays)):
            result = {**row, "prob": prob}
            if weights and has_odds(row):
                result["combined_prob"] = blend(weights, prob, row["home_ml"], row["away_ml"])
                result["weights"] = weights
            results.append(result)

    summary = summarize(results)
    priced = [r for r in results if has_odds(r)]
    if len(priced) >= MIN_BLEND_GAMES:
        summary["blend"] = fit_blend(priced)
    return summary


def _log_loss(probs, labels):
    return mean(-math.log(min(max(p if y else 1 - p, 1e-6), 1.0)) for p, y in zip(probs, labels))


def _brier(probs, labels):
    return mean((p - y) ** 2 for p, y in zip(probs, labels))


def _accuracy(probs, labels):
    return mean(int((p >= 0.5) == bool(y)) for p, y in zip(probs, labels))


def _scores(probs, labels):
    return {"accuracy": _accuracy(probs, labels), "log_loss": _log_loss(probs, labels),
            "brier": _brier(probs, labels)}


def summarize(results):
    if not results:
        return {"games": 0}
    labels = [r["label"] for r in results]
    model_probs = [r["prob"] for r in results]
    summary = {
        "start": results[0]["game_date"].isoformat(),
        "end": results[-1]["game_date"].isoformat(),
        "games": len(results),
        "home_win_rate": mean(labels),
        "model": _scores(model_probs, labels),
        "elo_only": _scores([r["elo_prob"] for r in results], labels),
        "games_with_odds": sum(1 for r in results if has_odds(r)),
    }

    # Compare against the market on games where every estimate exists.
    combined = [r for r in results if "combined_prob" in r]
    if combined:
        y = [r["label"] for r in combined]
        summary["vs_market"] = {
            "games": len(combined),
            "model": _scores([r["prob"] for r in combined], y),
            "market": _scores([no_vig_probability(r["home_ml"], r["away_ml"]) for r in combined], y),
            "combined": _scores([r["combined_prob"] for r in combined], y),
        }
        summary["betting"] = [_betting(combined, t) for t in BET_THRESHOLDS]

    summary["calibration"] = []
    for low, high in CALIBRATION_BUCKETS:
        bucket = [(max(p, 1 - p), int((p >= 0.5) == bool(y))) for p, y in zip(model_probs, labels)
                  if low <= max(p, 1 - p) < high]
        if bucket:
            summary["calibration"].append({
                "range": f"{round(low * 100)}–{min(round(high * 100), 100)}%",
                "games": len(bucket),
                "predicted": mean(b[0] for b in bucket),
                "actual": mean(b[1] for b in bucket),
            })
    return summary


def _betting(results, min_ev):
    bets = []
    for r in results:
        bet = value_bet(r["prob"], r["combined_prob"], r["home_ml"], r["away_ml"], r["weights"], min_ev)
        if bet:
            side, odds, _ = bet
            bets.append(profit(odds, (side == "home") == bool(r["label"])))
    units = sum(bets)
    return {"min_ev": min_ev, "bets": len(bets), "wins": sum(1 for b in bets if b > 0),
            "units": units, "roi": units / len(bets) if bets else None}


def format_report(metrics):
    """Plain-text/markdown summary for the CLI and GitHub Actions job summary."""
    if not metrics.get("games"):
        return "Not enough games since the data start date to backtest yet."
    lines = [
        f"### Walk-forward backtest: {metrics['start']} to {metrics['end']}",
        f"{metrics['games']} games ({metrics['games_with_odds']} with moneylines); "
        f"home teams won {metrics['home_win_rate']:.1%}.",
        "",
        "| | Accuracy | Log loss | Brier |",
        "|---|---|---|---|",
    ]
    for name, key in (("Model", "model"), ("Elo only", "elo_only")):
        s = metrics[key]
        lines.append(f"| {name} | {s['accuracy']:.1%} | {s['log_loss']:.4f} | {s['brier']:.4f} |")
    if metrics.get("vs_market"):
        vm = metrics["vs_market"]
        lines += ["", f"**Against the betting market** ({vm['games']} games; lower log loss is better)", "",
                  "| | Accuracy | Log loss | Brier |", "|---|---|---|---|"]
        for name, key in (("Model", "model"), ("Market (no-vig)", "market"), ("Combined", "combined")):
            s = vm[key]
            lines.append(f"| {name} | {s['accuracy']:.1%} | {s['log_loss']:.4f} | {s['brier']:.4f} |")
        lines += ["", "| Bet when EV ≥ | Bets | Won | Units | ROI |", "|---|---|---|---|---|"]
        for b in metrics["betting"]:
            roi = f"{b['roi']:+.1%}" if b["roi"] is not None else "–"
            lines.append(f"| {b['min_ev']:+.0%} | {b['bets']} | {b['wins']} | {b['units']:+.2f} | {roi} |")
    else:
        lines += ["", f"Not enough games with moneylines (need {MIN_BLEND_GAMES}) to compare with the market."]
    if metrics.get("blend"):
        b = metrics["blend"]
        lines += ["", f"Blend weights: market {b['market_weight']:+.3f}, model {b['model_weight']:+.3f}, "
                      f"intercept {b['intercept']:+.3f} ({b['games']} games)"]
    if metrics.get("coefficients"):
        lines += ["", "Model coefficients: " + ", ".join(f"{k}={v:+.3f}" for k, v in metrics["coefficients"].items())]
    return "\n".join(lines)
