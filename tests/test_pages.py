from datetime import date

from patSite import routes
from patSite.pipeline import jobs
from tests.conftest import TODAY, finish_games


def test_homepage_without_picks(client):
    html = client.get("/").get_data(as_text=True)
    assert "No picks posted yet" in html


def test_homepage_shows_todays_slate(client, season, monkeypatch):
    jobs.make_predictions()
    monkeypatch.setattr(routes, "today_et", lambda: TODAY)
    html = client.get("/").get_data(as_text=True)
    assert "Today's picks" in html and "Friday, March 20, 2026" in html
    away = season[TODAY][0]["competitions"][0]["competitors"][1]["team"]["displayName"]
    assert away in html
    assert "8:30 PM" in html          # 00:30 UTC during daylight saving time
    assert html.count("<tr>") == 1 + 6  # header + today's six games, not tomorrow's


def test_homepage_falls_forward_to_next_slate(client, season, monkeypatch):
    jobs.make_predictions()
    monkeypatch.setattr(routes, "today_et", lambda: date(2026, 3, 19))
    html = client.get("/").get_data(as_text=True)
    assert "Next picks" in html and "March 20" in html


def test_performance_page_empty(client):
    html = client.get("/performance").get_data(as_text=True)
    assert "No graded picks yet" in html
    assert "backtest runs once" in html


def test_performance_page_with_record_and_backtest(client, season, monkeypatch):
    jobs.make_predictions()
    finish_games(season, TODAY, monkeypatch)
    jobs.grade_predictions()
    jobs.run_backtest()
    html = client.get("/performance").get_data(as_text=True)
    assert "Picks correct" in html and "Units won" in html
    assert "Most recent 6 graded picks" in html
    assert "Walk-forward test on" in html
    assert "Not enough games with moneylines yet" in html   # under MIN_BLEND_GAMES
    assert "Elo rating gap" in html
