import pandas as pd
from os import path
import seaborn as sns
from pandas import Series
from utilities import (generate_token, get_sims, LICENSE_KEY, get_players,
    name_sims)

# generate access token
token = generate_token(LICENSE_KEY)['token']

WEEK = 1
SEASON = 2021
NSIMS = 500
SCORING = {'qb': 'pass_6', 'skill': 'ppr_1', 'dst': 'dst_high'}

team1 = ['jalen-hurts', 'clyde-edwards-helaire', 'saquon-barkley',
         'keenan-allen', 'cooper-kupp', 'dallas-goedert', 'jason-myers', 'tb']
team1_ids = [498, 518, 904, 1954, 1139, 974, 1871, 5180]

team2 = ['justin-jefferson', 'antonio-gibson', 'noah-fant',
         'christian-mccaffrey', 'tyler-lockett', 'matthew-stafford',
         'matt-gay', 'gb']
team2_ids = [551, 567, 755, 1105, 1542, 2621, 776, 5162]

bench = ['darrell-henderson', 'ronald-jones', 'tony-pollard']
bench_ids = [703, 705, 906]

USE_SAVED_DATA = True

if USE_SAVED_DATA:
    valid_players = pd.read_csv(path.join('projects', 'wdis', 'data',
                                          'valid_players.csv')).set_index('player_id')
else:
    valid_players = get_players(token, season=SEASON, week=WEEK,
                                **SCORING).set_index('player_id')

(valid_players[['name']])[:20]

# and query sims
player_ids = team1_ids + team2_ids + bench_ids

if USE_SAVED_DATA:
    sims = pd.read_csv(path.join('projects', 'wdis', 'data', 'sims.csv'))
    sims.columns = [int(x) for x in sims.columns]
else:
    sims = get_sims(token, player_ids, week=WEEK, season=SEASON, nsims=NSIMS,
                    **SCORING)

sims.head()

nsims = name_sims(sims, valid_players)
nsims.head()

# coding up WDIS
nsims[team1].head()

nsims[team1].sum()

nsims[team1].sum(axis=1).head()
nsims[team2].sum(axis=1).head()

team1_beats_team2 = nsims[team1].sum(axis=1) > nsims[team2].sum(axis=1)
team1_beats_team2.head()

print(team1_beats_team2.mean())

# first cut at WDIS
def simple_wdis(sims, team1, team2, wdis):
    team1_wdis = team1 + [wdis]
    return (sims[team1_wdis].sum(axis=1) > sims[team2].sum(axis=1)).mean()

team1_no_wdis = ['jalen-hurts', 'saquon-barkley', 'keenan-allen',
                 'cooper-kupp', 'dallas-goedert', 'jason-myers', 'tb']

wdis = ['clyde-edwards-helaire', 'darrell-henderson', 'ronald-jones',
        'tony-pollard']

for player in wdis:
    print(player)
    print(simple_wdis(nsims, team1_no_wdis, team2, player))

# modify it to so it takes in a list of wdis players and analyzes them all
def simple_wdis2(sims, team1, team2, wdis):
    return {
        player: float((sims[team1 + [player]].sum(axis=1) >
                 sims[team2].sum(axis=1)).mean())
        for player in wdis}

simple_wdis2(nsims, team1_no_wdis, team2, wdis)

# modify so can take a complete team1
def simple_wdis3(sims, team1, team2, wdis):

    # there should be one player that overlaps in wdis and team1
    team1_no_wdis = [x for x in team1 if x not in wdis]

    # another way to do this is using python sets
    # team1_no_wdis_alt = set(team1) - set(wdis)

    return {
        player: float((sims[team1_no_wdis + [player]].sum(axis=1) >
                 sims[team2].sum(axis=1)).mean()) for player in wdis}

simple_wdis3(nsims, team1, team2, wdis)
simple_wdis3(nsims, team1, team2, ['saquon-barkley', 'darrell-henderson'])

# throws an error
# assert False

# no error
assert True

def simple_wdis4(sims, team1, team2, wdis):

    # there should be one player that overlaps in wdis and team1
    team1_no_wdis = [x for x in team1 if x not in wdis]

    # some checks
    current_starter = [x for x in team1 if x in wdis]
    assert len(current_starter) == 1

    bench_options = [x for x in wdis if x not in team1]
    assert len(bench_options) >= 1

    return Series({
        player: float((sims[team1_no_wdis + [player]].sum(axis=1) >
                 sims[team2].sum(axis=1)).mean()) for player in wdis}
                  ).sort_values(ascending=False)


simple_wdis4(nsims, team1, team2, wdis)

# will throw an error:
# simple_wdis4(nsims, team1, team2, ['darrell-henderson', 'ronald-jones',
#                                    'tony-pollard'])

# beyond WDIS
# here's where we landed
team1 = ['jalen-hurts', 'saquon-barkley', 'clyde-edwards-helaire',
         'keenan-allen', 'cooper-kupp', 'dallas-goedert', 'jason-myers',
         'tb']

team2 = ['matthew-stafford', 'christian-mccaffrey', 'antonio-gibson',
        'tyler-lockett', 'justin-jefferson', 'noah-fant', 'matt-gay',
        'gb']


current_starter = 'clyde-edwards-helaire'
bench_options = ['darrell-henderson', 'ronald-jones', 'tony-pollard']
team1_sans_starter = list(set(team1) - set([current_starter]))

# overall score
nsims[team1].sum(axis=1).describe()

stats = pd.concat([(nsims[team1_sans_starter].sum(axis=1) + 
                    nsims[x]).describe() for x in wdis], axis=1)
stats.columns = wdis  # make column names = players
stats

stats.T.drop(['count', 'min', 'max'], axis=1)  # drop unnec columns

# prob of starting the wrong guy
nsims[bench_options].max(axis=1).head()

pd.concat([nsims[bench_options].max(axis=1),
           nsims[current_starter]], axis=1).head()

print((nsims[bench_options].max(axis=1) > nsims[current_starter]).mean())

# prob of losing because we start the wrong guy
# pieces we need
team1_w_starter = nsims[team1_sans_starter].sum(axis=1) + nsims[current_starter]

team1_w_best_backup = (nsims[team1_sans_starter].sum(axis=1) +
                       nsims[bench_options].max(axis=1))

team2_total = nsims[team2].sum(axis=1)

# true if team w/ best backup > team2 AND team w/ starer we picked < team2
regret_col = ((team1_w_best_backup > team2_total) &
              (team1_w_starter < team2_total))
print(regret_col.mean())

# true if team w/ best backup > team2 AND team w/ starer we picked < team2
nailed_it_col = ((team1_w_best_backup < team2_total) &
                 (team1_w_starter > team2_total))
print(nailed_it_col.mean())

# function forms
def sumstats(starter):
    team_w_starter = nsims[team1_sans_starter].sum(axis=1) + nsims[starter]
    stats_series = (team_w_starter
                    .describe(percentiles=[.05, .25, .5, .75, .95])
                    .drop(['count', 'min', 'max']))
    stats_series.name = starter
    return stats_series

def win_prob(starter):
    team_w_starter = nsims[team1_sans_starter].sum(axis=1) + nsims[starter]
    return (team_w_starter > team2_total).mean()

def wrong_prob(starter, bench):
    return (nsims[bench].max(axis=1) > nsims[starter]).mean()

def regret_prob(starter, bench):
    team_w_starter = nsims[team1_sans_starter].sum(axis=1) + nsims[starter]
    team_w_best_backup = (nsims[team1_sans_starter].sum(axis=1) +
                        nsims[bench].max(axis=1))

    return ((team_w_best_backup > team2_total) &
            (team_w_starter < team2_total)).mean()

def nailed_it_prob(starter, bench):
    team_w_starter = nsims[team1_sans_starter].sum(axis=1) + nsims[starter]
    team_w_best_backup = (nsims[team1_sans_starter].sum(axis=1) +
                        nsims[bench].max(axis=1))

    return ((team_w_best_backup < team2_total) &
            (team_w_starter > team2_total)).mean()

# CEH
print(sumstats('clyde-edwards-helaire'))
print(win_prob(current_starter))
print(wrong_prob(current_starter, bench_options))
print(regret_prob(current_starter, bench_options))
print(nailed_it_prob(current_starter, bench_options))

# now with next best alternative, henderson
print(sumstats('darrell-henderson'))
print(win_prob('darrell-henderson'))
print(wrong_prob('darrell-henderson',
           ['clyde-edwards-helaire', 'ronald-jones', 'tony-pollard']))
print(regret_prob('darrell-henderson',
           ['clyde-edwards-helaire', 'ronald-jones', 'tony-pollard']))
print(nailed_it_prob('darrell-henderson',
           ['clyde-edwards-helaire', 'ronald-jones', 'tony-pollard']))

# and so on ...

def start_bench_scenarios(wdis):
    """
    Return all combinations of start, backups for all players in wdis.
    """
    return [{
        'starter': player,
        'bench': [x for x in wdis if x != player]
    } for player in wdis]

# walk through buliding start bench scenarios

wdis
start_bench_scenarios(wdis)

scenarios = start_bench_scenarios(wdis)

# simpler start bench scenarios
wdis

# concrete case
player = 'clyde-edwards-helaire'
[x for x in wdis if x != player]

# want that in a dict:
{'starter': player, 'bench': [x for x in wdis if x != player]}

[{'starter': player, 'bench': [x for x in wdis if x != player] }
    for player in wdis]

# back to analyzing player stats

# start with table of sum stats
df = pd.concat([sumstats(player) for player in wdis], axis=1)

df = df.T

df.head()

# now let's go through and add all our extra data to it
# start with win prob
wps = [win_prob(player) for player in wdis]
df['wp'] = wps  # adding wps as a column to our data of stats

df.head()

# now do wrong prob
# note, skipping separate step above and just putting it in the dataframe all
# at once
df['wrong'] = [wrong_prob(scen['starter'], scen['bench']) for scen in scenarios]
df.head()

# now regret prob
# this time: ** trick, can p
df['regret'] = [regret_prob(**scen) for scen in scenarios]
df['nailed'] = [nailed_it_prob(**scen) for scen in scenarios]

# final result:
df.round(2)

def wdis_plus(sims, team1, team2, wdis):

    # do some validity checks
    current_starter = set(team1) & set(wdis)
    assert len(current_starter) == 1

    bench_options = set(wdis) - set(team1)
    assert len(bench_options) >= 1

    team_sans_starter = list(set(team1) - current_starter)

    scenarios = start_bench_scenarios(wdis)
    team2_total = sims[team2].sum(axis=1)  # opp

    # note these functions all work with sims, even though they don't take sims
    # as an argument
    # it works because everything inside wdis_plus has access to sims
    # if these functions were defined outside of wdis_plus it wouldn't work
    # this is an example of lexical scope: https://stackoverflow.com/a/53062093
    def sumstats(starter):
        team_w_starter = sims[team_sans_starter].sum(axis=1) + sims[starter]
        team_info = (team_w_starter
                    .describe(percentiles=[.05, .25, .5, .75, .95])
                    .drop(['count', 'min', 'max']))

        return team_info

    def win_prob(starter):
        team_w_starter = sims[team_sans_starter].sum(axis=1) + sims[starter]
        return (team_w_starter > team2_total).mean()

    def wrong_prob(starter, bench):
        return (sims[bench].max(axis=1) > sims[starter]).mean()

    def regret_prob(starter, bench):
        team_w_starter = sims[team_sans_starter].sum(axis=1) + sims[starter]
        team_w_best_backup = (sims[team_sans_starter].sum(axis=1) +
                            sims[bench].max(axis=1))

        return ((team_w_best_backup > team2_total) &
                (team_w_starter < team2_total)).mean()

    def nailed_it_prob(starter, bench):
        team_w_starter = sims[team1_sans_starter].sum(axis=1) + sims[starter]
        team_w_best_backup = (sims[team1_sans_starter].sum(axis=1) +
                            sims[bench].max(axis=1))

        return ((team_w_best_backup < team2_total) &
                (team_w_starter > team2_total)).mean()


    # start with DataFrame of summary stats
    df = pd.concat([sumstats(player) for player in wdis], axis=1)
    df.columns = wdis
    df = df.T

    # then add prob of win, being wrong, regretting decision
    df['wp'] = [win_prob(x['starter']) for x in scenarios]
    df['wrong'] = [wrong_prob(**x) for x in scenarios]
    df['regret'] = [regret_prob(**x) for x in scenarios]
    df['nailed'] = [nailed_it_prob(**x) for x in scenarios]

    return df.sort_values('wp', ascending=False)


wdis_plus(nsims, team1, team2, wdis)

# now lets use our new function to analyze every kicker on waivers

fa_kickers = ['jake-elliott', 'tristan-vizcaino', 'josh-lambo', 'greg-joseph',
              'evan-mcpherson', 'chase-mclaughlin', 'ryan-santoso',
              'aldrick-rosas', 'jason-sanders', 'daniel-carlson',
              'rodrigo-blankenship', 'brandon-mcmanus', 'joey-slye',
              'graham-gano', 'nick-folk', 'cairo-santos']

fa_kicker_ids = [1188, 869, 1635, 1035, 435, 872, 1079, 1477, 1003, 981, 592,
                 1839, 864, 2713, 2939, 1837]

if USE_SAVED_DATA:
    k_sims = pd.read_csv(path.join('projects', 'wdis', 'data', 'k_sims.csv'))
    k_sims.columns = [int(x) for x in k_sims.columns]
else:
    k_sims = get_sims(token, fa_kicker_ids, week=WEEK, season=SEASON,
                      nsims=1000, **SCORING)

nk_sims = name_sims(k_sims, valid_players)

nsims_plus = pd.concat([nsims, nk_sims], axis=1)

wdis_k = fa_kickers + ['jason-myers']

df_k = wdis_plus(nsims_plus, team1, team2, wdis_k)
df_k

############################
# Plotting
############################

points_wide = pd.concat(
    [nsims[team1].sum(axis=1), nsims[team2].sum(axis=1)], axis=1)

points_wide.columns = ['team1', 'team2']
points_wide.head()

points_wide.stack().head()

points_long = points_wide.stack().reset_index()
points_long.columns = ['sim', 'team', 'points']
points_long.head(10)

g = sns.FacetGrid(points_long, hue='team', aspect=2)
g = g.map(sns.kdeplot, 'points', fill=True)
g.add_legend()
g.fig.subplots_adjust(top=0.9)
g.fig.suptitle('Team Fantasy Points Distributions')
g.fig.savefig(path.join('projects', 'wdis', 'plots', 'wdis_dist_by_team1.png'),
              bbox_inches='tight', dpi=500)

# all players
points_wide = pd.concat(
    [nsims[team1_sans_starter].sum(axis=1) + nsims[player] for player in wdis], axis=1)
points_wide.columns = wdis
points_wide['opp'] = nsims[team2].sum(axis=1)

points_wide.head()

# rest is the same as above
points_long = points_wide.stack().reset_index()
points_long.columns = ['sim', 'team', 'points']

points_long.head(10)

g = sns.FacetGrid(points_long, hue='team', aspect=2)
g = g.map(sns.kdeplot, 'points', fill=True)
g.add_legend()
g.fig.subplots_adjust(top=0.9)
g.fig.suptitle('Team Fantasy Points Distributions - WDIS Options')
g.fig.savefig(path.join('projects', 'wdis', 'plots', 'wdis_dist_by_team2.png'),
              bbox_inches='tight', dpi=500)

def wdis_plot(nsims, team1, team2, wdis):

    # do some validity checks
    current_starter = set(team1) & set(wdis)
    assert len(current_starter) == 1

    bench_options = set(wdis) - set(team1)
    assert len(bench_options) >= 1

    #
    team_sans_starter = list(set(team1) - current_starter)

    # total team points under allt he starters
    points_wide = pd.concat(
        [nsims[team_sans_starter].sum(axis=1) + nsims[player] for player in
         wdis], axis=1)

    points_wide.columns = wdis

    # add in apponent
    points_wide['opp'] = nsims[team2].sum(axis=1)

    # shift data from columns to rows to work with seaborn
    points_long = points_wide.stack().reset_index()
    points_long.columns = ['sim', 'team', 'points']

    # actual plotting portion
    g = sns.FacetGrid(points_long, hue='team', aspect=4)
    g = g.map(sns.kdeplot, 'points', fill=True)
    g.add_legend()
    g.fig.subplots_adjust(top=0.9)
    g.fig.suptitle('Team Fantasy Points Distributions - WDIS Options')

    return g


# individual player plots

pw = nsims[wdis].stack().reset_index()
pw.columns = ['sim', 'player', 'points']

g = sns.FacetGrid(pw, hue='player', aspect=2)
g = g.map(sns.kdeplot, 'points', fill=True)
g.add_legend()
g.fig.subplots_adjust(top=0.9)
g.fig.suptitle(f'WDIS Projections')
g.fig.savefig(path.join('projects', 'wdis', 'plots', 'player_wdis_dist.png'),
              bbox_inches='tight', dpi=500)
