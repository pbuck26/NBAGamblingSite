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

    from .scrapeTodaysGames import scrapeGamesAndOdds

    @app.before_first_request
    def load_model():
        model = pickle.load(open('model.pkl','rb'))
        global games
        games = scrapeGamesAndOdds(model)


    @app.route("/")
    def renderHomepage():
        app.logger.info('homepage')
        # have to add a "pick" variable
        # verify that the path to static png file works
        # arrange picks into one variable
        # move website html to index file
        return render_template('websitetake2.html', games = games, user_verified = False)
    
    @app.route("/", methods=['POST', 'GET'])
    def get_email():
        app.logger.info('Email request endpoint')
        if "email" in request.form:
            email = request.form['email']
            password = request.form['pwd']
            data = Users(email, password)
            db.session.add(data)
            db.session.commit()
            return render_template('websitetake2.html', games = games, user_verified = True)
        else:
            app.logger.error('poopoo')


    return app