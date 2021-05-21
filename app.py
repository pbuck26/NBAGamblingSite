from flask import Flask, request, render_template, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
import json
import sklearn
from sklearn.naive_bayes import GaussianNB
import requests
import scrapeTodaysGames as sc
import logging
import pickle
import os

app = Flask(__name__)

#app.config['SECRET_KEY'] = 'POOP'
logging.basicConfig(level=logging.DEBUG)

db=SQLAlchemy(app)

class Users(db.Model):
    __tablename__='users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200))
    password = db.Column(db.String(200))

    def __init__(self, email, password):
        self.email     =  email
        self.password  = password

# Unpickle model and make todays predictions
app.logger.info('Importing Model!')
Model = pickle.load(open('model.pkl','rb'))
app.logger.info('Scraping Games!')
games = sc.scrapeGamesAndOdds(Model)

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
        
if __name__ == '__main__':
    app.run()