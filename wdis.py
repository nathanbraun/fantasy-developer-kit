from hosts.league_setup import LEAGUES
from pandas import DataFrame
import hosts.db as db
from os import path
import datetime as dt
import sqlite3
import wdis_manual as wdis
import pandas as pd
from pathlib import Path
from os import path
from utilities import (LICENSE_KEY, generate_token, master_player_lookup,
    get_players, DB_PATH, OUTPUT_PATH, get_sims_from_roster, schedule_long)

#####################
# set parameters here
#####################
LEAGUE = 'nate-league'
WEEK = 1
WRITE_OUTPUT = False

##############################################
# shouldn't have to change anything below this
##############################################

def wdis_by_pos(pos, sims, roster, opponent_starters):
    wdis_options = wdis_options_by_pos(roster, pos)

    starters = list(roster.loc[roster['start'] &
                               roster['player_id'].notnull(),
                               'player_id'])

    df = wdis.calculate(sims, starters, opponent_starters, set(wdis_options) &
                        set(sims.columns))

    df['pos'] = pos
    df.index.name = 'player_id'
    df.reset_index(inplace=True)
    df.set_index(['pos', 'player_id'], inplace=True)

    # now update roster with start decisions
    current_starter = roster.loc[(roster['team_position'] == pos) &
        roster['start'], 'player_id'].iloc[0]
    recc_starter = df.xs(pos).index[0]

    if current_starter == recc_starter:
        return df, roster
    else:
        bench = roster.loc[(roster['player_id'] == recc_starter),
        'team_position'].iloc[0]

        roster.loc[(roster['player_id'] == current_starter), 'team_position'] = bench
        roster.loc[(roster['player_id'] == current_starter), 'start'] = False
        roster.loc[(roster['player_id'] == recc_starter), 'start'] = True
        roster.loc[(roster['player_id'] == recc_starter), 'team_position'] = pos

        return df, roster

# as always, let's put this in a function
def wdis_options_by_pos(roster, team_pos):
    is_wdis_elig = ((roster['player_position']
                    .astype(str)
                    .apply(lambda x: x in team_pos) & ~roster['start']) |
                    (roster['team_position'] == team_pos))

    return list(roster.loc[is_wdis_elig, 'player_id'])

def positions_from_roster(roster):
    return list(roster.loc[roster['start'] &
                           roster['player_id'].notnull(),
                           'team_position'])

if __name__ == '__main__':
    try:
        assert LEAGUE in LEAGUES.keys()
    except AssertionError:
        print(f"League {LEAGUE} not found. Valid leagues are: {', '.join(list(LEAGUES.keys()))}")

    LEAGUE_ID = LEAGUES[LEAGUE]['league_id']

    # open up our database connection
    conn = sqlite3.connect(DB_PATH)

    #######################################
    # load team and schedule data from DB
    #######################################

    teams = db.read_league('teams', LEAGUE_ID, conn)
    schedule = db.read_league('schedule', LEAGUE_ID, conn)
    league = db.read_league('league', LEAGUE_ID, conn)

    # now import site based on host
    host = league.iloc[0]['host']
    if host == 'fleaflicker':
        import hosts.fleaflicker as site
    elif host == 'yahoo':
        import hosts.yahoo as site
    elif host ==  'espn':
        import hosts.espn as site
    else:
        raise ValueError('Unknown host')

    # get parameters from league DataFrame

    team_id = league.iloc[0]['team_id']
    host = league.iloc[0]['host']
    league_scoring = {
        'qb':league.iloc[0]['qb_scoring'],
        'skill': league.iloc[0]['skill_scoring'],
        'dst': league.iloc[0]['dst_scoring']
    }

    #####################
    # get current rosters
    #####################

    # need players from FM API
    token = generate_token(LICENSE_KEY)['token']
    player_lookup = master_player_lookup(token)

    rosters = site.get_league_rosters(player_lookup, LEAGUE_ID, WEEK,
                                      starting=False)

    ########################
    # what we need for wdis:
    ########################
    # 1. list of our starters

    roster = rosters.query(f"team_id == {team_id}")

    current_starters = list(roster.loc[roster['start'] &
                                       roster['player_id'].notnull(),
                                       'player_id'])

    # 2. list of opponent's starters

    # first: use schedule to find our opponent this week
    schedule_team = schedule_long(schedule)
    opponent_id = schedule_team.loc[
        (schedule_team['team_id'] == team_id) & (schedule_team['week'] == WEEK),
        'opp_id'].values[0]

    # then same thing
    opponent_starters = rosters.loc[
        (rosters['team_id'] == opponent_id) & rosters['start'] &
        rosters['player_id'].notnull(), ['player_id', 'actual']]


    # 3. sims
    sims = get_sims_from_roster(
        token, rosters.query(f"team_id in ({team_id}, {opponent_id})"),
        nsims=1000, **league_scoring)

    ################################################
    # analysis - call wdis_by_pos over all positions
    ################################################

    positions = positions_from_roster(roster)

    # calling actual analysis function goes here
    df_start = DataFrame()
    for pos in positions:
        df1, roster = wdis_by_pos(pos, sims, roster,
                                  list(opponent_starters['player_id']))
        df_start = pd.concat([df_start, df1])

    # extract starters
    rec_starters = [df_start.xs(pos)['wp'].idxmax() for pos in positions]

    players = get_players(token, **league_scoring).set_index('player_id')

    print("")
    print("Recommended Starters:")
    print("")
    for starter, pos in zip(rec_starters, positions):
        print(f"{pos}: {players.loc[starter, 'name']}")

    print("")
    if set(rec_starters) == set(current_starters):
        print("Current starters maximize probability of winning")
    else:
        print("WARNING: Not maximizing probability of winning!")
        print("")
        print("Start:")
        print(", ".join(players.loc[list(set(rec_starters) - set(current_starters)),
              'name'].values))
        print("")
        print("Instead of:")
        print(", ".join(players.loc[list(set(current_starters) - set(rec_starters)),
              'name'].values))
        
    # update df_start with players
    # make name column using value of player_id
    df_start.reset_index(inplace=True)
    df_start['name'] = df_start['player_id'].map(players['name'].to_dict())
    df_start.set_index(['pos', 'name'], inplace=True)


    ######################
    # write output to file
    ######################
    if WRITE_OUTPUT:
        league_wk_output_dir = path.join(
            OUTPUT_PATH, f'{LEAGUE}_2024-{str(WEEK).zfill(2)}')

        Path(league_wk_output_dir).mkdir(exist_ok=True)

        wdis_output_file = path.join(league_wk_output_dir, 'wdis.txt')

        with open(wdis_output_file, 'w') as f:
            print(f"WDIS Analysis, {LEAGUE}, Week {WEEK}", file=f)
            print("", file=f)
            print(f"Run at {dt.datetime.now()}", file=f)
            print("", file=f)
            print("Recommended Starters:", file=f)
            for starter, pos in zip(rec_starters, positions):
                print(f"{pos}: {players.loc[starter, 'name']}", file=f)

            print("", file=f)
            print("Detailed Projections and Win Probability:", file=f)
            print(df_start[['mean', 'wp', 'wrong', 'regret']], file=f)
            print("", file=f)

            if set(current_starters) == set(rec_starters):
                print("Current starters maximize probability of winning.", file=f)
            else:
                print("Not maximizing probability of winning.", file=f)
                print("", file=f)
                print("Start:", file=f)
                print(set(rec_starters) - set(current_starters), file=f)
                print("", file=f)
                print("Instead of:", file=f)
                print(set(current_starters) - set(rec_starters), file=f)
