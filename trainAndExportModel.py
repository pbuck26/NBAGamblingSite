import pandas as pd
import numpy as np
import os
import sklearn
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import LabelEncoder
import pickle

# This function when called will return the trained model ready for making predictions
# As of now it will scrape the data from a csv file
# This should be called once a day after "scrapeTodaysGames.py" is called and updates
# the csv file/database

def trainAndExportModel():
# start of this function
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

    # x feature matrix
    # y = home win(y/n)
    x = df[df.columns[:-1]]
    y = df[df.columns[-1]]

    from sklearn.model_selection import train_test_split
    x_train, x_test, y_train, y_test = train_test_split(x,y, test_size=0.2, random_state=1)

    #instantiate model
    bng = GaussianNB()
    #fit data to model
    bngModel = bng.fit(x_train, y_train)
    # score model
    score = bngModel.score(x_test, y_test)
    print(f"Score fo Bayes Model: {score}\n")
    pickle.dump(bngModel, open('model.pkl', 'wb'))

class MultiColumnLabelEncoder:
    def __init__(self,columns = None):
        self.columns = columns # array of column names to encode

    def fit(self,X,y=None):
        return self # not relevant here

    def transform(self,X):
        '''
        Transforms columns of X specified in self.columns using
        LabelEncoder(). If no columns specified, transforms all
        columns in X.
        '''
        #from sklearn.preprocessing import LabelEncoder
        output = X.copy()
        dictionary = []
        if self.columns is not None:
            for col in self.columns:
                encoder = LabelEncoder()
                output[col] = encoder.fit_transform(output[col])
                keys= encoder.classes_
                values = encoder.transform(encoder.classes_)
                dictionary.append(dict(zip(keys,values)))
                #print(dictionary)
        else:
            for colname,col in output.iteritems():
                output[colname] = LabelEncoder().fit_transform(col)
        return output

    def fit_transform(self,X,y=None):
        return self.fit(X,y).transform(X)

def format_nba_df(df):
    print(df.columns)
    print(df.head())
    df['homeWin'] = df['winningTeam'] == df['Home']
    df['homeTeam'] = np.where(df['homeWin']==True, df['winningTeam'], df['losingTeam'])
    ## create away team column
    df['awayTeam'] = np.where(df['homeWin']==False, df['winningTeam'], df['losingTeam'])
    df['homeScore'] = np.where(df['homeWin']==True, df['winningScore'], df['losingScore'])
    df['awayScore'] = np.where(df['homeWin']==False, df['winningScore'], df['losingScore'])
    df['pointDiff'] = df['homeScore'] - df['awayScore']
    df.drop(['winningScore', 'losingScore', 'winningTeam', 'losingTeam', 'Home'], axis=1, inplace=True)
    return df

def avg_previous_num_games(df):
    ### This function changes each stat to be the average of the last num_games for each team, and shifts it one so it does not include the current stats and drops the first num_games that become null
    columnsT = df.columns.to_list()
    home_col = columnsT[1:13:2]
    away_col = columnsT[2:13:2]
    # get list of teams
    team_list = df['homeTeam'].unique()
    for col in home_col:
        for team in team_list:
            df[col].loc[df['homeTeam']==team] = df[col].loc[df['homeTeam']==team].expanding(1).mean()
    for col in away_col:
        for team in team_list:
            df[col].loc[df['awayTeam']==team] = df[col].loc[df['awayTeam']==team].expanding(1).mean()
    return df.dropna()

if __name__ == "__main__":
    trainAndExportModel()