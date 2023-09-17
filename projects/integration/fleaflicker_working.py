import requests
import numpy as np
from pandas import DataFrame, Series
import pandas as pd
from utilities import LICENSE_KEY, SEASON, generate_token, master_player_lookup
import json

pd.options.mode.chained_assignment = None

LEAGUE_ID = 316893
TEAM_ID = 1605156
WEEK = 2
USE_SAVED_DATA = True

###############################################################################
# roster data
###############################################################################
roster_url = ('https://www.fleaflicker.com/api/FetchRoster?' +
              f'leagueId={LEAGUE_ID}&teamId={TEAM_ID}')

if USE_SAVED_DATA:
    with open('./projects/integration/raw/fleaflicker/roster.json') as f:
        roster_json = json.load(f)
else:
    roster_json = requests.get(roster_url).json()

list_of_starter_slots = roster_json['groups'][0]['slots']
list_of_bench_slots = roster_json['groups'][1]['slots']

starter_slot0 = list_of_starter_slots[0]

starter_slot0['leaguePlayer']['proPlayer']

def process_player1(slot):
    fleaflicker_player_dict = slot['leaguePlayer']['proPlayer']
    fleaflicker_position_dict = slot['position']

    dict_to_return = {}
    dict_to_return['name'] = fleaflicker_player_dict['nameFull']
    dict_to_return['player_position'] = fleaflicker_player_dict['position']
    dict_to_return['fleaflicker_id'] = fleaflicker_player_dict['id']

    dict_to_return['team_position'] = fleaflicker_position_dict['label']

    return dict_to_return

process_player1(starter_slot0)

[process_player1(player) for player in list_of_starter_slots]
[process_player1(player) for player in list_of_bench_slots]  

# to modify process_player1 to handle situations where leaguePlayer isn't in
# dict
def process_player2(slot):
    dict_to_return = {}

    if 'leaguePlayer' in slot.keys():
        fleaflicker_player_dict = slot['leaguePlayer']['proPlayer']

        dict_to_return['name'] = fleaflicker_player_dict['nameFull']
        dict_to_return['player_position'] = fleaflicker_player_dict['position']
        dict_to_return['fleaflicker_id'] = fleaflicker_player_dict['id']

    if 'position' in slot.keys():
        fleaflicker_position_dict = slot['position']

        dict_to_return['team_position'] = fleaflicker_position_dict['label']

    return dict_to_return

[process_player2(x) for x in list_of_starter_slots]

starter_df1 = DataFrame([process_player2(x) for x in list_of_starter_slots])
starter_df1

def process_player3(slot):
    dict_to_return = {}

    if 'leaguePlayer' in slot.keys():
        fleaflicker_player_dict = slot['leaguePlayer']['proPlayer']

        dict_to_return['name'] = fleaflicker_player_dict['nameFull']
        dict_to_return['player_position'] = fleaflicker_player_dict['position']
        dict_to_return['fleaflicker_id'] = fleaflicker_player_dict['id']

        if 'requestedGames' in slot['leaguePlayer']:
            game = slot['leaguePlayer']['requestedGames'][0]
            if 'pointsActual' in game:
                if 'value' in game['pointsActual']:
                    dict_to_return['actual'] = game['pointsActual']['value']


    if 'position' in slot.keys():
        fleaflicker_position_dict = slot['position']

        dict_to_return['team_position'] = fleaflicker_position_dict['label']

    return dict_to_return

# list of dicts: put in DataFrame
starter_df1 = DataFrame([process_player3(x) for x in list_of_starter_slots])
starter_df1

# looks pretty good
# but duplicate team_positions might be a problem
# would be better to have it be RB1, RB2, etc

# start with specific example
wrs = starter_df1.query("team_position == 'WR'")
wrs

suffix = Series(range(1, len(wrs) + 1), index=wrs.index)
suffix

wrs['team_position'] = wrs['team_position'] + suffix.astype(str)
wrs

# so put in a function that takes any position
def add_pos_suffix(df_subset):
    if len(df_subset) > 1:
        suffix = Series(range(1, len(df_subset) + 1), index=df_subset.index)

        df_subset['team_position'] = df_subset['team_position'] + suffix.astype(str)
    return df_subset

# and we want to apply it to every position in the starter df
starter_df2 = pd.concat([
    add_pos_suffix(starter_df1.query(f"team_position == '{x}'"))
    for x in starter_df1['team_position'].unique()])

starter_df2

bench_df = DataFrame([process_player3(x) for x in list_of_bench_slots])

# now let's ID these and stick them together
starter_df2['start'] = True
bench_df['start'] = False

roster_df = pd.concat([starter_df2, bench_df], ignore_index=True)
roster_df

roster_df['team_id'] = TEAM_ID
roster_df.head()

from utilities import (LICENSE_KEY, generate_token, master_player_lookup)

if USE_SAVED_DATA:
    fantasymath_players = pd.read_csv('./projects/integration/raw/fleaflicker/lookup.csv')
else:
    token = generate_token(LICENSE_KEY)['token']
    fantasymath_players = master_player_lookup(token)

fantasymath_players.head()

roster_df_w_id = pd.merge(
    roster_df, fantasymath_players[['player_id', 'fleaflicker_id']],
    how='left')

# we can basically put everything we did above into a function
# put in a function

def get_team_roster(team_id, league_id, lookup):
    roster_url = ('https://www.fleaflicker.com/api/FetchRoster?' +
        f'leagueId={league_id}&teamId={team_id}')

    roster_json = requests.get(roster_url).json()

    starter_slots = roster_json['groups'][0]['slots']
    bench_slots = roster_json['groups'][1]['slots']

    starter_df = DataFrame([process_player3(x) for x in starter_slots])
    bench_df = DataFrame([process_player3(x) for x in bench_slots])

    starter_df['start'] = True
    bench_df['start'] = False

    team_df = pd.concat([starter_df, bench_df], ignore_index=True)
    team_df['team_id'] = team_id

    team_df_w_id = pd.merge(team_df,
                            lookup[['player_id', 'fleaflicker_id']],
                            how='left').drop('fleaflicker_id', axis=1)

    if 'actual' not in team_df_w_id.columns:
        team_df_w_id['actual'] = np.nan

    return team_df_w_id

if USE_SAVED_DATA:
    my_roster = pd.read_csv('./projects/integration/raw/fleaflicker/my_roster.csv')
else:
    my_roster = get_team_roster(TEAM_ID, LEAGUE_ID, fantasymath_players)

my_roster

###############################################################################
# team data
###############################################################################

# gets current data
teams_url = ('https://www.fleaflicker.com/api/FetchLeagueStandings?' +
             f'leagueId={LEAGUE_ID}')
# saved data
if USE_SAVED_DATA:
    with open('./projects/integration/raw/fleaflicker/teams.json') as f:
        teams_json = json.load(f)
else:
    teams_json = requests.get(teams_url).json()

# same process - look at json (dict) and see how it's structured

division0 = teams_json['divisions'][0]
team0_division0 = division0['teams'][0]

team0_division0

def process_team(team):
    dict_to_return = {}

    dict_to_return['team_id'] = team['id']
    dict_to_return['owner_id'] = team['owners'][0]['id']
    dict_to_return['owner_name'] = team['owners'][0]['displayName']

    return dict_to_return

# works on one team
process_team(team0_division0)

def teams_from_div(division):
    return DataFrame([process_team(x) for x in division['teams']])

teams_from_div(division0)

# now let's put inside function to get all teams from all divisions
def divs_from_league(divisions):
    return pd.concat([teams_from_div(division) for division in divisions],
                     ignore_index=True)

divs_from_league(teams_json['divisions'])

# basically what we want, now let's put everything into a function that takes
# league, year and returns all teams, owners, divisions they're in

def get_teams_in_league(league_id):
    teams_url = ('https://www.fleaflicker.com/api/FetchLeagueStandings?' +
                f'leagueId={league_id}')

    teams_json = requests.get(teams_url).json()

    teams_df = divs_from_league(teams_json['divisions'])
    teams_df['league_id'] = league_id
    return teams_df

if USE_SAVED_DATA:
    league_teams = pd.read_csv('./projects/integration/raw/fleaflicker/league_teams.csv')
else:
    league_teams = get_teams_in_league(LEAGUE_ID)

league_teams

###############################################################################
# combining teams + roster functions
###############################################################################

def get_league_rosters(lookup, league_id):
    teams = get_teams_in_league(league_id)

    league_rosters = pd.concat(
        [get_team_roster(x, league_id, lookup) for x in
            teams['team_id']],
        ignore_index=True)
    return league_rosters

if USE_SAVED_DATA:
    league_rosters = pd.read_csv('./projects/integration/raw/fleaflicker/league_rosters.csv')
else:
    league_rosters = get_league_rosters(fantasymath_players, LEAGUE_ID)

league_rosters.sample(20)

###############################################################################
# schedule
###############################################################################

schedule_url = (
    'https://www.fleaflicker.com/api/FetchLeagueScoreboard?' +
    f'leagueId={LEAGUE_ID}&scoringPeriod={WEEK}&season={SEASON}')

# saved data
if USE_SAVED_DATA:
    with open('./projects/integration/raw/fleaflicker/schedule.json') as f:
        schedule_json = json.load(f)
else:
    schedule_json = requests.get(schedule_url).json()

matchup_list = schedule_json['games']
matchup0 = matchup_list[0]

# basic: just need team info
def process_matchup(game):
    return_dict = {}
    return_dict['team1_id'] = game['home']['id']
    return_dict['team2_id'] = game['away']['id']
    return_dict['game_id'] = game['id']
    return return_dict

process_matchup(matchup0)

# let's just do our usual, wrap it in a function that takes league_id, season,
# week and returns a dataframe

def get_schedule_by_week(league_id, week):
    schedule_url = (
        'https://www.fleaflicker.com/api/FetchLeagueScoreboard?' +
        f'leagueId={LEAGUE_ID}&scoringPeriod={WEEK}&season={SEASON}')

    schedule_json = requests.get(schedule_url).json()

    matchup_df = DataFrame([process_matchup(x) for x in schedule_json['games']])
    matchup_df['season'] = SEASON
    matchup_df['week'] = week
    matchup_df['league_id'] = league_id
    return matchup_df

if USE_SAVED_DATA:
    sched_w2 = pd.read_csv('./projects/integration/raw/fleaflicker/sched_w2.csv')
else:
    sched_w2 = get_schedule_by_week(LEAGUE_ID, 2)

# now let's do for entire season
def get_league_schedule(league_id):
    return pd.concat([get_schedule_by_week(league_id, week) for week in
                      range(1, 15)], ignore_index=True)

if USE_SAVED_DATA:
    league_schedule = pd.read_csv('./projects/integration/raw/fleaflicker/league_schedule.csv')
else:
    league_schedule = get_league_schedule(LEAGUE_ID)

league_schedule.head()

################################################################################
################################################################################

## note: this part isn't meant to be run
## i (nate) am running this Friday 9/15/23 - after PHI beat MIN last night - to
## save data we'll load above
## 
## including here to make it clearer this saved data just comes from APIs

########################################
## get data from Fleaflicker and FM apis
########################################

#LEAGUE_ID = 316893
#TEAM_ID = 1605156
#WEEK = 2
#SEASON = 2023

#roster_url = ('https://www.fleaflicker.com/api/FetchRoster?' +
#              f'leagueId={LEAGUE_ID}&teamId={TEAM_ID}')

#teams_url = ('https://www.fleaflicker.com/api/FetchLeagueStandings?' +
#             f'leagueId={LEAGUE_ID}')

#schedule_url = (
#    'https://www.fleaflicker.com/api/FetchLeagueScoreboard?' +
#    f'leagueId={LEAGUE_ID}&scoringPeriod={WEEK}&season={SEASON}')

#token = generate_token(LICENSE_KEY)['token']

## player_dict = points_json['fantasy_content']['team'][1]['players']
## player_dict['9']

#roster_json = requests.get(roster_url).json()
#teams_json = requests.get(teams_url).json()
#schedule_json = requests.get(schedule_url).json()
#fantasymath_players = master_player_lookup(token)
#my_roster = get_team_roster(TEAM_ID, LEAGUE_ID, fantasymath_players)
#league_rosters = get_league_rosters(fantasymath_players, LEAGUE_ID)
#league_teams = get_teams_in_league(LEAGUE_ID)
#sched_w2 = get_schedule_by_week(LEAGUE_ID, 2)
#league_schedule = get_league_schedule(LEAGUE_ID)

##############
## now save it
##############

#with open('./projects/integration/raw/fleaflicker/roster.json', 'w') as f:
#    json.dump(roster_json, f)

#with open('./projects/integration/raw/fleaflicker/teams.json', 'w') as f:
#    json.dump(teams_json, f)

#with open('./projects/integration/raw/fleaflicker/schedule.json', 'w') as f:
#    json.dump(schedule_json, f)

#fantasymath_players.to_csv('./projects/integration/raw/fleaflicker/lookup.csv', index=False)
#my_roster.to_csv('./projects/integration/raw/fleaflicker/my_roster.csv', index=False)
#league_rosters.to_csv('./projects/integration/raw/fleaflicker/league_rosters.csv', index=False)
#league_teams.to_csv('./projects/integration/raw/fleaflicker/league_teams.csv', index=False)
#sched_w2.to_csv('./projects/integration/raw/fleaflicker/sched_w2.csv', index=False)
#league_schedule.to_csv('./projects/integration/raw/fleaflicker/league_schedule.csv', index=False)
