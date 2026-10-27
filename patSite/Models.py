import hashlib
import hmac
from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime as dt
from patSite.clock import to_et

# Accounts created before 2026 were hashed with Werkzeug's old single-round
# "sha256" method, which current Werkzeug no longer accepts.
LEGACY_HASH_PREFIX = 'sha256$'

class Users(UserMixin, db.Model):
    __tablename__='users'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(200), unique=True, nullable=False)
    password   = db.Column(db.String(200), nullable=False)
    created_on = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    messages   = db.relationship('ContactMessages', backref='users', lazy=True)

    def __init__(self, email, password, name):
        self.email      = email
        self.name       = name
        self.created_on = dt.now()
        self.last_login = dt.now()
        self.set_password(password)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Verify a password. A matching legacy hash is upgraded to the
        current algorithm; the caller is responsible for committing."""
        if self.password.startswith(LEGACY_HASH_PREFIX):
            _, salt, expected = self.password.split('$', 2)
            actual = hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(actual, expected):
                return False
            self.set_password(password)
            return True
        return check_password_hash(self.password, password)

    def __repr__(self):
        return '<User {}>'.format(self.id)

class Game(db.Model):
    """One NBA game, as reported by ESPN. Times are naive UTC."""
    __tablename__='games'
    id           = db.Column(db.String(32), primary_key=True)  # ESPN event id
    season       = db.Column(db.Integer, nullable=False)       # ESPN season year: 2026 = the 2025-26 season
    season_type  = db.Column(db.Integer, nullable=True)        # 2 = regular season, 3 = playoffs
    start_time   = db.Column(db.DateTime, nullable=False)
    game_date    = db.Column(db.Date, nullable=False, index=True)  # US Eastern date
    home_team    = db.Column(db.String(64), nullable=False)
    away_team    = db.Column(db.String(64), nullable=False)
    neutral_site = db.Column(db.Boolean, nullable=False, default=False)
    state        = db.Column(db.String(8), nullable=False, default='pre')  # pre / in / post
    completed    = db.Column(db.Boolean, nullable=False, default=False)
    home_score   = db.Column(db.Integer, nullable=True)
    away_score   = db.Column(db.Integer, nullable=True)
    home_ml      = db.Column(db.Integer, nullable=True)  # latest American moneyline seen
    away_ml      = db.Column(db.Integer, nullable=True)
    prediction   = db.relationship('Prediction', back_populates='game', uselist=False)

    @property
    def winner(self):
        if not self.completed:
            return None
        return self.home_team if self.home_score > self.away_score else self.away_team

    @property
    def start_time_et(self):
        return to_et(self.start_time)


class Prediction(db.Model):
    """The model's pick for a game. Updated until tip-off, then graded once final."""
    __tablename__='predictions'
    id               = db.Column(db.Integer, primary_key=True)
    game_id          = db.Column(db.String(32), db.ForeignKey('games.id'), unique=True, nullable=False)
    updated_at       = db.Column(db.DateTime, nullable=False)
    home_prob        = db.Column(db.Float, nullable=False)
    home_ml          = db.Column(db.Integer, nullable=True)  # odds when the pick was last updated
    away_ml          = db.Column(db.Integer, nullable=True)
    market_home_prob = db.Column(db.Float, nullable=True)    # implied by those odds, vig removed
    combined_home_prob = db.Column(db.Float, nullable=True)  # model + market blend; bets use this
    pick             = db.Column(db.String(64), nullable=False)
    bet_side         = db.Column(db.String(4), nullable=True)  # 'home', 'away', or None for no bet
    bet_odds         = db.Column(db.Integer, nullable=True)
    bet_ev           = db.Column(db.Float, nullable=True)      # expected profit per 1 unit staked
    graded           = db.Column(db.Boolean, nullable=False, default=False)
    correct          = db.Column(db.Boolean, nullable=True)
    profit           = db.Column(db.Float, nullable=True)      # units won or lost on the bet
    game             = db.relationship('Game', back_populates='prediction')

    @property
    def pick_prob(self):
        return self.home_prob if self.pick == self.game.home_team else 1 - self.home_prob

    @property
    def market_pick_prob(self):
        if self.market_home_prob is None:
            return None
        return self.market_home_prob if self.pick == self.game.home_team else 1 - self.market_home_prob

    @property
    def bet_team(self):
        if self.bet_side is None:
            return None
        return self.game.home_team if self.bet_side == 'home' else self.game.away_team


class ModelRun(db.Model):
    """Walk-forward backtest results and coefficients from a daily model run."""
    __tablename__='model_runs'
    id         = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False)
    metrics    = db.Column(db.JSON, nullable=False)


class ContactMessages(db.Model):
    __tablename__='contactmessages'
    id          = db.Column(db.Integer, primary_key=True)
    subject     = db.Column(db.Text, nullable=False)
    message     = db.Column(db.Text, nullable=False)
    date        = db.Column(db.DateTime, nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __init__(self, subject, message, user_id):
        self.subject       = subject
        self.message       = message
        self.date          = dt.now()
        self.user_id       = user_id
