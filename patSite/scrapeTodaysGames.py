# will have to make this its own function at some point
from flask_sqlalchemy import SQLAlchemy
import requests
from datetime import date
import sklearn
from sklearn.naive_bayes import GaussianNB
import pandas as pd
import os
import numpy as np
from sportsreference.nba.teams import Teams
from patSite.trainAndExportModel import MultiColumnLabelEncoder, avg_previous_num_games, format_nba_df
import sys
from flask_sqlalchemy import SQLAlchemy

# Main Function
def scrapeGamesAndOdds(Model):
    df = pd.read_csv(os.getcwd() + '/nbaScrapermodelData.csv')
    # format data
    df = format_nba_df(df)
    #do averaging thing i dont understand
    df = avg_previous_num_games(df)
    columnsT= np.array(df.columns.to_list())
    columnsT = columnsT[[1,2,3,4,5,6,7,8,9,10,11,12,15,16,14]]
    columnsT = columnsT.tolist()
    df = df[columnsT]

    #encode features
    df = MultiColumnLabelEncoder(columns = ['homeTeam','awayTeam']).fit_transform(df)

    source = requests.get("https://www.bovada.lv/services/sports/event/v2/events/A/description/basketball/nba").json()
    homeOdds        = []
    homeTeam        = []
    awayTeam        = []
    awayOdds        = []
    predictionFaith = []
    games           = []
    gameIndex = 0
    #print(f'{date.today()} games:\n')
    #main event loop
    for game in range(len(source[0]['events'])):
        if source[0]['events'][game]['competitors']:

            try: #For some reason this can be half moneyline
                if '2H' in source[0]['events'][game]['displayGroups'][0]['markets'][0]['outcomes'][0]['description']:
                    continue

                # Don't care about live games for right now
                if source[0]['events'][game]['displayGroups'][0]['markets'][0]['period']['description'] == 'Live Game':
                    continue

                if source[0]['events'][game]['displayGroups'][0]['markets'][0]['outcomes'][0]['type'] == 'H':
                    homeIndex = 0
                    awayIndex = 1
                else:
                    awayIndex = 0
                    homeIndex = 1
                
                homeOdds.append(source[0]['events'][game]['displayGroups'][0]['markets'][0]['outcomes'][homeIndex]['price']['american'])
                homeTeam.append(source[0]['events'][game]['displayGroups'][0]['markets'][0]['outcomes'][homeIndex]['description'])
                awayOdds.append(source[0]['events'][game]['displayGroups'][0]['markets'][0]['outcomes'][awayIndex]['price']['american'])
                awayTeam.append(source[0]['events'][game]['displayGroups'][0]['markets'][0]['outcomes'][awayIndex]['description'])
                #print("######################################################")
                #print(f'{homeTeam[-1]} ({homeOdds[-1]}) vs {awayTeam[-1]} ({awayOdds[-1]})')
                beans = getTeamData4Model(df, homeTeam[-1], awayTeam[-1])
                #prediction = Model.predict(beans)
                predictionAcc = Model.predict_proba(beans)
                if homeOdds[-1] == 'EVEN':
                    homeOdds[-1] = '-100'
                if awayOdds[-1] == 'EVEN':
                    awayOdds[-1] = '-100'
                predictionFaith.append(predictionAcc[0,1])
                probHome  = getImpliedProbability(int(homeOdds[-1]))
                #awayOdds[-1] = getImpliedProbability(int(awayOdds[-1]))

                prediction = Model.predict(beans)
                if prediction:
                    pick = homeTeam[-1]
                else:
                    pick = awayTeam[-1]
                
                #stupid formatting
                if homeTeam[-1] == "L.A. Clippers":
                    homeTeam[-1] = "Los Angeles Clippers"
                if awayTeam[-1] == "L.A. Clippers":
                    awayTeam[-1] = "Los Angeles Clippers"
                if pick == "L.A. Clippers":
                    pick = "Los Angeles Clippers"
                # Lakers section
                if homeTeam[-1] == "L.A. Lakers":
                    homeTeam[-1] = "Los Angeles Lakers"
                if awayTeam[-1] == "L.A. Lakers":
                    awayTeam[-1] = "Los Angeles Lakers"
                if pick == "L.A. Lakers":
                    pick = "Los Angeles Lakers"



                homeTeam[-1] = homeTeam[-1].replace(" ", "%20")
                awayTeam[-1] = awayTeam[-1].replace(" ", "%20")
                pick = pick.replace(" ", "%20")
                gameT = {
                "homeOdds"    :homeOdds[-1],
                "awayOdds"    :awayOdds[-1],
                "homeTeam"    :f"/static/{homeTeam[-1]}.png",
                "awayTeam"    :f"/static/{awayTeam[-1]}.png",
                "pick"        :f"/static/{pick}.png",
                "prob"        :"{:.2f}".format(predictionFaith[-1]),
                "vegas_prob"  :"{:.2f}".format(probHome)
                }
                games.append(gameT)
                gameIndex +=1
            except:
                print('stinky shit!')

            else:
                continue
    from patSite.Models import Picks, db
    for game in games:
        picks_final = Picks(game.get("homeOdds"), game.get("awayOdds"), game.get("homeTeam"), 
        game.get("awayTeam"), game.get("pick"), game.get("prob"), game.get("vegas_prob"))
        db.session.add(picks_final)
    db.session.commit()

def getTeamData4Model(df, homeTeam, awayTeam):
    #find matching team
    predObject = predictionFormatter()
    homeTeamEncoded = predObject.setEncodingIndex(homeTeam)
    awayTeamEncoded = predObject.setEncodingIndex(awayTeam)

    #populate Away Stats
    dfFinal = df[df['awayTeam'] == awayTeamEncoded].iloc[[-1]]
    dfFinal['Pace_Home'].iloc[[-1]]    = df[df['homeTeam'] == homeTeamEncoded].iloc[[-1]]['Pace_Home']
    dfFinal['TOV_Home'].iloc[[-1]]     = df[df['homeTeam'] == homeTeamEncoded].iloc[[-1]]['TOV_Home']
    dfFinal['ORB_Home'].iloc[[-1]]     = df[df['homeTeam'] == homeTeamEncoded].iloc[[-1]]['ORB_Home']
    dfFinal['FT_Rate_Home'].iloc[[-1]] = df[df['homeTeam'] == homeTeamEncoded].iloc[[-1]]['FT_Rate_Home']
    dfFinal['Off_Rat_Home'].iloc[[-1]] = df[df['homeTeam'] == homeTeamEncoded].iloc[[-1]]['Off_Rat_Home']
    dfFinal['homeTeam'].iloc[[-1]]     = df[df['homeTeam'] == homeTeamEncoded].iloc[[-1]]['homeTeam']
    beans = dfFinal[dfFinal.columns[:-1]]
    return beans

class predictionFormatter:
    def __init__(self):
        #get team data
        self.teamNamesJson = []
        teams = Teams()
        for team in teams:
            self.teamNamesJson.append(team.name)
        self.teamNamesJson.sort()

    def setEncodingIndex(self, teamString):
        if teamString == "L.A. Clippers":
            teamString = "Los Angeles Clippers"
        return self.teamNamesJson.index(teamString)

def getImpliedProbability(line):
    if line > 0:
        prob = 100/(line + 100)
        return prob
    else:
        prob = abs(line)/(abs(line) + 100)
        return prob

if __name__ == "__main__":
    Model = sys.argv[1]
    scrapeGamesAndOdds(Model)