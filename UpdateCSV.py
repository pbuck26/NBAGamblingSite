#!/usr/bin/env python3.8
from datetime import date, datetime, timedelta
import pandas as pd
from sportsipy.nba.boxscore import Boxscores, Boxscore
import os

def main():

    file_path = os.getcwd()

    with open(file_path + '/nbaScraperModelData.csv', "r") as f:
        last_line = f.readlines()[-1].strip().split(",")
        last_recorded_date = last_line[-1]
    
    datetime_object = datetime.strptime(last_recorded_date, '%I:%M%p, %B %d, %Y')
    start_date = datetime_object + timedelta(days=1)
    start_date = date(2021,10,19)
    end_date   = date.today() 
    game_dates = Boxscores(start_date, end_date)
    for date_key in game_dates.games.keys():
        for game_key in game_dates.games[date_key]:
            game_df = Boxscore(game_key['boxscore'])
            game_Stats = {}
            # winning team (not always home) -- home team on top 
            winningTeam = game_df.winner
            if winningTeam == 'Home':
                game_Stats['Home']         = game_df.winning_name
                game_Stats['winningScore'] = game_df.home_points
                game_Stats['losingScore']  = game_df.away_points

            else:
                game_Stats['Home']         = game_df.losing_name
                game_Stats['winningScore'] = game_df.away_points
                game_Stats['losingScore']  = game_df.home_points
            
            game_Stats['winningTeam']  = game_df.winning_name
            game_Stats['losingTeam']   = game_df.losing_name

            game_Stats['Pace_Home'] = game_df.pace
            game_Stats['Pace_AWAY'] = game_df.pace

            game_Stats['FG_PpercentHome'] = game_df.home_effective_field_goal_percentage
            game_Stats['FG_PpercentAWAY'] = game_df.away_effective_field_goal_percentage

            game_Stats['TOV_Home'] = game_df.home_turnovers
            game_Stats['TOV_AWAY'] = game_df.away_turnovers

            game_Stats['ORB_Home'] = game_df.home_offensive_rebounds
            game_Stats['ORB_AWAY'] = game_df.away_offensive_rebounds

            game_Stats['FT_Rate_Home'] = game_df.home_free_throw_attempt_rate
            game_Stats['FT_Rate_AWAY'] = game_df.away_free_throw_attempt_rate

            game_Stats['Off_Rat_Home'] = game_df.home_offensive_rating
            game_Stats['Off_Rat_AWAY'] = game_df.away_offensive_rating

            # get date
            game_Stats['date'] = game_df.date

            df = pd.DataFrame(game_Stats, index=[0])

            df.to_csv(file_path + '/nbaScrapermodelData.csv', mode='a', header=False)
            # look up injuries?
            # player/team nba ratings? 2k ratings?
            # back2back game indicator
            # away game stretch
            # cool site --> http://www.espn.com/nba/hollinger/teamstats/_/sort/defensiveEff/order/false
            # could get logos from site
            # scrape lines at different sites
if __name__ == "__main__":
    main()