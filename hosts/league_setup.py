from hosts.db import overwrite_league
from pandas import DataFrame
import sqlite3
from utilities import DB_PATH

#########################################
# update all this for your league
# need to do for EVERY league you analyze
#########################################
LEAGUE_ID = 34958
TEAM_ID = 217960

LEAGUE_NAME = "BB Bowl"
HOST = 'fleaflicker'
SCORING = {'qb': 'pass_6', 'skill': 'ppr_1', 'dst': 'dst_high'}

##################################################
# shouldn't have to change anything from here down
##################################################

# do some checks
assert SCORING['qb'] in ['pass_4', 'pass_6']
assert SCORING['skill'] in ['ppr_1', 'ppr_1over2', 'ppr_0']
assert SCORING['dst'] in ['dst_std', 'dst_high']

# load right helper functions depending on platform
match HOST.lower():
    case 'fleaflicker':
        import hosts.fleaflicker as site
    case 'espn':
        import hosts.espn as site
    case 'yahoo':
        import hosts.yahoo as site
    case 'sleeper':
        import hosts.sleeper as site
    case _:
        raise ValueError(f"Unknown host: {HOST}")

if __name__ == '__main__':
    # work starts here:
    # open up our database connection
    conn = sqlite3.connect(DB_PATH)

    # team list
    teams = site.get_teams_in_league(LEAGUE_ID)
    overwrite_league(teams, 'teams', conn, LEAGUE_ID)

    # schedule info
    schedule = site.get_league_schedule(LEAGUE_ID)
    overwrite_league(schedule, 'schedule', conn, LEAGUE_ID)


    # league info
    league = DataFrame([{'league_id': LEAGUE_ID,
                         'team_id': TEAM_ID,
                         'host': HOST.lower(),
                         'name': LEAGUE_NAME,
                         'qb_scoring': SCORING['qb'],
                         'skill_scoring': SCORING['skill'],
                         'dst_scoring': SCORING['dst']}])

    overwrite_league(league, 'league', conn, LEAGUE_ID)
