from datetime import date, datetime

from patSite.pipeline.espn import parse_moneylines, parse_scoreboard
from tests.factories import espn_event


def test_parses_final_game_with_eastern_date_and_team_alias():
    event = espn_event(401, datetime(2026, 1, 16, 0, 30), "LA Clippers", "Boston Celtics",
                       completed=True, home_score=101, away_score=99, home_ml=-150, away_ml=130)
    [game] = parse_scoreboard({"events": [event]})
    assert game["id"] == "401"
    assert game["game_date"] == date(2026, 1, 15)      # 7:30 PM ET on the 15th
    assert game["start_time"] == datetime(2026, 1, 16, 0, 30)
    assert game["home_team"] == "Los Angeles Clippers"
    assert (game["home_score"], game["away_score"]) == (101, 99)
    assert (game["home_ml"], game["away_ml"]) == (-150, 130)
    assert game["completed"] and game["state"] == "post"
    assert game["season"] == 2026


def test_scheduled_game_has_no_scores():
    event = espn_event(402, datetime(2026, 10, 28, 23, 0), "Miami Heat", "Orlando Magic", season=2027)
    [game] = parse_scoreboard({"events": [event]})
    assert game["home_score"] is None and not game["completed"] and game["state"] == "pre"
    assert (game["home_ml"], game["away_ml"]) == (None, None)


def test_skips_preseason_all_star_and_garbage():
    events = [
        espn_event(1, datetime(2026, 10, 10, 23, 0), "Miami Heat", "Orlando Magic", season_type=1),
        espn_event(2, datetime(2026, 2, 16, 1, 0), "Team USA", "Team World"),
        {"id": "3", "competitions": [{"competitors": []}]},
        {"id": "4", "date": "not a date", "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"displayName": "Miami Heat"}},
            {"homeAway": "away", "team": {"displayName": "Orlando Magic"}}]}]},
    ]
    assert parse_scoreboard({"events": events}) == []
    assert parse_scoreboard({}) == []


def test_moneylines_from_older_odds_shape_and_even():
    assert parse_moneylines([{"homeTeamOdds": {"moneyLine": -120}, "awayTeamOdds": {"moneyLine": 100}}]) == (-120, 100)
    assert parse_moneylines([{"moneyline": {"home": {"open": {"odds": "EVEN"}},
                                            "away": {"close": {"odds": "-120"}}}}]) == (100, -120)
    assert parse_moneylines([{"details": "BOS -5.5"}]) == (None, None)
