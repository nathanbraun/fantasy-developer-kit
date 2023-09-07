import pandas as pd
from os import path
from utilities import (LICENSE_KEY, generate_token, get_players, get_sims,
    name_sims)

# parameters
SEASON = 2022
WEEK = 1
SCORING = {'qb': 'pass_4', 'skill': 'ppr_1', 'dst': 'dst_std'}

# get an access token
token = generate_token(LICENSE_KEY)['token']

players = get_players(token, season=2022, week=1,
                      **SCORING).set_index('player_id')

USE_SAVED_DATA = True

# note: **SCORING same as passing qb='pass4', skill='ppr' ... to function
if USE_SAVED_DATA:
    players = (pd.read_csv(path.join('data', 'players.csv'))
        .set_index('fantasymath_id'))
else:
    players = get_players(token, **SCORING, season=SEASON,
                          week=WEEK).set_index('player_id')

# use this list of player ids (players.index) to get all the simulations for
# this week

if USE_SAVED_DATA:
    sims = pd.read_csv(path.join('data', 'sims.csv'))
else:
    sims = get_sims(token, players=list(players.index), week=WEEK, season=SEASON,
                    nsims=500, **SCORING)

sims.head()

# who is player 165
players.loc[[165, 172]]

sims = name_sims(sims, players)
sims.head()

sims['justin-herbert'].mean()
sims['justin-herbert'].median()

sims[['justin-herbert', 'patrick-mahomes']].head()

(sims['justin-herbert'] > sims['patrick-mahomes']).head()

(sims['justin-herbert'] > sims['patrick-mahomes']).mean()

(sims['justin-herbert'] >
         sims[['matthew-stafford', 'russell-wilson']].max(axis=1) + 11.5).mean()

sims['bb_qb'] = sims[['justin-herbert', 'matthew-stafford']].max(axis=1)
sims[['bb_qb', 'justin-herbert', 'matthew-stafford']].describe()

sims['bb_qb2'] = sims[['justin-herbert', 'matthew-stafford',
                       'kirk-cousins']].max(axis=1)
sims[['bb_qb2', 'bb_qb', 'justin-herbert', 'matthew-stafford',
      'kirk-cousins']].describe().round(2)

# correlations
sims[['justin-herbert', 'keenan-allen']].corr()

sims[['justin-herbert', 'lv']].corr()

sims[['justin-herbert', 'keenan-allen', 'lv']].corr()

(sims[['justin-herbert', 'derek-carr', 'keenan-allen', 'aaron-rodgers', 'lv']]
    .corr()
 .round(2))

sims['keenan-allen'].describe()

pd.concat([
    sims.loc[sims['justin-herbert'] > 30, 'keenan-allen'].describe(),
    sims.loc[sims['justin-herbert'] < 12, 'keenan-allen'].describe()], axis=1)

(sims['aaron-rodgers'] > sims['matthew-stafford']).mean()

(sims[['aaron-rodgers', 'cooper-kupp']].sum(axis=1) > 50).mean()

(sims[['matthew-stafford', 'cooper-kupp']].sum(axis=1) > 50).mean()
