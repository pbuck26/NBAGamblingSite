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
