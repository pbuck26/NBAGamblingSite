from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from patSite.pipeline import features


def game(i, day, home, away, home_score=None, away_score=None, season=2026, neutral=False, state=None):
    completed = home_score is not None
    return SimpleNamespace(
        id=str(i), season=season, start_time=datetime(day.year, day.month, day.day, 23, 0),
        game_date=day, home_team=home, away_team=away, neutral_site=neutral,
        state=state or ("post" if completed else "pre"), completed=completed,
        home_score=home_score, away_score=away_score, home_ml=None, away_ml=None)


D = date(2026, 1, 5)


def test_features_never_use_the_games_own_or_later_results():
    games = [game(i, D + timedelta(days=i), "Miami Heat", "Orlando Magic", 100 + i, 95) for i in range(6)]
    before = features.compute(games)
    games[3].home_score = 60          # change one result
    after = features.compute(games)
    def feats(row):
        return {k: v for k, v in row.items() if k != "label"}
    # That game's features, and every earlier game's, are unchanged; only its label is.
    assert before[:3] == after[:3]
    assert feats(before[3]) == feats(after[3]) and before[3]["label"] != after[3]["label"]
    assert feats(before[4]) != feats(after[4])  # later games do see the result


def test_back_to_backs_and_rest_including_tomorrows_scheduled_game():
    games = [
        game(1, D, "Miami Heat", "Orlando Magic", 100, 90),
        game(2, D + timedelta(days=1), "Boston Celtics", "Miami Heat"),       # scheduled, MIA on a b2b
        game(3, D + timedelta(days=2), "Miami Heat", "Chicago Bulls"),        # MIA again; CHI first game
    ]
    rows = features.compute(games)
    assert rows[1]["away_b2b"] == 1 and rows[1]["home_b2b"] == 0
    assert rows[2]["home_b2b"] == 1
    assert rows[2]["rest_diff"] == 1 - features.REST_CAP


def test_neutral_site_removes_home_edge():
    rows = features.compute([game(1, D, "Miami Heat", "Orlando Magic", neutral=True),
                             game(2, D, "Boston Celtics", "Chicago Bulls")])
    neutral, home = rows
    assert neutral["home_court"] == 0 and neutral["elo_prob"] == pytest.approx(0.5)
    assert home["home_court"] == 1 and home["elo_prob"] > 0.6


def test_elo_regresses_toward_average_at_new_season():
    played = [game(i, D + timedelta(days=i), "Miami Heat", "Orlando Magic", 120, 90) for i in range(10)]
    same_season = played + [game(98, D + timedelta(days=20), "Miami Heat", "Orlando Magic")]
    next_season = played + [game(99, date(2026, 10, 25), "Miami Heat", "Orlando Magic", season=2027),
                            game(100, date(2026, 10, 26), "Boston Celtics", "Chicago Bulls", season=2027)]
    gap_end_of_season = features.compute(same_season)[-1]["elo_diff"] * 100 - features.ELO_HOME_EDGE
    rows = features.compute(next_season)
    gap_new_season = rows[10]["elo_diff"] * 100 - features.ELO_HOME_EDGE
    assert gap_end_of_season > 100
    assert gap_new_season == pytest.approx(features.ELO_SEASON_CARRY * gap_end_of_season)
    assert rows[10]["form_diff"] == 0 and rows[10]["season_margin_diff"] == 0
    # Elo is zero-sum: teams that haven't played are still even.
    assert rows[11]["elo_diff"] * 100 == pytest.approx(features.ELO_HOME_EDGE)


def test_min_games_counts_history_for_burn_in():
    games = [game(i, D + timedelta(days=i), "Miami Heat", "Orlando Magic", 100, 90) for i in range(3)]
    games.append(game(9, D + timedelta(days=5), "Miami Heat", "Chicago Bulls"))
    rows = features.compute(games)
    assert [r["min_games"] for r in rows] == [0, 1, 2, 0]
    assert rows[0]["label"] == 1 and rows[3]["label"] is None
