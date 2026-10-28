from datetime import date
from os import environ, path
from dotenv import load_dotenv

basedir = path.abspath(path.dirname(__file__))
# `neon env pull` writes .env.local (or .env if it exists). The first file loaded
# wins, and real environment variables beat both.
load_dotenv(path.join(basedir, '.env.local'))
load_dotenv(path.join(basedir, '.env'))


def normalize_url(url):
    # Heroku-style "postgres://" URLs are rejected by SQLAlchemy 1.4+.
    if url and url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return url or None


def database_url():
    url = environ.get('DATABASE_URL') or environ.get('SQLALCHEMY_DATABASE_URI')
    return normalize_url(url) or 'sqlite:///' + path.join(basedir, 'nba.db')


class Config:
    DEBUG = environ.get('FLASK_DEBUG') == '1'
    SECRET_KEY = environ.get('SECRET_KEY')
    # On Neon, DATABASE_URL is the pooled connection (app traffic) and
    # DATABASE_URL_UNPOOLED the direct one, which schema changes should use.
    SQLALCHEMY_DATABASE_URI = database_url()
    SCHEMA_DATABASE_URI = normalize_url(environ.get('DATABASE_URL_UNPOOLED'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Free Postgres hosts (e.g. Neon) drop idle connections; check before use.
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = environ.get('SESSION_COOKIE_SECURE') == '1'
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    # The model trains and is evaluated only on games from this date on.
    DATA_START_DATE = date.fromisoformat(environ.get('DATA_START_DATE', '2026-01-01'))
