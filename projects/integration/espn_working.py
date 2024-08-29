import requests
from pandas import DataFrame, Series
import pandas as pd
from utilities import (LICENSE_KEY, generate_token, master_player_lookup, SWID,
                       ESPN_S2, SEASON)
import json

pd.options.mode.chained_assignment = None


############
# parameters
############

# LEAGUE_ID = 242906
LEAGUE_ID = 395209553
TEAM_ID = 12
USE_SAVED_DATA = True
WEEK = 2

###############################################################################
# roster data
###############################################################################
roster_url = (f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}' +
              f'/segments/0/leagues/{LEAGUE_ID}?view=mRoster')

# saved data
if USE_SAVED_DATA:
    with open('./projects/integration/raw/espn/roster.json') as f:
        roster_json = json.load(f)
else:
    roster_json = requests.get(roster_url, cookies={'swid': SWID, 'espn_s2':
                                                    ESPN_S2}).json()

list_of_rosters = roster_json['teams']

roster0 = list_of_rosters[0]
roster0

list_of_players_on_roster0 = roster0['roster']['entries']
roster0_player0 = list_of_players_on_roster0[0]
roster0_player0.keys()

def process_player1(player):
    dict_to_return = {}
    dict_to_return['team_position'] = player['lineupSlotId']
    dict_to_return['espn_id'] = player['playerId']

    dict_to_return['name'] = player['playerPoolEntry']['player']['fullName']
    dict_to_return['player_position'] = player['playerPoolEntry']['player']['defaultPositionId']
    return dict_to_return

process_player1(roster0_player0)

TEAM_POSITION_MAP = {
    0: 'QB', 1: 'TQB', 2: 'RB', 3: 'RB/WR', 4: 'WR', 5: 'WR/TE',
    6: 'TE', 7: 'OP', 8: 'DT', 9: 'DE', 10: 'LB', 11: 'DL',
    12: 'CB', 13: 'S', 14: 'DB', 15: 'DP', 16: 'D/ST', 17: 'K',
    18: 'P', 19: 'HC', 20: 'BE', 21: 'IR', 22: '', 23: 'RB/WR/TE',
    24: 'ER', 25: 'Rookie', 'QB': 0, 'RB': 2, 'WR': 4, 'TE': 6,
    'D/ST': 16, 'K': 17, 'FLEX': 23, 'DT': 8, 'DE': 9, 'LB': 10,
    'DL': 11, 'CB': 12, 'S': 13, 'DB': 14, 'DP': 15, 'HC': 19
}

PLAYER_POSITION_MAP = {1: 'QB', 2: 'RB', 3: 'WR', 4: 'TE', 5: 'K', 16: 'D/ST'}

def process_player2(player):
    dict_to_return = {}
    dict_to_return['team_position'] = TEAM_POSITION_MAP[player['lineupSlotId']]
    dict_to_return['espn_id'] = player['playerId']

    dict_to_return['name'] = player['playerPoolEntry']['player']['fullName']
    dict_to_return['player_position'] = (
        PLAYER_POSITION_MAP[
            player['playerPoolEntry']['player']['defaultPositionId']])
    return dict_to_return

[process_player2(x) for x in list_of_players_on_roster0]

roster0_df = DataFrame([process_player2(x) for x in
                        list_of_players_on_roster0])

roster0_df

# handling duplicate team_position
wrs = roster0_df.query("team_position == 'WR'")
wrs

suffix = Series(range(1, len(wrs) + 1), index=wrs.index)
suffix

wrs['team_position'] + suffix.astype(str)

def add_pos_suffix(df_subset):
    # only add if more than one position -- want just K, not K1
    if len(df_subset) > 1:
        suffix = Series(range(1, len(df_subset) + 1), index=df_subset.index)

        df_subset['team_position'] = df_subset['team_position'] + suffix.astype(str)
    return df_subset

roster0_df2 = pd.concat([
    add_pos_suffix(roster0_df.query(f"team_position == '{x}'"))
    for x in roster0_df['team_position'].unique()])

roster0_df2

roster0_df2['start'] = ~roster0_df2['team_position'].str.startswith('BE')
roster0_df2

def process_players(entries):
    roster_df = DataFrame([process_player2(x) for x in entries])

    roster_df2 = pd.concat([
        add_pos_suffix(roster_df.query(f"team_position == '{x}'"))
        for x in roster_df['team_position'].unique()])

    roster_df2['start'] = ~roster_df2['team_position'].str.startswith('BE')

    return roster_df2

process_players(list_of_players_on_roster0)

roster1 = list_of_rosters[1]

roster1['id']
process_players(roster1['roster']['entries']).head()

def process_roster(team):
    roster_df = process_players(team['roster']['entries'])
    roster_df['team_id'] = team['id']
    return roster_df

roster3 = list_of_rosters[3]
process_roster(roster3).head()


all_rosters = pd.concat([process_roster(x) for x in list_of_rosters],
                        ignore_index=True)
all_rosters.sample(15)


# this saved data we're using is from Friday, Week 2, 2023
# AFTER PHI-MIN already played
# so want to grab those actual scores too

boxscore_url = (f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}' +
                f'/segments/0/leagues/{LEAGUE_ID}?view=mBoxscore')


# saved data
if USE_SAVED_DATA:
    with open('./projects/integration/raw/espn/boxscore.json') as f:
        boxscore_json = json.load(f)
else:
    boxscore_json = requests.get(boxscore_url, cookies={'swid': SWID, 'espn_s2':
                                                        ESPN_S2}).json()

# only week 2 matchups
matchup_list = [x for x in boxscore_json['schedule']
                if x['matchupPeriodId'] == WEEK]

matchup0 = matchup_list[0]
matchup0_away = matchup0['away']
matchup0_away_roster = matchup0['away']['rosterForMatchupPeriod']['entries']
cousins_dict = matchup0_away_roster[0]

cousins_dict

def proc_played_player(player):
    dict_to_return = {}
    dict_to_return['espn_id'] = player['playerId']

    dict_to_return['actual'] = (player['playerPoolEntry']
        ['player']['stats'][0]['appliedTotal'])
    return dict_to_return

proc_played_player(cousins_dict)

def proc_played_team(team):
    if 'rosterForMatchupPeriod' in team.keys():
        return DataFrame([proc_played_player(x) for x in
                          team['rosterForMatchupPeriod']['entries']])
    else:
        return DataFrame()

matchup2 = matchup_list[2]
matchup2_home = matchup2['home']

proc_played_team(matchup2_home)

def proc_played_matchup(matchup):
    return pd.concat([proc_played_team(matchup['home']),
                      proc_played_team(matchup['away'])],
                     ignore_index=True)

proc_played_matchup(matchup0)
proc_played_matchup(matchup2)

scores = pd.concat([proc_played_matchup(x) for x in matchup_list])
scores

# fix:
# doesn't work if scores is empty (e.g. it's tue-wed and no one has played yet)
# so in that case make an empty dataframe
if scores.empty:
    scores = DataFrame(columns=['espn_id', 'actual'])

all_rosters_w_pts = pd.merge(all_rosters, scores, how='left')
all_rosters_w_pts.head(15)

from utilities import (LICENSE_KEY, generate_token, master_player_lookup)

if USE_SAVED_DATA:
    fantasymath_players = pd.read_csv('./projects/integration/raw/espn/lookup.csv')
else:
    token = generate_token(LICENSE_KEY)['token']
    fantasymath_players = master_player_lookup(token)

fantasymath_players.head()

all_rosters_w_id = pd.merge(
    all_rosters_w_pts,
    fantasymath_players[['player_id', 'espn_id']],
    how='left')

all_rosters_final = all_rosters_w_id.drop('espn_id', axis=1)
all_rosters_final.sample(10)

def get_league_rosters(lookup, league_id, week):
    roster_url = (f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}' +
                  f'/segments/0/leagues/{league_id}?view=mRoster')

    roster_json = requests.get(
        roster_url,
        cookies={'swid': SWID, 'espn_s2': ESPN_S2}).json()

    all_rosters = pd.concat([process_roster(x) for x in roster_json['teams']],
                            ignore_index=True)

    # score part
    boxscore_url = (
        f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}' +
            f'/segments/0/leagues/{league_id}?view=mBoxscore')
    boxscore_json = requests.get(
        boxscore_url,
        cookies={'swid': SWID, 'espn_s2': ESPN_S2}).json()


    matchup_list = [x for x in boxscore_json['schedule'] if
        x['matchupPeriodId'] == week]
    scores = pd.concat([proc_played_matchup(x) for x in matchup_list])

    all_rosters = pd.merge(all_rosters, scores, how='left')


    all_rosters_w_id = pd.merge(all_rosters,
                                lookup[['player_id', 'espn_id']],
                                how='left').drop('espn_id', axis=1)

    return all_rosters_w_id

if USE_SAVED_DATA:
    complete_league_rosters = pd.read_csv('./projects/integration/raw/espn/complete_league_rosters.csv')
else:
    complete_league_rosters = get_league_rosters(fantasymath_players, LEAGUE_ID, 2)

complete_league_rosters.head(10)

###############################################################################
# team data
###############################################################################

teams_url = (f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}' +
             f'/segments/0/leagues/{LEAGUE_ID}?view=mTeam')

if USE_SAVED_DATA:
    with open('./projects/integration/raw/espn/teams.json') as f:
        teams_json = json.load(f)
else:
    teams_json = requests.get(teams_url, cookies={'swid': SWID, 'espn_s2':
                                                  ESPN_S2}).json()


teams_list = teams_json['teams']
members_list = teams_json['members']

def process_team(team):
    dict_to_return = {}
    dict_to_return['team_id'] = team['id']
    dict_to_return['owner_id'] = team['owners'][0]
    return dict_to_return

def process_member(member):
    dict_to_return = {}
    dict_to_return['owner_id'] = member['id']
    dict_to_return['owner_name'] = (member['firstName'] + ' ' + member['lastName'][0]).title()
    return dict_to_return

DataFrame([process_team(team) for team in teams_list])
DataFrame([process_member(member) for member in members_list])

def get_teams_in_league(league_id):
    teams_url = (
        f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}' +
            f'/segments/0/leagues/{league_id}?view=mTeam')

    teams_json = requests.get(
        teams_url, cookies={'swid': SWID, 'espn_s2': ESPN_S2}).json()

    teams_list = teams_json['teams']
    members_list = teams_json['members']

    teams_df = DataFrame([process_team(team) for team in teams_list])
    member_df = DataFrame([process_member(member) for member in members_list])

    comb = pd.merge(teams_df, member_df)
    comb['league_id'] = league_id

    return comb

if USE_SAVED_DATA:
    league_teams = pd.read_csv('./projects/integration/raw/espn/league_teams.csv')
else:
    league_teams = get_teams_in_league(LEAGUE_ID)

###############################################################################
# schedule
###############################################################################

schedule_url = (
    f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}' +
        f'/segments/0/leagues/{LEAGUE_ID}?view=mBoxscore')

if USE_SAVED_DATA:
    schedule_json = requests.get(schedule_url,
                                 cookies={'swid': SWID, 'espn_s2': ESPN_S2}
                                 ).json()
else:
    with open('./projects/integration/raw/espn/schedule.json') as f:
        schedule_json = json.load(f)

matchup_list = schedule_json['schedule']

matchup0 = matchup_list[0]

matchup0['id']  # matchup_id
matchup0['home']['teamId']  # "home" team_id
matchup0['away']['teamId']  # "away" team_id
matchup0['matchupPeriodId'] # week

def process_matchup(matchup):
    dict_to_return = {}

    dict_to_return['matchup_id'] = matchup['id']  # matchup_id
    dict_to_return['home_id'] = matchup['home']['teamId']  # "home" team_id
    dict_to_return['away_id'] = matchup['away']['teamId']  # "away" team_id
    dict_to_return['week'] = matchup['matchupPeriodId'] # week

    return dict_to_return

matchup_df = DataFrame([process_matchup(matchup) for matchup in matchup_list])
matchup_df.head(10)

def get_league_schedule(league_id):
    schedule_url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}/segments/0/leagues/{LEAGUE_ID}?view=mBoxscore'

    schedule_json = requests.get(
        schedule_url,
        cookies={'swid': SWID, 'espn_s2': ESPN_S2}).json()

    matchup_list = schedule_json['schedule']

    matchup_df = DataFrame([process_matchup(matchup) for matchup in matchup_list])
    matchup_df['league_id'] = league_id
    matchup_df['season'] = SEASON
    matchup_df.rename(columns={'home_id': 'team1_id', 'away_id': 'team2_id'},
                      inplace=True)
    return matchup_df

if USE_SAVED_DATA:
    league_schedule = pd.read_csv('./projects/integration/raw/espn/league_schedule.csv')
else:
    league_schedule = get_league_schedule(LEAGUE_ID)
league_schedule.head()

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
#roster_url = (f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}' +
#              f'/segments/0/leagues/{LEAGUE_ID}?view=mRoster')

#boxscore_url = (f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}' +
#                f'/segments/0/leagues/{LEAGUE_ID}?view=mBoxscore')

#teams_url = (f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}' +
#             f'/segments/0/leagues/{LEAGUE_ID}?view=mTeam')

#schedule_url = (
#    f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}' +
#        f'/segments/0/leagues/{LEAGUE_ID}?view=mBoxscore')

#roster_json = requests.get(roster_url, cookies={'swid': SWID, 'espn_s2':
#                                                ESPN_S2}).json()

#boxscore_json = requests.get(boxscore_url, cookies={'swid': SWID, 'espn_s2':
#                                                    ESPN_S2}).json()

#teams_json = requests.get(teams_url, cookies={'swid': SWID, 'espn_s2':
#                                              ESPN_S2}).json()

#schedule_json = requests.get(schedule_url, cookies={'swid': SWID, 'espn_s2':
#                                                    ESPN_S2}).json()

#token = generate_token(LICENSE_KEY)['token']
#fantasymath_players = master_player_lookup(token)
#complete_league_rosters = get_league_rosters(fantasymath_players, LEAGUE_ID, 2)
#league_teams = get_teams_in_league(LEAGUE_ID)
#league_schedule = get_league_schedule(LEAGUE_ID)

##############
## now save it
##############
#with open('./projects/integration/raw/espn/roster.json', 'w') as f:
#    json.dump(roster_json, f)

#with open('./projects/integration/raw/espn/boxscore.json', 'w') as f:
#    json.dump(boxscore_json, f)

#with open('./projects/integration/raw/espn/teams.json', 'w') as f:
#    json.dump(teams_json, f)

#with open('./projects/integration/raw/espn/schedule.json', 'w') as f:
#    json.dump(schedule_json, f)

#fantasymath_players.to_csv('./projects/integration/raw/espn/lookup.csv', index=False)
# complete_league_rosters.to_csv('./projects/integration/raw/espn/complete_league_rosters.csv', index=False)
#league_teams.to_csv('./projects/integration/raw/espn/league_teams.csv', index=False)
#league_schedule.to_csv('./projects/integration/raw/espn/league_schedule.csv', index=False)
