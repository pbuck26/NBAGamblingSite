"""Test-only data: ESPN-shaped events and synthetic seasons. Never used as real results."""
import random
from datetime import datetime, timedelta, timezone

from patSite.teams import TEAMS


def espn_event(event_id, start_utc, home, away, completed=False, home_score=None, away_score=None,
               home_ml=None, away_ml=None, season=2026, season_type=2, neutral=False, state=None):
    def fmt(odds):
        return f"+{odds}" if odds > 0 else str(odds)

    odds = []
    if home_ml is not None:
        odds = [{"provider": {"name": "Test"},
                 "moneyline": {"home": {"close": {"odds": fmt(home_ml)}},
                               "away": {"close": {"odds": fmt(away_ml)}}}}]
    return {
        "id": str(event_id),
        "date": start_utc.strftime("%Y-%m-%dT%H:%MZ"),
        "season": {"year": season, "type": season_type},
        "competitions": [{
            "neutralSite": neutral,
            "competitors": [
                {"homeAway": "home", "team": {"displayName": home},
                 "score": str(home_score if home_score is not None else 0)},
                {"homeAway": "away", "team": {"displayName": away},
                 "score": str(away_score if away_score is not None else 0)},
            ],
            "status": {"type": {"state": state or ("post" if completed else "pre"),
                                "completed": completed}},
            "odds": odds,
        }],
    }


def synthetic_season(start, days, today, seed=7, games_per_day=6):
    """ESPN events keyed by ET date. Team strength drives results, games before
    `today` are final, the rest are scheduled; every game has a fair-ish moneyline."""
    rng = random.Random(seed)
    teams = sorted(TEAMS)
    strength = {t: rng.gauss(0, 6) for t in teams}
    by_day, event_id = {}, 1000
    for offset in range(days):
        day = start + timedelta(days=offset)
        rng.shuffle(teams)
        events = []
        for i in range(games_per_day):
            home, away = teams[2 * i], teams[2 * i + 1]
            # 7:30 PM ET is 00:30 UTC the next day (winter, UTC-5).
            start_utc = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(hours=24, minutes=30)
            expected = strength[home] - strength[away] + 3
            win_prob = 1 / (1 + 10 ** (-expected / 12))
            home_ml, away_ml = _moneylines(win_prob)
            event_id += 1
            if day < today:
                margin = round(expected + rng.gauss(0, 12)) or 1
                home_score = 110 + max(margin, 0)
                away_score = 110 + max(-margin, 0)
                events.append(espn_event(event_id, start_utc, home, away, True, home_score, away_score,
                                         home_ml, away_ml))
            else:
                events.append(espn_event(event_id, start_utc, home, away, home_ml=home_ml, away_ml=away_ml))
        by_day[day] = events
    return by_day


def _moneylines(home_prob, vig=0.022):
    def to_american(p):
        p = min(max(p + vig, 0.02), 0.98)
        return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)
    return to_american(home_prob), to_american(1 - home_prob)


def fake_fetch(by_day):
    def fetch(day, session=None):
        return {"events": by_day.get(day, [])}
    return fetch
