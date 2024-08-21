import pandas as pd
from os import path
import seaborn as sns
from utilities import (LICENSE_KEY, generate_token, get_players, get_sims,
    name_sims, get_sims_from_file)

# parameters
SEASON = 2023
WEEK = 3
SCORING = {'qb': 'pass_4', 'skill': 'ppr_1', 'dst': 'dst_std'}

# get an access token
token = generate_token(LICENSE_KEY)['token']

players = get_players(token, **SCORING, season=SEASON,
                      week=WEEK).set_index('player_id')

players.head()

USE_SAVED_DATA = False

# note: **SCORING same as passing qb='pass4', skill='ppr' ... to function
if USE_SAVED_DATA:
    players = (pd.read_csv(path.join('data', 'players.csv'))
        .set_index('player_id'))
else:
    players = get_players(token, **SCORING, season=SEASON,
                          week=WEEK).set_index('player_id')

# use this list of player ids (players.index) to get all the simulations for
# this week

if USE_SAVED_DATA:
    sims = get_sims_from_file(path.join('data', 'sims.csv'))
else:
    sims = get_sims(token, players=list(players.index), week=WEEK, season=SEASON,
                    nsims=500, **SCORING)

sims.head()

# who is player 165
players.loc[[1091, 498]]

nsims = name_sims(sims, players)

nsims.head()

nsims['justin-herbert'].mean()
nsims['justin-herbert'].median()

nsims['justin-herbert'].describe(percentiles=[0.05, .25, .5, .75, .95])

g = sns.FacetGrid(nsims, aspect=2)
g = g.map(sns.kdeplot, 'justin-herbert', fill=True)
g.fig.subplots_adjust(top=0.9)
g.fig.suptitle("Justin Herbert's Fantasy Points Distribution - Wk 3, 2023")

nsims[['justin-herbert', 'patrick-mahomes']].head()

(nsims['justin-herbert'] > nsims['patrick-mahomes']).head()

(nsims['justin-herbert'] > nsims['patrick-mahomes']).mean()

nsims_long = nsims[['justin-herbert', 'patrick-mahomes']].stack().reset_index()
nsims_long.columns = ['sim_n', 'player', 'pts']

g = sns.FacetGrid(nsims_long, hue='player', aspect=2)
g.map(sns.kdeplot, 'pts', fill=True)
g.add_legend()
g.fig.subplots_adjust(top=0.9)
g.fig.suptitle("Herbert vs Mahomes Fantasy Points Distribution - Wk 3, 2023")

(nsims['justin-herbert'] >
         nsims[['matthew-stafford', 'justin-fields']].max(axis=1) + 11.5).mean()

nsims['bb_qb'] = nsims[['justin-herbert', 'matthew-stafford']].max(axis=1)
nsims[['bb_qb', 'justin-herbert', 'matthew-stafford']].describe()

nsims['bb_qb2'] = nsims[['justin-herbert', 'matthew-stafford',
                       'kirk-cousins']].max(axis=1)
nsims[['bb_qb2', 'bb_qb', 'justin-herbert', 'matthew-stafford',
      'kirk-cousins']].describe().round(2)

# projected vs actual vs % likelihood

players.head()

(25.68 > nsims['patrick-mahomes']).mean()

qbs = players.loc[players['pos'] == 'QB']
qbs['proj'] = sims.mean().round(2)


qbs.sort_values('proj', ascending=False).head(15)[['name', 'proj', 'actual']]

def fpts_percentile(row):
    return (row['actual'] > sims[row.name]).mean()

qbs['pctile'] = qbs.apply(fpts_percentile, axis=1)

qbs.sort_values('proj', ascending=False).head(15)[['name', 'proj', 'actual',
                                                   'pctile']]

qbs['pctile'].describe(percentiles=[.1, .2, .3, .4, .5, .6, .7, .8, .9])

qbs.sort_values('pctile', ascending=False).head(10)[['name', 'proj', 'actual',
                                                     'pctile']]

qbs.sort_values('pctile', ascending=False).tail(10)[['name', 'proj', 'actual',
                                                     'pctile']]

qbs.sort_values('actual', ascending=False).head(10)[['name', 'proj', 'actual',
                                                     'pctile']]

# correlations
nsims[['justin-herbert', 'keenan-allen']].corr()

nsims[['justin-herbert', 'min']].corr()

nsims[['justin-herbert', 'keenan-allen', 'min']].corr()

nsims[['justin-herbert', 'kirk-cousins', 'keenan-allen', 'justin-jefferson',
       'min', 'jordan-love']].corr().round(2)

nsims['keenan-allen'].describe()

pd.concat([
    nsims.loc[nsims['justin-herbert'] > 30, 'keenan-allen'].describe(),
    nsims.loc[nsims['justin-herbert'] < 12, 'keenan-allen'].describe()], axis=1)

# who should i start monday night
print((nsims['mike-evans'] > nsims['tee-higgins']).mean())

print((nsims[['joe-burrow', 'mike-evans']].sum(axis=1) > 50).mean())

print((nsims[['joe-burrow', 'tee-higgins']].sum(axis=1) > 50).mean())

# offense or defense as underog or favorite
nsims[['min', 'pit']].describe()

nsims[['justin-herbert', 'min', 'pit']].corr()

print((nsims[['geno-smith', 'pit']].sum(axis=1) >
    nsims[['justin-herbert', 'dal']].sum(axis=1)).mean())

print((nsims[['geno-smith', 'min']].sum(axis=1) >
    nsims[['justin-herbert', 'ne']].sum(axis=1)).mean())

print((nsims[['patrick-mahomes', 'pit']].sum(axis=1) >
    nsims[['justin-herbert', 'dal']].sum(axis=1)).mean())

print((nsims[['patrick-mahomes', 'min']].sum(axis=1) >
    nsims[['justin-herbert', 'dal']].sum(axis=1)).mean())

(sims['aaron-rodgers'] > sims['matthew-stafford']).mean()

(sims[['aaron-rodgers', 'cooper-kupp']].sum(axis=1) > 50).mean()

(sims[['matthew-stafford', 'cooper-kupp']].sum(axis=1) > 50).mean()


################################################################################
## note: this part isn't meant to be run (why it's commented out)
## just querying and saving the data we use above
## including here so you can see it just comes from the API
################################################################################

# ## get data
# players = get_players(token, **SCORING, season=SEASON,
#                       week=WEEK).set_index('player_id')
# sims = get_sims(token, players=list(players.index), week=WEEK, season=SEASON,
#                 nsims=500, **SCORING)
#
# ## save it
# players.to_csv(path.join('data', 'players.csv'))
# sims.to_csv(path.join('data', 'sims.csv'), index=False)
#
