from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime as dt

class Users(UserMixin, db.Model):
    __tablename__='users'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(200), unique=True, nullable=False)
    password   = db.Column(db.String(200), nullable=False)
    created_on = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)

    def __init__(self, email, password, name):
        self.email      = email
        self.password   = password
        self.name       = name
        self.created_on = dt.now()
        self.last_login = dt.now()
    
    def set_password(self, password):
        self.password = generate_password_hash(password, 'sha256')

    def check_password(self, password):
        return check_password_hash(self.password)
    
    def __repr__(self):
        return '<User {}>'.format(self.id)

class Picks(db.Model):
    __tablename__='picks'
    id          = db.Column(db.Integer, primary_key=True)
    homeOdds    = db.Column(db.String(200), nullable=False)
    awayOdds    = db.Column(db.String(200), nullable=False)
    homeTeam    = db.Column(db.String(200), nullable=False)
    awayTeam    = db.Column(db.String(200), nullable=False)
    date        = db.Column(db.DateTime, nullable=False)
    pick        = db.Column(db.String(200), nullable=False)
    prob        = db.Column(db.String(200), nullable=False)
    vegas_prob  = db.Column(db.String(200), nullable=False)
    correctPick = db.Column(db.Boolean, nullable=True)

    def __init__(self, homeOdds, awayOdds, homeTeam, awayTeam, pick, prob, vegas_prob):
        self.homeOdds       = homeOdds
        self.awayOdds       = awayOdds
        self.homeTeam       = homeTeam
        self.awayTeam       = awayTeam
        self.date           = dt.now()
        self.pick           = pick
        self.prob           = prob
        self.vegas_prob     = pick
