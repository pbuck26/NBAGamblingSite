import os
from flask import Flask, request, render_template, jsonify, Response
import pickle
import logging
from flask_sqlalchemy import SQLAlchemy

db=SQLAlchemy()

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=False)

    # load the instance config, if it exists, when not testing
    app.config.from_object("config.Config")
    
    db.init_app(app)
    with app.app_context():
        from patSite.routes import routes_blueprint
        import patSite.Models
        Models.db.create_all()
    
    from patSite.scrapeTodaysGames import scrapeGamesAndOdds

    @app.before_first_request
    def load_model():
        model = pickle.load(open('model.pkl','rb'))
        global games
        games = scrapeGamesAndOdds(model)

    return app