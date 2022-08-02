import pandas as pd
from os import path
from utilities import LICENSE_KEY, generate_token, get_players, get_sims

# parameters
SEASON = 2021
WEEK = 1
SCORING = {'qb': 'pass4', 'skill': 'ppr', 'dst': 'mfl'}

# get an access token
token = generate_token(LICENSE_KEY)['token']

USE_SAVED_DATA = True

# note: **SCORING same as passing qb='pass4', skill='ppr' ... to function
if USE_SAVED_DATA:
    players = get_players(token, **SCORING, season=SEASON,
                          week=WEEK).set_index('fantasymath_id')
else:
    players = (pd.read_csv(path.join('data', 'players.csv'))
        .set_index('fantasymath_id'))

players.head()

# use this list of player ids (players.index) to get all the simulations for
# this week

if USE_SAVED_DATA:
    sims = pd.read_csv(path.join('data', 'sims.csv'))
else:
    sims = get_sims(token, players=list(players.index), week=WEEK, season=SEASON,
                    nsims=1000, **SCORING)

sims.head()

sims.shape

sims['kyler-murray'].mean()
sims['kyler-murray'].median()

sims[['kyler-murray', 'patrick-mahomes']].head()

(sims['kyler-murray'] > sims['patrick-mahomes']).head()

(sims['kyler-murray'] > sims['patrick-mahomes']).mean()

(sims['kyler-murray'] >
         sims[['matthew-stafford', 'russell-wilson']].max(axis=1) + 11.5).mean()

sims['bb_qb'] = sims[['kyler-murray', 'matthew-stafford']].max(axis=1)
sims[['bb_qb', 'kyler-murray', 'matthew-stafford']].describe()

sims['bb_qb2'] = sims[['kyler-murray', 'matthew-stafford',
                       'kirk-cousins']].max(axis=1)
sims[['bb_qb2', 'bb_qb', 'kyler-murray', 'matthew-stafford',
      'kirk-cousins']].describe().round(2)

# correlations
sims[['kyler-murray', 'deandre-hopkins']].corr()

sims[['kyler-murray', 'ten-dst']].corr()

sims[['kyler-murray', 'deandre-hopkins', 'ten-dst']].corr()

(sims[['kyler-murray', 'ryan-tannehill', 'deandre-hopkins', 'aaron-rodgers',
    'ten-dst']] .corr()
 .round(2))

sims['deandre-hopkins'].describe()

pd.concat([
    sims.loc[sims['kyler-murray'] > 30, 'deandre-hopkins'].describe(),
    sims.loc[sims['kyler-murray'] < 12, 'deandre-hopkins'].describe()], axis=1)

(sims['aaron-rodgers'] > sims['russell-wilson']).mean()

(sims[['aaron-rodgers', 'tyler-lockett']].sum(axis=1) > 60).mean()

(sims[['russell-wilson', 'tyler-lockett']].sum(axis=1) > 60).mean()
