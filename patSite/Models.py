from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Users(UserMixin, db.Model):
    __tablename__='users'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(200), unique=True, nullable=False)
    password   = db.Column(db.String(200), nullable=False)
    created_on = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)

    def __init__(self, email, password):
        self.email     = email
        self.password  = password
        self.name      = name 
    
    def set_password(self, password):
        self.password = generate_password_hash(password, 'sha256')

    def check_password(self, password):
        return check_password_hash(self.password)
    
    def __repr__(self):
        return '<User {}>'.format(self.id)