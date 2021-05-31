import click
from .Models import db
from .Models import Picks, Users
import pickle
from flask import Blueprint

commands_bp= Blueprint('commands', __name__)

@commands_bp.cli.command('create_db')
def create_db():
    """Creates database"""
    db.create_all()

@commands_bp.cli.command('drop_db')
def drop_db():
    """Drop / Clean database - DANGER ACTION"""
    db.drop_all()

@commands_bp.cli.command('create_table')
def create_model_table():
    """Create table model in the database"""
    from patSite.scrapeTodaysGames import scrapeGamesAndOdds
    model = pickle.load(open('model.pkl','rb'))
    scrapeGamesAndOdds(model)
