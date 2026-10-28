"""Live track record from graded picks. Pure Python so the web app stays light."""
from statistics import mean

FEATURE_LABELS = {
    "home_court": "Home court (adjusts the home bonus already in the Elo gap)",
    "elo_diff": "Elo rating gap (per 100 pts)",
    "form_diff": "Last-10-games margin gap (per 10 pts)",
    "season_margin_diff": "Season scoring margin gap (per 10 pts)",
    "rest_diff": "Extra rest days",
    "home_b2b": "Home team on a back-to-back",
    "away_b2b": "Away team on a back-to-back",
}


def track_record(graded):
    """Summary of graded predictions (each with .game loaded), or None if there are none."""
    if not graded:
        return None
    correct = sum(1 for p in graded if p.correct)
    bets = [p for p in graded if p.bet_side]
    units = sum(p.profit for p in bets)
    priced = [p for p in graded if p.market_home_prob is not None]

    def home_won(p):
        return 1.0 if p.game.home_score > p.game.away_score else 0.0

    return {
        "since": min(p.game.game_date for p in graded),
        "picks": len(graded),
        "correct": correct,
        "accuracy": correct / len(graded),
        "bets": len(bets),
        "bet_wins": sum(1 for p in bets if p.profit > 0),
        "units": units,
        "roi": units / len(bets) if bets else None,
        "priced": len(priced),
        "brier_model": mean((p.home_prob - home_won(p)) ** 2 for p in priced) if priced else None,
        "brier_market": mean((p.market_home_prob - home_won(p)) ** 2 for p in priced) if priced else None,
    }
