import hosts.db as db
import pandas as pd
from pathlib import Path
import sqlite3
from hosts.league_setup import LEAGUES
from pandas import DataFrame
from os import path
import seaborn as sns
from pandas import Series
from utilities import (generate_token, LICENSE_KEY, master_player_lookup,
    OUTPUT_PATH, get_sims_from_roster, DB_PATH)
import hosts.sleeper as site

# PARAMETERS
POS = ['qb', 'rb1', 'rb2', 'wr1', 'wr2', 'wr3', 'te', 'flex', 'dst']
LEAGUE = 'bball'
WEEK = 3  
WRITE_OUTPUT = True

##############################################
# shouldn't have to change anything below this
##############################################

def n_highest_scores_from_sim(sim, players, n):
    df = sim.loc[players].sort_values(ascending=False).iloc[:n].reset_index()
    df.columns = ['name', 'points']
    df['rank'] = range(1, n+1)
    df['sim'] = sim.name
    return df

def top_n_by_pos(sims, pos, players, n):
    df_long = pd.concat([n_highest_scores_from_sim(row, players, n) for
                        _, row in sims.iterrows()], ignore_index=True)
    df_wide = df_long.set_index(['sim', 'rank']).unstack()
    df_wide.columns = ([f'{pos}{x}_name' for x in range(1, n+1)] +
                    [f'{pos}{x}_points' for x in range(1, n+1)])
    return df_wide

# after cutoff
def leftover_from_sim(sim, players, n):
    df = sim.loc[players].sort_values(ascending=False).iloc[n:].reset_index()
    df.columns = ['name', 'points']
    df['sim'] = sim.name
    return df

def wide_by_team(roster, sims):
    pos_dict = {pos: list(roster
                          .query(f"player_position == '{pos.upper()}'")['player_id']
                          .values) for pos in ['qb', 'rb', 'wr', 'te', 'dst']}

    # wide positions
    rbs_wide = top_n_by_pos(sims, 'rb', pos_dict['rb'], 2)
    wrs_wide = top_n_by_pos(sims, 'wr', pos_dict['wr'], 3)
    qb_wide = top_n_by_pos(sims, 'qb', pos_dict['qb'], 1)
    te_wide = top_n_by_pos(sims, 'te', pos_dict['te'], 1)
    dst_wide = top_n_by_pos(sims, 'dst', pos_dict['dst'], 1)

    # leftovers for flex
    rbs_leftover = pd.concat([leftover_from_sim(row, pos_dict['rb'], 2) for _, row
                              in sims.iterrows()], ignore_index=True)
    wrs_leftover = pd.concat([leftover_from_sim(row, pos_dict['wr'], 3) for _, row
                              in sims.iterrows()], ignore_index=True)
    tes_leftover = pd.concat([leftover_from_sim(row, pos_dict['te'], 1) for _, row
                              in sims.iterrows()], ignore_index=True)

    leftovers = pd.concat([rbs_leftover, wrs_leftover, tes_leftover],
                          ignore_index=True)
    max_points_index = leftovers.groupby('sim').idxmax()['points']
    flex_wide = leftovers.loc[max_points_index].set_index('sim')
    flex_wide.columns = ['flex_name', 'flex_points']

    team_wide = pd.concat([qb_wide, rbs_wide, wrs_wide, te_wide, flex_wide,
                           dst_wide], axis=1)
    return team_wide

def name_names(df, rosters):
    lookup = (rosters.set_index('player_id')['name']
        .str.lower()
        .str.replace('.','', regex=False)
        .str.replace(' ', '-', regex=False)
        .to_dict())
    return df.replace(lookup)

def usage(df, pos):
    dfu = pd.concat([df[x].value_counts(normalize=True) for x in pos],
                      axis=1, join='outer').fillna(0)
    dfu.columns = [x.upper() for x in pos]
    dfu['ALL'] = dfu.sum(axis=1)

    dfuc = dfu.round(2).astype(str)
    for x in dfuc.columns:
        dfuc[x] = (dfuc[x]
            .str.pad(4, fillchar='0', side='right')
            .str.replace('^0.00$','', regex=True))
    return dfuc

def points(dfp):
    """
    Calculate summary stats on one set of teams.
    """
    dft = dfp.sum(axis=1).reset_index()
    dft.columns = ['team_id', 'sim', 'points']
    return dft.groupby('team_id')['points'].describe(percentiles=[.05, .25, .5, .75, .95]) [['mean', 'std', '5%', '25%', '50%', '75%', '95%']]

if __name__ == '__main__':
    try:
        assert LEAGUE in LEAGUES.keys()
    except AssertionError:
        print(f"League {LEAGUE} not found. Valid leagues are: {', '.join(list(LEAGUES.keys()))}")


    # first: get league data from DB + roster data by connecting to site
    LEAGUE_ID = LEAGUES[LEAGUE]['league_id']
    conn = sqlite3.connect(DB_PATH)

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
    elif host ==  'sleeper':
        import hosts.sleeper as site
    else:
        raise ValueError('Unknown host')

    # set other parameters
    host = league.iloc[0]['host']
    league_scoring = {
        'qb':league.iloc[0]['qb_scoring'],
        'skill': league.iloc[0]['skill_scoring'],
        'dst': league.iloc[0]['dst_scoring']
    }

    # then load rosters
    token = generate_token(LICENSE_KEY)['token']
    player_lookup = master_player_lookup(token)
    rosters = site.get_league_rosters(player_lookup, LEAGUE_ID, WEEK)

    # and get sims
    sims = get_sims_from_roster(token, rosters, nsims=1000, **league_scoring)

    # user owner names instead of team ids
    team_to_owner = {team: owner for team, owner in zip(teams['team_id'],
                                                        teams['owner_name'])}
    rosters['team_id'] = rosters['team_id'].map(team_to_owner)

    ####################################
    # calculate points and usage by team
    ####################################
    dfw = rosters.groupby('team_id').apply(wide_by_team, sims)

    # separate out into names and points
    dfn = dfw[[x for x in dfw.columns if x.endswith('_name')]]
    dfn.columns = POS
    dfn = name_names(dfn, rosters)

    dfp = dfw[[x for x in dfw.columns if x.endswith('_points')]]
    dfp.columns = POS

    # now make usage for each team
    usage_by_team = dfn.groupby(level=0).apply(usage, POS)
    team_df = points(dfp).round(2)

    totals_by_team = dfp.sum(axis=1).unstack(0)
    team_df['phigh'] = totals_by_team.idxmax(axis=1).value_counts(normalize=True)
    team_df['plow'] = totals_by_team.idxmin(axis=1).value_counts(normalize=True)

    team_df.sort_values('mean', ascending=False).round(2)

    if WRITE_OUTPUT:
        league_wk_output_dir = path.join(
            OUTPUT_PATH, f'{host}_{LEAGUE_ID}_2023-{str(WEEK).zfill(2)}')
        Path(league_wk_output_dir).mkdir(exist_ok=True, parents=True)
        usage_by_team.to_csv(path.join(league_wk_output_dir, 'usage.csv'))

