import requests
import json
import numpy as np
from pandas import DataFrame, Series
import pandas as pd
from utilities import (LICENSE_KEY, generate_token, master_player_lookup, SEASON)
pd.options.mode.chained_assignment = None

######################
# top level functions:
######################
def get_league_rosters(lookup, league_id, week):
    matchup_url = f'https://api.sleeper.app/v1/league/{league_id}/matchups/{week}'
    matchup_json = requests.get(matchup_url).json()

    settings_url = f'https://api.sleeper.app/v1/league/{league_id}'
    settings_json = requests.get(settings_url).json()

    roster_url = f'https://api.sleeper.app/v1/league/{league_id}/rosters'
    roster_json = requests.get(roster_url).json()

    rteams = DataFrame([_roster_team_lookup(x) for x in roster_json])

    roster_df = pd.concat([_get_team_roster(
        m, lookup, settings_json['roster_positions'], r['starters'])
        for m, r in zip(matchup_json, roster_json)], ignore_index=True)

    roster_df = (pd.merge(roster_df, rteams, how='left').drop('roster_id', axis=1))
    return roster_df

    # add in team ids


def get_teams_in_league(league_id, example=False):
    teams_url = f'https://api.sleeper.app/v1/league/{league_id}/users'
    if example:
        with open('./projects/integration/raw/sleeper/teams.json') as f:
            teams_json = json.load(f)
    else:
        teams_json = requests.get(teams_url).json()

    all_teams = DataFrame(
        [_proc_team(team) for team in teams_json])
    all_teams['league_id'] = league_id
    return all_teams

def get_league_schedule(league_id, example=False):
    if example:
        return pd.read_csv('./projects/integration/raw/sleeper/schedule.csv')

    settings_url = f'https://api.sleeper.app/v1/league/{league_id}'
    settings_json = requests.get(settings_url).json()

    roster_url = f'https://api.sleeper.app/v1/league/{league_id}/rosters'
    roster_json = requests.get(roster_url).json()

    n = settings_json['settings']['playoff_week_start']
    if n == 0:
        n = 19
    return pd.concat(
        [_get_schedule_by_week(league_id, x) for x in range(1, n)], ignore_index=True)

##################
# helper functions
##################

def _get_team_roster(team, lookup, positions, rstarters=None):
    # starters
    if team['starters'] is None:
        starters = Series(rstarters).to_frame('sleeper_id')
        starter_points = [0 for x in rstarters]
    else:
        starters = Series(team['starters']).to_frame('sleeper_id')
        starter_points = team['starters_points']

    starters_w_info = pd.merge(starters, lookup, how='left')
    starters_w_info['actual'] = starter_points
    starters_w_info.loc[starters_w_info['actual'] == 0, 'actual'] = np.nan
    starters_w_info['team_position'] = [x for x in positions if x != 'BN']

    starters_pos = pd.concat([
        _add_pos_suffix(starters_w_info.query(f"team_position == '{x}'"))
        for x in starters_w_info['team_position'].unique()])

    players = Series(team['players']).to_frame('sleeper_id')
    players_w_info = pd.merge(players, lookup, how='left')

    players_w_info['actual'] = (
        players_w_info['sleeper_id'].replace(team['players_points']))

    bench_players = set(team['players']) - set(starters['sleeper_id'])

    bench_df = players_w_info.query(f"sleeper_id in {tuple(bench_players)}")
    bench_df['team_position'] = 'BN'
    bench_df.loc[bench_df['actual'] == 0, 'actual'] = np.nan

    team_df = pd.concat([starters_pos, bench_df], ignore_index=True)
    team_df.drop(['yahoo_id', 'espn_id', 'fleaflicker_id', 'sleeper_id'], axis=1,
                inplace=True)
    team_df.rename(columns={'pos': 'player_position'}, inplace=True)
    team_df['start'] = team_df['team_position'] != 'BN'
    # team_df['name'] = team_df['player_id'].str.replace('-', ' ').str.title()
    team_df['roster_id'] = team['roster_id']
    return team_df

def _get_schedule_by_week(league_id, week):
    matchup_url = f'https://api.sleeper.app/v1/league/{league_id}/matchups/{week}'
    matchup_json = requests.get(matchup_url).json()

    roster_url = f'https://api.sleeper.app/v1/league/{league_id}/rosters'
    roster_json = requests.get(roster_url).json()

    team_sched = DataFrame([_proc_team_schedule(team) for team in matchup_json])

    rteams = DataFrame([_roster_team_lookup(x) for x in roster_json])
    team_sched = pd.merge(team_sched, rteams).drop('roster_id', axis=1)

    team_sched_wide = pd.merge(
        team_sched.drop_duplicates('matchup_id', keep='first'),
        team_sched.drop_duplicates('matchup_id', keep='last'), on='matchup_id')

    team_sched_wide.rename(
        columns={'team_id_x': 'team1_id', 'team_id_y': 'team2_id'},
        inplace=True)

    team_sched_wide['season'] = SEASON
    team_sched_wide['week'] = week
    team_sched_wide['league_id'] = league_id
    return team_sched_wide

def _add_pos_suffix(df_subset):
    if len(df_subset) > 1:
        suffix = Series(range(1, len(df_subset) + 1), index=df_subset.index)

        df_subset['team_position'] = df_subset['team_position'] + suffix.astype(str)
    return df_subset

def _proc_team(team):
    dict_to_return = {}

    dict_to_return['owner_id'] = team['user_id']
    dict_to_return['owner_name'] = team['display_name']
    dict_to_return['team_id'] = team['user_id']
    return dict_to_return

def _proc_team_schedule(team):
    dict_to_return = {}
    dict_to_return['roster_id'] = team['roster_id']
    dict_to_return['matchup_id'] = team['matchup_id']
    return dict_to_return

def _roster_team_lookup(roster):
    return {'roster_id': roster['roster_id'], 'team_id': int(roster['owner_id'])}

if __name__ == '__main__':
    league_id = 1002102487509295104
    week = 2

    token = generate_token(LICENSE_KEY)['token']
    lookup = master_player_lookup(token)

    teams = get_teams_in_league(league_id)
    schedule = get_league_schedule(league_id)
    rosters = get_league_rosters(lookup, league_id, week)
