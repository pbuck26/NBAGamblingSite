import os
from flask import Flask, request, render_template, jsonify, Response, g
import pickle
import logging
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from patSite import commands

db=SQLAlchemy()
login_manager = LoginManager()

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=False)

    # load the instance config, if it exists, when not testing
    app.config.from_object("config.Config")
    app.logger.info("Creating application")
    db.init_app(app)
    commands.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        from patSite.routes import routes_blueprint
        app.register_blueprint(routes_blueprint)
        from patSite import Models
        from patSite.auth import auth_bp
        app.register_blueprint(auth_bp)
        Models.db.create_all()
    
    from patSite.scrapeTodaysGames import scrapeGamesAndOdds

    #@app.before_request
    #def load_model():
     #   model = pickle.load(open('model.pkl','rb'))
      #  g.games = scrapeGamesAndOdds(model)

    return app