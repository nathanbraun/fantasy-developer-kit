from hosts.db import overwrite_league
from pandas import DataFrame
import sqlite3
from utilities import DB_PATH

#########################################
# update all this for your league
# need to do for EVERY league you analyze
#########################################

LEAGUES = {
    'nate-league': {
        'host': 'fleaflicker',
        'league_id': 34958,
        'team_id': 217960,
        'scoring': {'qb': 'pass_6', 'skill': 'ppr_1', 'dst': 'dst_high'}},
    # add new leagues here in same format (uncomment)
    # 'your-league': {
    #     'host': 'espn',
    #     'league_id': 34958,
    #     'team_id': 217960,
    #     'scoring': {'qb': 'pass_6', 'skill': 'ppr_1', 'dst': 'dst_high'}},
}

##################################################
# shouldn't have to change anything from here down
##################################################

if __name__ == '__main__':
    # work starts here:
    # open up our database connection
    conn = sqlite3.connect(DB_PATH)

    for name, league in LEAGUES.items():
        host = league['host'].lower()
        league_id = league['league_id']
        team_id = league['team_id']
        scoring = league['scoring']

        # do some checks
        assert scoring['qb'] in ['pass_4', 'pass_6']
        assert scoring['skill'] in ['ppr_1', 'ppr_1over2', 'ppr_0']
        assert scoring['dst'] in ['dst_std', 'dst_high']

        # load right helper functions depending on platform
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

        # team list
        teams = site.get_teams_in_league(league_id)
        overwrite_league(teams, 'teams', conn, league_id)

        # schedule info
        schedule = site.get_league_schedule(league_id)
        overwrite_league(schedule, 'schedule', conn, league_id)


        # league info
        league = DataFrame([{'league_id': league_id,
                             'team_id': team_id,
                             'host': host,
                             'name': name,
                             'qb_scoring': scoring['qb'],
                             'skill_scoring': scoring['skill'],
                             'dst_scoring': scoring['dst']}])

        overwrite_league(league, 'league', conn, league_id)
