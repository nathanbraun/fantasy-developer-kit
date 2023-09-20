import requests
import numpy as np
from pandas import DataFrame, Series
import pandas as pd
from utilities import (LICENSE_KEY, generate_token, master_player_lookup,
    SEASON)

import json
pd.options.mode.chained_assignment = None

LEAGUE_ID = 1002102487509295104
WEEK = 2
USE_SAVED_DATA = True

roster_url = f'https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters'

if USE_SAVED_DATA:
    with open('./projects/integration/raw/sleeper/roster.json') as f:
        roster_json = json.load(f)
else:
    roster_json = requests.get(roster_url).json()

matchup_url = f'https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{WEEK}'

if USE_SAVED_DATA:
    with open('./projects/integration/raw/sleeper/matchup.json') as f:
        matchup_json = json.load(f)
else:
    matchup_json = requests.get(matchup_url).json()

team5 = matchup_json[5]
team5['starters']

settings_url = f'https://api.sleeper.app/v1/league/{LEAGUE_ID}'

if USE_SAVED_DATA:
    with open('./projects/integration/raw/sleeper/settings.json') as f:
        settings_json = json.load(f)
else:
    settings_json = requests.get(settings_url).json()

positions = settings_json['roster_positions']

positions

if USE_SAVED_DATA:
    fantasymath_players = pd.read_csv('./projects/integration/raw/sleeper/lookup.csv')
else:
    from utilities import (LICENSE_KEY, generate_token, master_player_lookup)
    token = generate_token(LICENSE_KEY)['token']
    fantasymath_players = master_player_lookup(token)

fantasymath_players.head()

starters5 = Series(team5['starters']).to_frame('sleeper_id')
starters5
type(starters5)

DataFrame([{'sleeper_id': x} for x in team5['starters']])

DataFrame(team5['starters'], columns=['sleeper_id'])

starters5_w_info = pd.merge(starters5, fantasymath_players[['sleeper_id', 'player_id', 'name', 'pos']], how='left')
starters5_w_info

starters5_w_info['actual'] = team5['starters_points']
starters5_w_info

starters5_w_info.loc[starters5_w_info['actual'] == 0, 'actual'] = np.nan
starters5_w_info

positions

starters5_w_info['team_position'] = [x for x in positions if x != 'BN']
starters5_w_info

wrs = starters5_w_info.query("team_position == 'WR'")
wrs

suffix = Series(range(1, len(wrs) + 1), index=wrs.index)
suffix

wrs['team_position'] + suffix.astype(str)

def add_pos_suffix(df_subset):
    if len(df_subset) > 1:
        suffix = Series(range(1, len(df_subset) + 1), index=df_subset.index)

        df_subset['team_position'] = df_subset['team_position'] + suffix.astype(str)
    return df_subset

starters5_pos = pd.concat([
    add_pos_suffix(starters5_w_info.query(f"team_position == '{x}'"))
    for x in starters5_w_info['team_position'].unique()])

starters5_pos

players5 = Series(team5['players']).to_frame('sleeper_id')
players5_w_info = pd.merge(players5, fantasymath_players, how='left')

players5_w_info

team5['players_points']

players5_w_info['actual'] = (
    players5_w_info['sleeper_id'].apply(lambda x: team5['players_points'][x]))

players5_w_info

bench_players = set(team5['players']) - set(team5['starters'])
bench_players

bench_df = players5_w_info.query(f"sleeper_id in {tuple(bench_players)}")
bench_df['team_position'] = 'BN'
bench_df.loc[bench_df['actual'] == 0, 'actual'] = np.nan
bench_df

team5_df = pd.concat([starters5_pos, bench_df], ignore_index=True)
team5_df.drop(['yahoo_id', 'espn_id', 'fleaflicker_id', 'sleeper_id'], axis=1,
              inplace=True)
team5_df.rename(columns={'position': 'player_position'}, inplace=True)
team5_df['start'] = team5_df['team_position'] != 'BN'
team5_df['team_id'] = team5['roster_id']
team5_df

def get_team_roster(team, lookup):
    # starters
    starters = Series(team['starters']).to_frame('sleeper_id')

    starters_w_info = pd.merge(starters, lookup, how='left')
    starters_w_info['actual'] = team['starters_points']
    starters_w_info.loc[starters_w_info['actual'] == 0, 'actual'] = np.nan
    starters_w_info['team_position'] = [x for x in positions if x != 'BN']

    starters_pos = pd.concat([
        add_pos_suffix(starters_w_info.query(f"team_position == '{x}'"))
        for x in starters_w_info['team_position'].unique()])

    players = Series(team['players']).to_frame('sleeper_id')
    players_w_info = pd.merge(players, fantasymath_players, how='left')

    players_w_info['actual'] = (
        players_w_info['sleeper_id'].replace(team['players_points']))

    bench_players = set(team['players']) - set(team['starters'])

    bench_df = players_w_info.query(f"sleeper_id in {tuple(bench_players)}")
    bench_df['team_position'] = 'BN'
    bench_df.loc[bench_df['actual'] == 0, 'actual'] = np.nan

    team_df = pd.concat([starters_pos, bench_df], ignore_index=True)
    team_df.drop(['yahoo_id', 'espn_id', 'fleaflicker_id', 'sleeper_id'], axis=1,
                inplace=True)
    team_df.rename(columns={'position': 'player_position'}, inplace=True)
    team_df['start'] = team_df['team_position'] != 'BN'
    # team_df['name'] = team_df['fantasymath_id'].str.replace('-', ' ').str.title()
    team_df['team_id'] = team['roster_id']
    return team_df

get_team_roster(matchup_json[0], fantasymath_players)

all_rosters = pd.concat([get_team_roster(x, fantasymath_players) for x in
                         matchup_json], ignore_index=True)

all_rosters.sample(10)

def get_league_rosters(lookup, league_id, week):
    matchup_url = f'https://api.sleeper.app/v1/league/{league_id}/matchups/{week}'
    matchup_json = requests.get(matchup_url).json()

    return pd.concat([get_team_roster(x, lookup) for x in
                      matchup_json], ignore_index=True)

if USE_SAVED_DATA:
    league_rosters = pd.read_csv('./projects/integration/raw/sleeper/league_rosters.csv')
else:
    league_rosters = get_league_rosters(fantasymath_players, LEAGUE_ID, 2)

# team info
teams_url = f'https://api.sleeper.app/v1/league/{LEAGUE_ID}/users'

if USE_SAVED_DATA:
    with open('./projects/integration/raw/sleeper/teams.json') as f:
        teams_json = json.load(f)
else:
    teams_json = requests.get(teams_url).json()

team1 = teams_json[1]

def proc_team1(team):
    dict_to_return = {}

    dict_to_return['owner_id'] = team['user_id']
    dict_to_return['owner_name'] = team['display_name']
    return dict_to_return

proc_team1(team1)

def proc_team2(team, team_id):
    dict_to_return = {}

    dict_to_return['owner_id'] = team['user_id']
    dict_to_return['owner_name'] = team['display_name']
    dict_to_return['team_id'] = team_id
    return dict_to_return

proc_team2(team1, 1)

for i, team in enumerate(teams_json, start=1):
    print(i)
    print(team['display_name'])

all_teams = DataFrame(
    [proc_team2(team, i) for i, team in enumerate(teams_json, start=1)])

all_teams

def get_teams_in_league(league_id):
    teams_url = f'https://api.sleeper.app/v1/league/{league_id}/users'
    teams_json = requests.get(teams_url).json()

    all_teams = DataFrame(
        [proc_team2(team, i) for i, team in enumerate(teams_json, start=1)])
    all_teams['league_id'] = league_id
    return all_teams

if USE_SAVED_DATA:
    league_teams = pd.read_csv('./projects/integration/raw/sleeper/league_teams.csv')
else:
    league_teams = get_teams_in_league(LEAGUE_ID)

league_teams

##################################
# schedule - batck to matchup_json
##################################
team0 = matchup_json[0]
team0

def proc_team_schedule(team):
    dict_to_return = {}
    dict_to_return['roster_id'] = team['roster_id']
    dict_to_return['game_id'] = team['matchup_id']
    return dict_to_return

proc_team_schedule(team0)

schedule_w2 = DataFrame([proc_team_schedule(team) for team in matchup_json])

schedule_w2

# problem ids ("roster_id") here aren't available all the time
# let's use owner ids instead
# that's available in rosters

roster0 = roster_json[0]

def roster_team_lookup(roster):
    return {'roster_id': roster['roster_id'], 'team_id': roster['owner_id']}

rteams = DataFrame([roster_team_lookup(x) for x in roster_json])
schedule_w2 = pd.merge(schedule_w2, rteams, on='roster_id')

schedule_w2_wide = pd.merge(
    schedule_w2.drop_duplicates('game_id', keep='first'),
    schedule_w2.drop_duplicates('game_id', keep='last'), on='game_id')

schedule_w2_wide

schedule_w2_wide.rename(
    columns={'team_id_x': 'team1_id', 'team_id_y': 'team2_id'}, inplace=True)

schedule_w2_wide['season'] = SEASON
schedule_w2_wide['week'] = WEEK

schedule_w2_wide

def get_schedule_by_week(league_id, week):
    matchup_url = f'https://api.sleeper.app/v1/league/{league_id}/matchups/{week}'
    matchup_json = requests.get(matchup_url).json()

    roster_url = f'https://api.sleeper.app/v1/league/{league_id}/rosters'
    roster_json = requests.get(roster_url).json()

    team_sched = DataFrame([proc_team_schedule(team) for team in matchup_json])

    rteams = DataFrame([roster_team_lookup(x) for x in roster_json])
    team_sched = pd.merge(team_sched, rteams).drop('roster_id', axis=1)

    team_sched_wide = pd.merge(
        team_sched.drop_duplicates('game_id', keep='first'),
        team_sched.drop_duplicates('game_id', keep='last'), on='game_id')

    team_sched_wide.rename(
        columns={'team_id_x': 'team1_id', 'team_id_y': 'team2_id'},
        inplace=True)

    team_sched_wide['season'] = SEASON
    team_sched_wide['week'] = week
    team_sched_wide['league_id'] = league_id
    return team_sched_wide

if USE_SAVED_DATA:
    sched_w3 = pd.read_csv('./projects/integration/raw/sleeper/schedule_w3.csv')
else:
    sched_w3 = get_schedule_by_week(LEAGUE_ID, 3)

sched_w3

settings_json['settings']['playoff_week_start']  # 0 since it's a best ball league

def get_league_schedule(league_id):
    settings_url = f'https://api.sleeper.app/v1/league/{league_id}'
    settings_json = requests.get(settings_url).json()

    n = settings_json['settings']['playoff_week_start']
    if n == 0:
        n = 19
    return pd.concat(
        [get_schedule_by_week(league_id, x) for x in range(1, n)], ignore_index=True)

if USE_SAVED_DATA:
    league_schedule = pd.read_csv('./projects/integration/raw/sleeper/league_schedule.csv')
else:
    league_schedule = get_league_schedule(LEAGUE_ID)

league_schedule

################################################################################
################################################################################

## note: this part isn't meant to be run
## i (NB) am running this Friday 9/15/23 - after PHI beat MIN last night - to
## save data we'll load above
## 
## including here to make it clearer this saved data just comes from APIs

##################################
## get data from ESPN and FM apis
##################################

#roster_url = f'https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters'
#matchup_url = f'https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{WEEK}'
#settings_url = f'https://api.sleeper.app/v1/league/{LEAGUE_ID}'
#teams_url = f'https://api.sleeper.app/v1/league/{LEAGUE_ID}/users'

#roster_json = requests.get(roster_url).json()
#matchup_json = requests.get(matchup_url).json()
#settings_json = requests.get(settings_url).json()
#teams_json = requests.get(teams_url).json()

#token = generate_token(LICENSE_KEY)['token']
#fantasymath_players = master_player_lookup(token)
#league_rosters = get_league_rosters(fantasymath_players, LEAGUE_ID, 2)
#league_teams = get_teams_in_league(LEAGUE_ID)
#sched_w3 = get_schedule_by_week(LEAGUE_ID, 3)
#league_schedule = get_league_schedule(LEAGUE_ID)

##############
## now save it
##############
#with open('./projects/integration/raw/sleeper/roster.json', 'w') as f:
#    json.dump(roster_json, f)

#with open('./projects/integration/raw/sleeper/matchup.json', 'w') as f:
#    json.dump(matchup_json, f)

#with open('./projects/integration/raw/sleeper/teams.json', 'w') as f:
#    json.dump(teams_json, f)

#with open('./projects/integration/raw/sleeper/settings.json', 'w') as f:
#    json.dump(settings_json, f)

#fantasymath_players.to_csv('./projects/integration/raw/sleeper/lookup.csv', index=False)
#league_rosters.to_csv('./projects/integration/raw/sleeper/league_rosters.csv', index=False)
#league_teams.to_csv('./projects/integration/raw/sleeper/league_teams.csv', index=False)
#sched_w3.to_csv('./projects/integration/raw/sleeper/schedule_w3.csv', index=False)
# league_schedule.to_csv('./projects/integration/raw/sleeper/league_schedule.csv', index=False)
