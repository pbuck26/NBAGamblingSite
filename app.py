from flask import Flask, request, render_template, jsonify, Response
import json
import sklearn
from sklearn.naive_bayes import GaussianNB
import pandas as pd
import numpy as np
import os
from sportsreference.nba.schedule import Schedule
from sportsreference.nba.boxscore import Boxscores, Boxscore
from sportsreference.nba.teams import Teams
from datetime import date, timedelta
import requests
import scrapeTodaysGames as sc
import trainAndExportModel as tm
import logging
import pprint

app = Flask(__name__)
app.config['SECRET_KEY'] = 'POOP'

logging.basicConfig(level=logging.DEBUG)

#Daily function calls
# Will have to see if I can scrape data using webdriver on server
Model  = tm.trainAndExportModel()
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
        
def getTeamStr(dictionary, number):
    for key, value in dictionary.items():  # for name, age in dictionary.iteritems():  (for Python 2.x)
        if value == number:
            #print(key)
            return key

def getImpliedProbability(line):
    if line > 0:
        prob = 100/(line + 100)
        return prob
    else:
        prob = abs(line)/(abs(line) + 100)
        return prob

def getPayout(odds, wager):
    if odds > 0:
        payout = (wager*odds)/100
        return payout
    else:
        payout = (wager*100)/abs(odds)
        return payout

if __name__ == '__main__':
    app.run(debug=True)