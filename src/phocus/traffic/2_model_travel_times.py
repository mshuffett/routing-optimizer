#!/usr/bin/env python

# author: jack chua
# description: model travel times

# using API data from long island, try to see if we can model
# travel times

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

_BASE_DIR = '/home/jack/source/traffic/'
_DATA_DATE = '20171104'
#_BASE_DIR = os.path.realpath(__file__)

data = pd.read_csv('%s/data/%s_training_data.csv' % (_BASE_DIR, _DATA_DATE))
X = data[['start_lat', 'start_lng', 'end_lat', 'end_lng', 'dists', 'departure_time']]
y = data['durs']
X_train, X_test, y_train, y_test = train_test_split(X,y, train_size=800)

regr = RandomForestRegressor(n_estimators=100, random_state=69)
regr.fit(X_train,y_train)

y_pred = regr.predict(X_test)
resid = y_pred - y_test

# plot residuals against actual hists
fig, (ax1,ax2) = plt.subplots(2,1)
pd.DataFrame(resid).hist(bins=50,ax=ax1)
data['durs'].hist(bins=100,ax=ax2)
plt.show()

pd.DataFrame(resid).describe()
