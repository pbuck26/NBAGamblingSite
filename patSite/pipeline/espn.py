"""Scores, schedule and moneylines from ESPN's public scoreboard feed.

The feed is unofficial and undocumented, so parsing is defensive: anything
unexpected is skipped and logged rather than guessed at.
"""
import logging
import sys
from datetime import date, datetime, timezone

import requests

from patSite.clock import ET
from patSite.pipeline.odds import parse_american
from patSite.teams import canonical_team

log = logging.getLogger(__name__)

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
PRESEASON = 1


def fetch_scoreboard(day, session=None):
    http = session or requests
    resp = http.get(SCOREBOARD_URL, params={"dates": day.strftime("%Y%m%d")}, timeout=30,
                    headers={"User-Agent": "nbagamblingsite/1.0"})
    resp.raise_for_status()
    return resp.json()


def parse_scoreboard(data):
    games = []
    for event in data.get("events") or []:
        try:
            game = parse_event(event)
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("Skipping unparseable event %s: %r", event.get("id"), exc)
            continue
        if game:
            games.append(game)
    return games


def parse_event(event):
    comp = (event.get("competitions") or [{}])[0]
    sides = {c.get("homeAway"): c for c in comp.get("competitors") or []}
    if "home" not in sides or "away" not in sides:
        return None
    home_name = sides["home"]["team"].get("displayName", "")
    away_name = sides["away"]["team"].get("displayName", "")
    home_team, away_team = canonical_team(home_name), canonical_team(away_name)
    if not home_team or not away_team:
        log.info("Skipping non-NBA matchup %s vs %s", away_name, home_name)
        return None

    season = event.get("season") or {}
    if season.get("type") == PRESEASON:
        return None

    start = _parse_time(event.get("date") or comp["date"])
    status = ((comp.get("status") or event.get("status") or {}).get("type")) or {}
    completed = bool(status.get("completed"))
    home_ml, away_ml = parse_moneylines(comp.get("odds") or [])
    return {
        "id": str(event["id"]),
        "season": int(season.get("year") or _season_for(start)),
        "season_type": season.get("type"),
        "start_time": start.replace(tzinfo=None),
        "game_date": start.astimezone(ET).date(),
        "home_team": home_team,
        "away_team": away_team,
        "neutral_site": bool(comp.get("neutralSite")),
        "state": status.get("state") or "pre",
        "completed": completed,
        "home_score": _score(sides["home"]) if completed else None,
        "away_score": _score(sides["away"]) if completed else None,
        "home_ml": home_ml,
        "away_ml": away_ml,
    }


def parse_moneylines(odds_list):
    """(home, away) American moneylines from the first provider that has both, else (None, None)."""
    for odds in odds_list:
        moneyline = odds.get("moneyline") or {}
        home, away = _latest_line(moneyline.get("home")), _latest_line(moneyline.get("away"))
        if home is None or away is None:
            home = parse_american((odds.get("homeTeamOdds") or {}).get("moneyLine"))
            away = parse_american((odds.get("awayTeamOdds") or {}).get("moneyLine"))
        if home is not None and away is not None:
            return home, away
    return None, None


def _latest_line(side):
    if not side:
        return None
    for key in ("close", "current", "open"):
        odds = parse_american((side.get(key) or {}).get("odds"))
        if odds is not None:
            return odds
    return None


def _score(competitor):
    score = competitor.get("score")
    if isinstance(score, dict):
        score = score.get("value")
    return int(float(score))


def _parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def _season_for(start):
    # ESPN names seasons by the year they end: games from August on belong to next year's season.
    return start.year + 1 if start.month >= 8 else start.year


if __name__ == "__main__":
    # Debug helper: python -m patSite.pipeline.espn 2026-01-15
    logging.basicConfig(level=logging.INFO)
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    for g in parse_scoreboard(fetch_scoreboard(day)):
        print(g)
