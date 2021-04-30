from flask import Flask, request, render_template, jsonify
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

app = Flask(__name__)

#Daily function calls
# Will have to see if I can scrape data using webdriver on server
Model  = tm.trainAndExportModel()
games = sc.scrapeGamesAndOdds(Model)

@app.route("/")
def renderHomepage():
    # have to add a "pick" variable
    # verify that the path to static png file works
    # arrange picks into one variable
    # move website html to index file
    
    return render_template('websitetake2.html', games = games)

#define route
@app.route("/result',methods = ['POST']")
def hello(temp):
    return
        
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

