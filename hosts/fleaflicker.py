import requests
from pandas import DataFrame, Series
import pandas as pd
from utilities import (LICENSE_KEY, generate_token, master_player_lookup, SEASON)
import numpy as np
import json

pd.options.mode.chained_assignment = None

######################
# top level functions:
######################

def get_league_rosters(lookup, league_id, week=None, starting=True,
                       skip_kickers=False):
    teams = get_teams_in_league(league_id)

    league_rosters = pd.concat(
        [_get_team_roster(x, league_id, lookup) for x in teams['team_id']],
        ignore_index=True)

    if skip_kickers:
        league_rosters = league_rosters.query("team_position != 'K'")

    if starting:
        league_rosters = league_rosters.query("start")

    league_rosters['player_id'] = league_rosters['player_id'].astype(int)

    return league_rosters

def get_teams_in_league(league_id, example=False):
    teams_url = ('https://www.fleaflicker.com/api/FetchLeagueStandings?' +
                f'leagueId={league_id}')

    if example:
        with open('./projects/integration/raw/fleaflicker/teams.json') as f:
            teams_json = json.load(f)
    else:
        teams_json = requests.get(teams_url).json()

    teams_df = _divs_from_league(teams_json['divisions'])
    teams_df['league_id'] = league_id
    return teams_df

def get_league_schedule(league_id, example=False):
    if example:
        return pd.read_csv('./projects/integration/raw/fleaflicker/schedule.csv')
    else:
        return pd.concat([_get_schedule_by_week(league_id, week) for week in
                          range(1, 19)], ignore_index=True)

##################
# helper functions
##################

# roster helper functions
def _process_player(slot):
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

def _add_pos_suffix(df_subset):
    if len(df_subset) > 1:
        suffix = Series(range(1, len(df_subset) + 1), index=df_subset.index)

        df_subset['team_position'] = df_subset['team_position'] + suffix.astype(str)
    return df_subset

def _get_team_roster(team_id, league_id, lookup):
    roster_url = ('https://www.fleaflicker.com/api/FetchRoster?' +
        f'leagueId={league_id}&teamId={team_id}')

    roster_json = requests.get(roster_url).json()

    starter_slots = roster_json['groups'][0]['slots']
    bench_slots = roster_json['groups'][1]['slots']

    starter_df = DataFrame([_process_player(x) for x in starter_slots])
    bench_df = DataFrame([_process_player(x) for x in bench_slots])

    starter_df2 = pd.concat([
        _add_pos_suffix(starter_df.query(f"team_position == '{x}'"))
        for x in starter_df['team_position'].unique()])

    starter_df2['start'] = True
    bench_df['start'] = False

    team_df = pd.concat([starter_df2, bench_df], ignore_index=True)
    team_df['team_id'] = team_id

    team_df_w_id = pd.merge(team_df,
                            lookup[['player_id', 'fleaflicker_id']],
                            how='left').drop('fleaflicker_id', axis=1)

    if 'actual' not in team_df_w_id.columns:
        team_df_w_id['actual'] = np.nan

    team_df_w_id = team_df_w_id.query("player_position.notnull()")
    return team_df_w_id

# team helper functions

def _process_team(team):
    dict_to_return = {}

    dict_to_return['team_id'] = team['id']
    dict_to_return['owner_id'] = team['owners'][0]['id']
    dict_to_return['owner_name'] = team['owners'][0]['displayName']

    return dict_to_return

def _teams_from_div(division):
    return DataFrame([_process_team(x) for x in division['teams']])

def _divs_from_league(divisions):
    return pd.concat([_teams_from_div(division) for division in divisions],
                     ignore_index=True)

# schedule and matchup helper functions
def _process_matchup(game):
    return_dict = {}
    return_dict['team1_id'] = game['home']['id']
    return_dict['team2_id'] = game['away']['id']
    return_dict['matchup_id'] = game['id']
    return return_dict


def _get_schedule_by_week(league_id, week):
    schedule_url = (
        'https://www.fleaflicker.com/api/FetchLeagueScoreboard?' +
        f'leagueId={league_id}&scoringPeriod={week}&season={SEASON}')

    schedule_json = requests.get(schedule_url).json()

    try:
        matchup_df = DataFrame([_process_matchup(x) for x in schedule_json['games']])
        matchup_df['season'] = SEASON
        matchup_df['week'] = week
        matchup_df['league_id'] = league_id
    except KeyError:
        matchup_df = DataFrame()
    return matchup_df

if __name__ == '__main__':
    # test
    LEAGUE_ID = 316893

    token = generate_token(LICENSE_KEY)['token']
    lookup = master_player_lookup(token)

    teams = get_teams_in_league(LEAGUE_ID)
    schedule = get_league_schedule(LEAGUE_ID)
    rosters = get_league_rosters(lookup, LEAGUE_ID)
