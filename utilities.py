from pandas import DataFrame, Series
import numpy as np
import os
from textwrap import dedent
import pandas as pd
import json
from textwrap import dedent
import requests
from configparser import ConfigParser
from pathlib import Path

config = ConfigParser(interpolation=None)
config.read('config.ini')

################################################################################
# shouldn't have to change anything in this file
# this file reads your config.ini and assigns values based on that
# do not edit them here
################################################################################

# constants - mostly loaded from config.ini - shouldn't need to change
# if not working make sure you have config.ini set up
API_URL = 'https://api.sims.fantasymath.com'
SEASON = 2024

if not Path('config.ini').is_file():
    print(dedent(f"""
    You don't have config.ini in your current working directory.

    See the Prerequisites: Tooling section of the book.

    Your current working directory is:
    {os.getcwd()}

    And the files in it are:
    {os.listdir()}
    """))

LICENSE_KEY = config['sdk']['LICENSE_KEY']
OUTPUT_PATH = config['sdk']['OUTPUT_PATH']
DB_PATH = config['sdk']['DB_PATH']

# league integration
# yahoo
YAHOO_FILE = config['yahoo']['FILE']
YAHOO_KEY =  config['yahoo']['KEY']
YAHOO_SECRET = config['yahoo']['SECRET']

YAHOO_GAME_ID = 449  # changes every year - 449 for 2024
# endpoint to find YAHOO_GAME_ID:
# 'https://fantasysports.yahooapis.com/fantasy/v2/game/nfl'
# (need to query through yahoo oauth)

# espn
SWID = config['espn']['SWID']
ESPN_S2 = config['espn']['ESPN_S2']

################################################################################
# auth functions
################################################################################

def generate_token(license):
    """
    Given some license key, validates it with the API endpoint, and — if
    successfully validated — returns an access token good for 24 hours.
    """
    query_token = dedent(
        f"""
        query {{
            token (license: "{license}") {{
                success,
                message,
                token
            }}
            }}
        """)

    r = requests.post(API_URL, json={'query': query_token})
    return json.loads(r.text)['data']['token']

def validate(token):
    """
    Can use this function to test whether your access token is working
    correctly.
    """
    query_validate = ("""
                      query {
                        validate {
                            validated,
                            message
                        }
                      }
                      """)

    r = requests.post(API_URL, json={'query': query_validate},
                  headers={'Authorization': f'Bearer {token}'})
    return json.loads(r.text)['data']

################################################################################
# player functions
################################################################################

def master_player_lookup(token):
    query_players = """
        query {
            players {
                name,
                player_id,
                pos,
                fleaflicker_id,
                espn_id,
                yahoo_id,
                sleeper_id
            }
        }
        """

    r = requests.post(API_URL, json={'query': query_players},
                  headers={'Authorization': f'Bearer {token}'})

    raw = json.loads(r.text)['data']

    if raw is None:
        print("Something went wrong. No data.")
        return DataFrame()
    else:
        return DataFrame(raw['players'])


def get_players(token,  qb='pass_6', skill='ppr_1', dst='dst_std', week=None,
                season=None):

    _check_arg('qb scoring', qb, ['pass_6', 'pass_4'])
    _check_arg('rb/wr/te scoring', skill, ['ppr_1', 'ppr_0', 'ppr_1over2'])
    _check_arg('dst scoring', dst, ['dst_high', 'dst_std'])

    arg_string = f'qb: "{qb}", skill: "{skill}", dst: "{dst}"'

    variables = ['player_id', 'name', 'pos', 'fleaflicker_id', 'espn_id',
                 'yahoo_id', 'sleeper_id', 'team']

    if (week is not None) and (season is not None):
        arg_string = arg_string + f', season: {season}, week: {week}'
        variables = variables + ['actual']

    query_available = dedent(
        f"""
        query {{
            available({arg_string}) {{
                {','.join(variables)}
            }}
        }}
        """)

    r = requests.post(API_URL, json={'query': query_available},
                  headers={'Authorization': f'Bearer {token}'})

    raw = json.loads(r.text)['data']

    if raw is None:
        print("Something went wrong. No data.")
        return DataFrame()
    else:
        return DataFrame(raw['available'])


def _check_arg(name, arg, allowed, none_ok=False):
    """
    Helper function to make sure argument is allowed.
    """
    if not ((arg in allowed) or (none_ok and arg is None)):
        raise ValueError(f"Invalid {name} argument. Needs to be in {allowed}.")

def remaining_teams_this_week(token):
    query = f"""
        query {{
            remaining_teams_this_week 
        }}
        """

    r = requests.post(API_URL, json={'query': query},
                  headers={'Authorization': f'Bearer {token}'})
    raw = json.loads(r.text)['data']

    if raw is None:
        print("No data. Check token.")
        return []

    return raw['remaining_teams_this_week']


def get_sims_from_roster(token, rosters, nsims=100, **kwargs):
    """
    Takes a league roster input, which is a DataFrame with player_id + any
    points scored so far (if running midweek).

    Uses that to get sims for players yet to to play. Adds in players actual
    scores if they played.
    """

    # teams still to play
    teams_to_play = remaining_teams_this_week(token)

    # add in team to rosters
    # available players (need this because it has team)
    players = get_players(token, **kwargs).set_index('player_id')
    rosters = pd.merge(rosters, players[['team']].reset_index(), how='left',
                       indicator=True)

    # print a warning for anyone in rosters that isn't available
    if (rosters['_merge'] == 'left_only').any():
        print("No sims available for:")
        print(rosters.query("_merge == 'left_only'"))

    rosters.drop('_merge', axis=1, inplace=True)

    # now get sims for players who have yet to play

    played = rosters['team'].apply(lambda x: x not in teams_to_play)
    players_to_get = list(rosters.loc[~played, 'player_id'])

    if len(players_to_get) == 0:
        sims = DataFrame(columns=list(rosters['player_id']), index=range(nsims))
    else:
        sims = get_sims(token, players_to_get, nsims=nsims, **kwargs)

    # add in any actual scores
    for i, row in rosters.set_index('player_id').iterrows():
        if i in players_to_get:
            continue
        else:
            if pd.isna(row['actual']):
                sims[i] = 0
            else:
                sims[i] = row['actual']

    return sims

def get_sims(token, players, qb='pass_6', skill='ppr_1', dst='dst_std',
             nsims=100, week=None, season=None):

    ###########################
    # check for valid arguments
    ###########################
    _check_arg('week', week, range(1, 19), none_ok=True)
    _check_arg('season', season, range(2020, 2024), none_ok=True)
    _check_arg('qb scoring', qb, ['pass_6', 'pass_4'])
    _check_arg('rb/wr/te scoring', skill, ['ppr_1', 'ppr_0', 'ppr_1over2'])
    _check_arg('dst scoring', dst, ['dst_high', 'dst_std'])

    player_str = ','.join([f'"{x}"' for x in players])

    arg_string = f'qb: "{qb}", skill: "{skill}", dst: "{dst}", nsims: {nsims}, player_ids: [{player_str}]'

    if (week is not None) and (season is not None):
        arg_string = arg_string + f', season: {season}, week: {week}'

    query = f"""
        query {{
            sims({arg_string}) {{
                players {{
                    player_id
                    sims
                }}
            }}
        }}
        """

    # send request
    r = requests.post(API_URL, json={'query': query},
                  headers={'Authorization': f'Bearer {token}'})
    raw = json.loads(r.text)['data']

    if raw is None:
        print("No data. Check token.")
        return DataFrame()

    return pd.concat([Series(x['sims']).to_frame(x['player_id']) for x in
        raw['sims']['players']], axis=1)

def get_sims_from_file(filename):
    sims = pd.read_csv(filename)
    sims.columns = [int(x) for x in sims.columns]
    return sims

def name_sims(sims, players):
    if 'player_id' in players.columns:
        players = players.set_index('player_id').copy()
    sims = DataFrame(sims, copy=True)
    sims.columns = list(players.loc[sims.columns, 'name']
                        .str.lower()
                        .str.replace('.','', regex=False)
                        .str.replace(' ', '-', regex=False))
    return sims

# misc helper

def schedule_long(sched):
    sched1 = sched.rename(columns={'team1_id': 'team_id', 'team2_id':
                                      'opp_id'})
    sched2 = sched.rename(columns={'team2_id': 'team_id', 'team1_id':
                                      'opp_id'})
    return pd.concat([sched1, sched2], ignore_index=True)

def proc_roster_score(rosters, players, teams_to_play):
    rosters = pd.merge(rosters, players[['team']].reset_index(), how='left',
                       indicator=True)
    assert rosters['_merge'].eq('both').all()
    rosters.drop('_merge', axis=1, inplace=True)
    played = rosters['team'].apply(lambda x: x not in teams_to_play)
    rosters.loc[played & rosters['actual'].isna(), 'actual'] = 0
    rosters.loc[~played, 'actual'] = np.nan

    return rosters

def update_sims_with_actual(sims, rosters):
    players_w_pts = rosters.query("actual.notnull()")
    for player, pts in zip(players_w_pts['player_id'], players_w_pts['actual']):
        sims[player] = pts
    return sims

if __name__ == '__main__':
    # generate access token
    token = generate_token(LICENSE_KEY)['token']
    token

    # validate it
    validate(token)

    # GraphQL
    # raw graphql example

    QUERY_STR = """
        query {
            available (season: 2024, week: 1) {
                player_id,
                name,
                pos,
                actual
            }
        }
        """

    r = requests.post(API_URL, json={'query': QUERY_STR},
                    headers={'Authorization': f'Bearer {token}'})
    df = DataFrame(json.loads(r.text)['data']['available'])
    df.head()
