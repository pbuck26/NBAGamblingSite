from flask import Flask, request, render_template, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
import json
import sklearn
from sklearn.naive_bayes import GaussianNB
from datetime import date, timedelta
import requests
import scrapeTodaysGames as sc
import logging
import pickle

app = Flask(__name__)

ENV= 'dev'
app.config['SECRET_KEY'] = 'POOP'
logging.basicConfig(level=logging.DEBUG)

if ENV == 'dev':
    app.debug= True
    app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://patrickbuckley:#xk3Li626@localhost"
else:
    app.debug=False
    app.config['SQLALCHEMY_DATABASE_URI'] = ""

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    return render_template('websitetake2.html', games = games)


@app.route("/", methods=['POST', 'GET'])
def get_email():
    app.logger.info('Email request endpoint')
    if "email" in request.form:
        email = request.form['email']
        password = request.form['pwd']
        return request.form['email']
    else:
        app.logger.error('poopoo')
        
if __name__ == '__main__':
    app.run()