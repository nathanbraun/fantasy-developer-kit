import hosts.db as db
from hosts.league_setup import LEAGUES
import sqlite3
import pandas as pd
from os import path
from pathlib import Path
import seaborn as sns
from textwrap import dedent
from pandas import DataFrame
from utilities import (generate_token, LICENSE_KEY, DB_PATH,
    OUTPUT_PATH, master_player_lookup, schedule_long, get_sims_from_roster)

#####################
# set parameters here
#####################
LEAGUE = 'nate-league'
WEEK = 1
WRITE_OUTPUT = False

##############################################
# shouldn't have to change anything below this
##############################################

def summarize_matchup(sims_a, sims_b):
    """
    Given two teams of sims (A and B), summarize a matchup with win
    probability, over-under, betting line, etc
    """

    # start by getting team totals
    total_a = sims_a.sum(axis=1)
    total_b = sims_b.sum(axis=1)

    # get win prob
    winprob_a = (total_a > total_b).mean()
    winprob_b = 1 - winprob_a

    # get over-under
    over_under = (total_a + total_b).median()

    # spread
    spread = round((total_a - total_b).median(), 2)

    # moneyline
    ml_a = wp_to_ml(winprob_a)

    return {'wp_a': round(winprob_a, 2), 'wp_b': round(winprob_b, 2),
            'over_under': round(over_under, 2), 'spread': spread, 'ml': ml_a}

def summarize_team(sims):
    """
    Calculate summary stats on one set of teams.
    """
    totals = sims.sum(axis=1)
    # note: dropping count, min, max since those aren't that useful
    stats = (totals.describe(percentiles=[.05, .25, .5, .75, .95])
            [['mean', 'std', '5%', '25%', '50%', '75%', '95%']].to_dict())

    # maybe share of points by each pos? commented out now but could look if
    # interesting

    # stats['qb'] = sims.iloc[:,0].mean()
    # stats['rb'] = sims.iloc[:,1:3].sum(axis=1).mean()
    # stats['flex'] = sims.iloc[:,3].mean()
    # stats['wr'] = sims.iloc[:,4:6].sum(axis=1).mean()
    # stats['te'] = sims.iloc[:,6].mean()
    # stats['k'] = sims.iloc[:,7].mean()
    # stats['dst'] = sims.iloc[:,8].mean()

    return stats

def lineup_by_team(team_id):
    return rosters.query(f"team_id == {team_id} & player_id.notnull()")['player_id']

def lock_of_week(df):
    # team a
    wp_a = df[['team_a', 'wp_a', 'team_b']]
    wp_a.columns = ['team', 'wp', 'opp']

    # team b
    wp_b = df[['team_b', 'wp_b', 'team_a']]
    wp_b.columns = ['team', 'wp', 'opp']

    # combine
    stacked = pd.concat([wp_a, wp_b], ignore_index=True)

    # sort highest to low, pick out top
    lock = stacked.sort_values('wp', ascending=False).iloc[0]
    return lock.to_dict()

def photo_finish(df):
    # get the std dev of win probs, lowest will be cloest matchup
    wp_std = df[['wp_a', 'wp_b']].std(axis=1)

    # idxmin "index min" returns the index of the lowest value
    closest_matchup_id = wp_std.idxmin()

    return df.loc[closest_matchup_id].to_dict()

def wp_to_ml(wp):
    if (wp == 0 or wp == 1):
        return 0
    elif wp > 0.5:
        return int(round(-1*(100/((1 - wp)) - 100), 0))
    else:
        return int(round((100/((wp)) - 100), 0))

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

    ########################################################
    # load weekly lineup, matchup info
    ########################################################

    schedule_this_week = schedule.query(f"week == {WEEK}")

    # apply summarize matchup to every matchup in the data
    matchup_list = []  # empty matchup list, where all our dicts will go

    for a, b in zip(schedule_this_week['team1_id'], schedule_this_week['team2_id']):

        # gives us Series of starting lineups for each team in matchup
        lineup_a = set(lineup_by_team(a)) & set(sims.columns)
        lineup_b = set(lineup_by_team(b)) & set(sims.columns)

        # use lineups to grab right sims, feed into summarize_matchup function
        working_matchup_dict = summarize_matchup(
            sims[list(lineup_a)], sims[list(lineup_b)])

        # add some other info to working_matchup_dict
        working_matchup_dict['team_a'] = a
        working_matchup_dict['team_b'] = b

        # add working dict to list of matchups, then loop around to next
        # matchup
        matchup_list.append(working_matchup_dict)

    matchup_df = DataFrame(matchup_list)

    team_to_owner = {team: owner for team, owner in zip(teams['team_id'],
                                                        teams['owner_name'])}

    matchup_df[['team_a', 'team_b']] = matchup_df[['team_a', 'team_b']].replace(team_to_owner)

    #################
    # analyzing teams
    #################

    team_list = []

    for team_id in teams['team_id']:
        team_lineup = list(set(lineup_by_team(team_id)) & set(sims.columns))
        working_team_dict = summarize_team(sims[team_lineup])
        working_team_dict['team_id'] = team_id
        working_team_dict['n'] = sims[team_lineup].shape[-1]

        team_list.append(working_team_dict)

    team_df = DataFrame(team_list).set_index('team_id')

    # high low
    # first step: get totals for each team in one DataFrame
    totals_by_team = pd.concat(
        [(sims[list(set(lineup_by_team(team_id)) & set(sims.columns))].sum(axis=1)
            .to_frame(team_id)) for team_id in teams['team_id']], axis=1)

    team_df['p_high'] = (totals_by_team.idxmax(axis=1)
                        .value_counts(normalize=True))

    team_df['p_low'] = (totals_by_team.idxmin(axis=1)
                        .value_counts(normalize=True))

    # lets see what those high and lows are, on average
    # first step: get high score of every sim (max, not idxmax, we don't care
    # who got it)
    high_score = totals_by_team.max(axis=1)

    # same for low score
    low_score = totals_by_team.min(axis=1)

    # then analyze
    pd.concat([
        high_score.describe(percentiles=[.05, .25, .5, .75, .95]).to_frame('high'),
        low_score.describe(percentiles=[.05, .25, .5, .75, .95]).to_frame('low')], axis=1)


    # add owner
    team_df = (pd.merge(team_df, teams[['team_id', 'owner_name']], left_index=True,
                    right_on = 'team_id')
            .set_index('owner_name')
            .drop('team_id', axis=1))

    league_wk_output_dir = path.join(
        OUTPUT_PATH, f'{LEAGUE}_2024-{str(WEEK).zfill(2)}')

    Path(league_wk_output_dir).mkdir(exist_ok=True, parents=True)

    if WRITE_OUTPUT:
        output_file = path.join(league_wk_output_dir, 'league_analysis.txt')

        # print results
        with open(output_file, 'w') as f:
            print(dedent(
                f"""
                **********************************
                Matchup Projections, Week {WEEK} - 2024
                **********************************
                """), file=f)
            print(matchup_df, file=f)

            print(dedent(
                f"""
                ********************************
                Team Projections, Week {WEEK} - 2024
                ********************************
                """), file=f)

            print(team_df.round(2).sort_values('mean', ascending=False),
                file=f)


            lock = lock_of_week(matchup_df)
            close = photo_finish(matchup_df)
            meh = matchup_df.sort_values('over_under').iloc[0]

            print(dedent("""
                Lock of the week:"""), file=f)
            print(f"{lock['team']} over {lock['opp']} — {lock['wp']}", file=f)

            print(dedent("""
                        Photo-finish of the week::"""), file=f)
            print(f"{close['team_a']} vs {close['team_b']}, {close['wp_a']}-{close['wp_b']}", file=f)

            print(dedent("""
                        Most unexciting game of the week:"""), file=f)
            print(f"{meh['team_a']} vs {meh['team_b']}, {meh['over_under']}", file=f)

        ########################################################################
        # plot section
        ########################################################################

        teams_long = totals_by_team.stack().reset_index()
        teams_long.columns = ['sim', 'team_id', 'pts']

        # now to link this to teams_long
        schedule_team = schedule_long(schedule).query(f"week == {WEEK}")

        teams_long_w_matchup = pd.merge(teams_long, schedule_team[['team_id', 'matchup_id']])


        schedule_this_week['desc'] = (schedule_this_week['team2_id'].replace(team_to_owner)
                                    + ' v ' +
                                    schedule_this_week['team1_id'].replace(team_to_owner))

        # and plot it
        teams_long_w_desc = pd.merge(teams_long_w_matchup,
                                    schedule_this_week[['matchup_id', 'desc']])
        teams_long_w_desc.head()

        g = sns.FacetGrid(teams_long_w_desc.replace(team_to_owner), hue='team_id',
                        col='desc', col_wrap=2, aspect=2)
        g = g.map(sns.kdeplot, 'pts', fill=True)
        g.add_legend()
        g.fig.subplots_adjust(top=0.9)
        g.fig.suptitle(f'Team Points Distributions by Matchup 2 - Week {WEEK}')
        g.fig.savefig(path.join(league_wk_output_dir, 'team_dist_by_matchup.png'),
                    bbox_inches='tight', dpi=500)

    else:
        print('\n')
        print('**********************************')
        print(f'Matchup Projections, Week {WEEK} - 2024')
        print('**********************************')
        print('\n')
        print(matchup_df)
        print('\n')
        print('**********************************')
        print(f'Team Projections, Week {WEEK} - 2024')
        print('**********************************')
        print('\n')
        print(team_df.sort_values('mean', ascending=False).round(2))
        # print('\n')
        # print('**********************************')
        # print("Projected high and low scores:")
        # print('**********************************')
        # print('\n')
        # print(pd.concat([high_score, low_score], axis=1, keys=['high', 'low'])
        #       .describe(percentiles=[.05, 0.1, .25, .5, .75, 0.9, .95])
        #       .drop(['count', 'min', 'max']))


