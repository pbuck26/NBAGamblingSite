from datetime import date, datetime

import pytest

from patSite import create_app, db
from patSite.Models import Users


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    u = Users("pat@example.com", "correct-horse", "Pat")
    db.session.add(u)
    db.session.commit()
    return u


def log_in(client, email="pat@example.com", password="correct-horse", next_page=None):
    url = "/login" + (f"?next={next_page}" if next_page else "")
    return client.post(url, data={"email": email, "password": password})


TODAY = date(2026, 3, 20)


@pytest.fixture
def season(app, monkeypatch):
    """A synthetic season synced into the database: Jan 1 - Mar 21, 2026, with
    games before TODAY final and TODAY/tomorrow scheduled."""
    from patSite.pipeline import jobs
    from tests.factories import espn_event, fake_fetch, synthetic_season

    by_day = synthetic_season(date(2026, 1, 1), days=80, today=TODAY)
    # ESPN can list a late-night Dec 31 game on Jan 1's scoreboard; it must be dropped.
    by_day[date(2026, 1, 1)].append(espn_event(1, datetime(2026, 1, 1, 3, 0), "Miami Heat",
                                               "Orlando Magic", True, 100, 90, -150, 130))
    monkeypatch.setattr(jobs, "today_et", lambda: TODAY)
    monkeypatch.setattr(jobs, "utc_now", lambda: datetime(2026, 3, 20, 16, 0))
    jobs.sync_games(fetch=fake_fetch(by_day), pause=0)
    return by_day


def finish_games(by_day, day, monkeypatch, home_score=112, away_score=104):
    """Re-sync `day` with every game final (home team wins), as of the next morning."""
    from datetime import timedelta
    from patSite.pipeline import jobs
    from tests.factories import espn_event, fake_fetch

    finals = []
    for event in by_day[day]:
        home, away = event["competitions"][0]["competitors"]
        finals.append(espn_event(event["id"], datetime.fromisoformat(event["date"][:-1]),
                                 home["team"]["displayName"], away["team"]["displayName"],
                                 True, home_score, away_score))
    monkeypatch.setattr(jobs, "today_et", lambda: day + timedelta(days=1))
    jobs.sync_games(start=day, end=day, fetch=fake_fetch({day: finals}), pause=0)
