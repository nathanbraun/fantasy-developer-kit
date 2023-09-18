import numpy as np
from pandas import DataFrame, Series
import pandas as pd
from utilities import (
    LICENSE_KEY, generate_token, master_player_lookup, YAHOO_FILE, YAHOO_KEY,
    YAHOO_SECRET, YAHOO_GAME_ID, SEASON)
import json
from yahoo_oauth import OAuth2
from pathlib import Path

pd.options.mode.chained_assignment = None

# store credentials if don't already exist
if not Path(YAHOO_FILE).exists():
    yahoo_credentials_dict = {
        'consumer_key': YAHOO_KEY,
        'consumer_secret': YAHOO_SECRET,
    }
    with open(YAHOO_FILE, 'w') as f:
        json.dump(yahoo_credentials_dict, f)

OAUTH = OAuth2(None, None, from_file=YAHOO_FILE)

game_url = 'https://fantasysports.yahooapis.com/fantasy/v2/game/nfl'
OAUTH.session.get(game_url, params={'format': 'json'}).json()

###############################################################################
# roster data
###############################################################################

LEAGUE_ID = 39252
TEAM_ID = 1
WEEK = 2
USE_SAVED_DATA = True

roster_url = ('https://fantasysports.yahooapis.com/fantasy/v2' +
            f'/team/{YAHOO_GAME_ID}.l.{LEAGUE_ID}.t.{TEAM_ID}/roster;week={WEEK}')


if USE_SAVED_DATA:
    with open('./projects/integration/raw/yahoo/roster.json') as f:
        roster_json = json.load(f)
else:
    roster_json = OAUTH.session.get(roster_url, params={'format': 'json'}).json()

# open up in browser and look at it

players_dict = (
    roster_json['fantasy_content']['team'][1]['roster']['0']['players'])

players_dict.keys()

player0 = players_dict['0']  # 
player0

def player_list_to_dict(player):
    player_info = player['player'][0]

    player_info_dict = {}
    for x in player_info:
        if (type(x) is dict) and (len(x.keys()) == 1):
                for key in x.keys():  
                    player_info_dict[key] = x[key]
    return player_info_dict

player_list_to_dict(player0)

def process_player(player):
    player_info = player_list_to_dict(player)
    pos_info = player['player'][1]['selected_position'][1]

    dict_to_return = {}
    dict_to_return['yahoo_id'] = int(player_info['player_id'])
    dict_to_return['name'] = player_info['name']['full']
    dict_to_return['player_position'] = player_info['primary_position']
    dict_to_return['team_position'] = pos_info['position']

    return dict_to_return

process_player(player0)

[process_player(player) for key, player
 in players_dict.items() if key != 'count']

players_df =  DataFrame(
    [process_player(player) for key, player in players_dict.items() if key !=
     'count' ])

players_df

wrs = players_df.query("team_position == 'WR'")
wrs

suffix = Series(range(1, len(wrs) + 1), index=wrs.index)
suffix

wrs['team_position'] + suffix.astype(str)

def add_pos_suffix(df_subset):
    if len(df_subset) > 1:
        suffix = Series(range(1, len(df_subset) + 1), index=df_subset.index)

        df_subset['team_position'] = (
          df_subset['team_position'] + suffix.astype(str))
    return df_subset

players_df2 = pd.concat([
    add_pos_suffix(players_df.query(f"team_position == '{x}'"))
    for x in players_df['team_position'].unique()])

players_df2

players_df2['start'] = ~(players_df2['team_position'].str.startswith('BN') |
                         players_df2['team_position'].str.startswith('IR'))

players_df2

def process_players(players):
    players_raw = DataFrame(
        [process_player(player) for key, player in players.items() if key !=
         'count' ])

    players_df = pd.concat([
        add_pos_suffix(players_raw.query(f"team_position == '{x}'"))
        for x in players_raw['team_position'].unique()])

    players_df['start'] = ~(players_df['team_position'].str.startswith('BN') |
                            players_df['team_position'].str.startswith('IR'))

    return players_df

process_players(players_dict)

# players_dict = roster_json['fantasy_content']['team'][1]['roster']['0']['players']
team_id = roster_json['fantasy_content']['team'][0][1]['team_id']
team_id

def process_roster(team):
    players_df = process_players(team[1]['roster']['0']['players'])
    team_id = team[0][1]['team_id']

    players_df['team_id'] = team_id
    return players_df

roster_df = process_roster(roster_json['fantasy_content']['team'])
roster_df

# get actual points
points_url = ('https://fantasysports.yahooapis.com/fantasy/v2/' +
                f'team/{YAHOO_GAME_ID}.l.{LEAGUE_ID}.t.{TEAM_ID}' +
                f'/players/stats;type=week;week={WEEK};out=stats')

# saved data
if USE_SAVED_DATA:
    with open('./projects/integration/raw/yahoo/points.json') as f:
        points_json = json.load(f)
else:
    points_json = OAUTH.session.get(points_url, params={'format': 'json'}).json()

player_dict = points_json['fantasy_content']['team'][1]['players']
goedert = player_dict['7']

def process_player_stats(player):
    dict_to_return = {}
    dict_to_return['yahoo_id'] = int(player['player'][0][1]['player_id'])
    dict_to_return['actual'] = float(
        player['player'][1]['player_points']['total'])
    return dict_to_return

process_player_stats(goedert)

def process_team_stats(team):
    stats = DataFrame([process_player_stats(player) for key, player in
                       team.items() if key != 'count'])
    stats.loc[stats['actual'] == 0, 'actual'] = np.nan
    return stats

stats = process_team_stats(player_dict)

roster_df_w_stats = pd.merge(roster_df, stats)
roster_df_w_stats.head(10)

roster_df_w_stats['name'].str.lower().str.replace(' ','-').head()

from utilities import (LICENSE_KEY, generate_token, master_player_lookup)

if USE_SAVED_DATA:
    fantasymath_players = pd.read_csv('./projects/integration/raw/yahoo/lookup.csv')
else:
    token = generate_token(LICENSE_KEY)['token']
    fantasymath_players = master_player_lookup(token)

fantasymath_players.head()

roster_df_w_id = pd.merge(roster_df_w_stats,
                          fantasymath_players[['player_id', 'yahoo_id']],
                          how='left')

def get_team_roster(team_id, league_id, week, lookup):
    roster_url = ('https://fantasysports.yahooapis.com/fantasy/v2' +
                  f'/team/{YAHOO_GAME_ID}.l.{league_id}.t.{team_id}/roster;week={week}')

    roster_json = OAUTH.session.get(roster_url, params={'format': 'json'}).json()

    roster_df = process_roster(roster_json['fantasy_content']['team'])

    # stats
    points_url = ('https://fantasysports.yahooapis.com/fantasy/v2/' +
                    f'team/{YAHOO_GAME_ID}.l.{league_id}.t.{team_id}' +
                    f'/players/stats;type=week;week={week};out=stats')

    points_json = OAUTH.session.get(points_url, params={'format': 'json'}).json()

    player_dict = points_json['fantasy_content']['team'][1]['players']
    stats = process_team_stats(player_dict)
    roster_df_w_stats = pd.merge(roster_df, stats)

    roster_df_w_id = pd.merge(roster_df_w_stats,
                            lookup[['player_id', 'yahoo_id']],
                            how='left').drop('yahoo_id', axis=1)

    return roster_df_w_id

if USE_SAVED_DATA:
    my_roster = pd.read_csv('./projects/integration/raw/yahoo/my_roster.csv')
else:
    my_roster = get_team_roster(TEAM_ID, LEAGUE_ID, 1, fantasymath_players)

###############################################################################
# team data
###############################################################################

teams_url = ('https://fantasysports.yahooapis.com/fantasy/v2/' +
            f'league/{YAHOO_GAME_ID}.l.{LEAGUE_ID}' +
            ';out=metadata,settings,standings,scoreboard,teams,players,draftresults,transactions')

# gets current data

if USE_SAVED_DATA:
    with open('./projects/integration/raw/yahoo/teams.json') as f:
        teams_json = json.load(f)
else:
    teams_json = (OAUTH
                    .session
                    .get(teams_url, params={'format': 'json'})
                    .json())


teams_dict = teams_json['fantasy_content']['league'][2]['standings'][0]['teams']

teams_dict.keys()

team0 = teams_dict['0']
team0

def yahoo_list_to_dict(yahoo_list, key):
    return_dict = {}
    for x in yahoo_list[key][0]:
        if (type(x) is dict) and (len(x.keys()) == 1):
                for key_ in x.keys():  # tricky way to get access to key
                    return_dict[key_] = x[key_]
    return return_dict

yahoo_list_to_dict(team0, 'team')

def process_team(team):
    team_dict = yahoo_list_to_dict(team, 'team')
    owner_dict = team_dict['managers'][0]['manager']

    dict_to_return = {}
    dict_to_return['team_id'] = team_dict['team_id']
    dict_to_return['owner_id'] = owner_dict['guid']
    dict_to_return['owner_name'] = owner_dict['nickname']
    return dict_to_return

process_team(team0)

def get_teams_in_league(league_id):
    teams_url = ('https://fantasysports.yahooapis.com/fantasy/v2/' +
                f'league/{YAHOO_GAME_ID}.l.{league_id}' +
                ';out=metadata,settings,standings,scoreboard,teams,players,draftresults,transactions')

    teams_json = (OAUTH
                 .session
                 .get(teams_url, params={'format': 'json'})
                 .json())

    teams_dict = (teams_json['fantasy_content']
                  ['league'][2]['standings'][0]['teams'])

    teams_df = DataFrame([process_team(team) for key, team in
                          teams_dict.items() if key != 'count'])

    teams_df['league_id'] = league_id
    return teams_df

if USE_SAVED_DATA:
    league_teams = pd.read_csv('./projects/integration/raw/yahoo/league_teams.csv')
else:
    league_teams = get_teams_in_league(LEAGUE_ID)

league_teams

def get_league_rosters(lookup, league_id, week):
    teams = get_teams_in_league(league_id)

    league_rosters = pd.concat(
        [get_team_roster(x, league_id, week, lookup) for x in
         teams['team_id']], ignore_index=True)
    league_rosters['team_position'].replace({'W/R/T': 'WR/RB/TE'}, inplace=True)
    league_rosters['team_position'].replace({'Q/W/R/T': 'QB/WR/RB/TE'}, inplace=True)
    return league_rosters

if USE_SAVED_DATA:
    league_rosters = pd.read_csv('./projects/integration/raw/yahoo/league_rosters.csv')
else:
    league_rosters = get_league_rosters(fantasymath_players, LEAGUE_ID, WEEK)

league_rosters.sample(20)

###############################################################################
# schedule info
###############################################################################
schedule_url = ('https://fantasysports.yahooapis.com/fantasy/v2/' +
                f'team/{YAHOO_GAME_ID}.l.{LEAGUE_ID}.t.{TEAM_ID}' +
                ';out=matchups')

# saved data
if USE_SAVED_DATA:
    with open('./projects/integration/raw/yahoo/schedule.json') as f:
        schedule_json = json.load(f)
else:
    schedule_json = OAUTH.session.get(schedule_url, params={'format': 'json'}).json()

matchups_dict = schedule_json['fantasy_content']['team'][1]['matchups']
matchup0 = matchups_dict['0']

matchup0

matchup0['matchup']['0']['teams']['0']

matchup0_team0 = yahoo_list_to_dict(
    matchup0['matchup']['0']['teams']['0'], 'team')
matchup0_team1 = yahoo_list_to_dict(
    matchup0['matchup']['0']['teams']['1'], 'team')

matchup0_team0['team_id']
matchup0_team1['team_id']
matchup0['matchup']['week']

def process_matchup1(matchup):
    team0 = yahoo_list_to_dict(matchup['matchup']['0']['teams']['0'], 'team')
    team1 = yahoo_list_to_dict(matchup['matchup']['0']['teams']['1'], 'team')

    dict_to_return = {}
    dict_to_return['team_id'] = team0['team_id']
    dict_to_return['opp_id'] = team1['team_id']
    dict_to_return['week'] = matchup['matchup']['week']

    return dict_to_return


process_matchup1(matchup0)

DataFrame([process_matchup1(matchup)
           for key, matchup
           in matchups_dict.items()
           if key != 'count'])

def make_matchup_id(season, week, team1, team2):
    teams = [team1, team2]
    teams.sort()

    return int(str(season) + str(week).zfill(2) +
                     str(teams[0]).zfill(2) + str(teams[1]).zfill(2))

make_matchup_id(2023, 1, 1, 8)

make_matchup_id(2023, 1, 8, 1)

def process_matchup2(matchup):
    team0 = yahoo_list_to_dict(matchup['matchup']['0']['teams']['0'], 'team')
    team1 = yahoo_list_to_dict(matchup['matchup']['0']['teams']['1'], 'team')

    dict_to_return = {}
    dict_to_return['team_id'] = team0['team_id']
    dict_to_return['opp_id'] = team1['team_id']
    dict_to_return['week'] = matchup['matchup']['week']
    dict_to_return['matchup_id'] = make_matchup_id(
        SEASON, matchup['matchup']['week'], team0['team_id'], team1['team_id'])

    return dict_to_return

def get_schedule_by_team(team_id, league_id):
    schedule_url = ('https://fantasysports.yahooapis.com/fantasy/v2/' +
                    f'team/{YAHOO_GAME_ID}.l.{league_id}.t.{team_id}' +
                    ';out=matchups')

    schedule_raw = OAUTH.session.get(schedule_url, params={'format': 'json'}).json()
    matchup_dict = schedule_raw['fantasy_content']['team'][1]['matchups']
    df =  DataFrame([process_matchup2(matchup)
            for key, matchup
            in matchup_dict.items()
            if key != 'count'])
    df['season'] = SEASON
    return df

if USE_SAVED_DATA:
    all_team_schedules = pd.read_csv('./projects/integration/raw/yahoo/schedule.csv')
else:
    all_team_schedules = pd.concat([get_schedule_by_team(x, LEAGUE_ID) for x in
                                    league_teams['team_id']], ignore_index=True)

all_team_schedules.head(20)

# in wide, week form:
schedule_by_week = all_team_schedules.drop_duplicates('matchup_id')

schedule_by_week.columns = ['team1_id', 'team2_id', 'week', 'matchup_id',
                            'season']

schedule_by_week.head(10)

def get_league_schedule(league_id):
    league_teams = get_teams_in_league(league_id)

    schedule_by_team = pd.concat([get_schedule_by_team(x, league_id) for
                                  x in league_teams['team_id']],
                                   ignore_index=True)

    schedule_by_week = schedule_by_team.drop_duplicates('matchup_id')

    schedule_by_week.columns = ['team1_id', 'team2_id', 'week', 'matchup_id',
                                'season']
    return schedule_by_week

if USE_SAVED_DATA:
    league_schedule = pd.read_csv('./projects/integration/raw/yahoo/league_schedule.csv')
else:
    league_schedule = get_league_schedule(LEAGUE_ID)
league_schedule.head(10)

###############################################################################
###############################################################################

# note: this part isn't meant to be run
# i (NB) am running this Friday 9/15/23 - after PHI beat MIN last night - to
# save data we'll load above
# 
# including here to make it clearer this saved data just comes from APIs

#################################
# get data from Yahoo and FM apis
#################################

LEAGUE_ID = 39252
TEAM_ID = 1
WEEK = 2
SEASON = 2023
USE_SAVED_DATA = False

roster_url = ('https://fantasysports.yahooapis.com/fantasy/v2' +
            f'/team/{YAHOO_GAME_ID}.l.{LEAGUE_ID}.t.{TEAM_ID}/roster;week={WEEK}')

points_url = ('https://fantasysports.yahooapis.com/fantasy/v2/' +
                f'team/{YAHOO_GAME_ID}.l.{LEAGUE_ID}.t.{TEAM_ID}' +
                f'/players/stats;type=week;week={WEEK};out=stats')

teams_url = ('https://fantasysports.yahooapis.com/fantasy/v2/' +
            f'league/{YAHOO_GAME_ID}.l.{LEAGUE_ID}' +
            ';out=metadata,settings,standings,scoreboard,teams,players,draftresults,transactions')

schedule_url = ('https://fantasysports.yahooapis.com/fantasy/v2/' +
                f'team/{YAHOO_GAME_ID}.l.{LEAGUE_ID}.t.{TEAM_ID}' +
                ';out=matchups')

token = generate_token(LICENSE_KEY)['token']

roster_json = OAUTH.session.get(roster_url, params={'format': 'json'}).json()

points_json = OAUTH.session.get(points_url, params={'format': 'json'}).json()

# player_dict = points_json['fantasy_content']['team'][1]['players']
# player_dict['9']

teams_json = (OAUTH.session.get(teams_url, params={'format': 'json'}).json())
schedule_json = OAUTH.session.get(schedule_url, params={'format': 'json'}).json()
fantasymath_players = master_player_lookup(token)
league_schedule = get_league_schedule(LEAGUE_ID)
league_rosters = get_league_rosters(fantasymath_players, LEAGUE_ID, WEEK)
my_roster = get_team_roster(TEAM_ID, LEAGUE_ID, 1, fantasymath_players)
league_teams = get_teams_in_league(LEAGUE_ID)

#############
# now save it
#############

with open('./projects/integration/raw/yahoo/roster.json', 'w') as f:
    json.dump(roster_json, f)

with open('./projects/integration/raw/yahoo/points.json', 'w') as f:
    json.dump(points_json, f)

with open('./projects/integration/raw/yahoo/teams.json', 'w') as f:
    json.dump(teams_json, f)

with open('./projects/integration/raw/yahoo/schedule.json', 'w') as f:
    json.dump(schedule_json, f)

fantasymath_players.to_csv('./projects/integration/raw/yahoo/lookup.csv', index=False)
all_team_schedules.to_csv('./projects/integration/raw/yahoo/schedule.csv', index=False)
league_rosters.to_csv('./projects/integration/raw/yahoo/league_rosters.csv', index=False)
league_schedule.to_csv('./projects/integration/raw/yahoo/league_schedule.csv', index=False)
my_roster.to_csv('./projects/integration/raw/yahoo/my_roster.csv', index=False)
league_teams.to_csv('./projects/integration/raw/yahoo/league_teams.csv', index=False)
