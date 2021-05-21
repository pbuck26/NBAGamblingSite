import os
from flask import Flask, request, render_template, jsonify, Response
import pickle
import logging
from flask_sqlalchemy import SQLAlchemy

db=SQLAlchemy()

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    db.init_app(app)

    from .scrapeTodaysGames import scrapeGamesAndOdds

    Model = pickle.load(open(os.getcwd() + 'model.pkl','rb'))
    games = scrapeGamesAndOdds(Model)

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