#!/usr/bin/env python
#
# author: jack chua
# description: get data for a salesperson's block

import json
import os
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd
import requests

# TODO: include parameters for salesperson territory corners
# TODO: include sampling method for picking random dates / times

# personal key
_BASE_DIR = os.path.realpath(__file__)
_GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']
_BASE_URL = 'https://maps.googleapis.com/maps/api/distancematrix/json?'
_CORNERS = [
    (40.586779, -73.979895),
    (40.719617, -73.906424)
]
_TS_OF_INTEREST = [
    # 8AM ET, 11/1-11/4
    1509710400,
    1509537600,
    1509624000,
    1509537600,
    # 12PM ET, 11/1-11/4
    1509508800,
    1509595200,
    1509681600,
    1509768000,
    # 4PM ET, 11/1-11/4
    1509523200,
    1509609600,
    1509696000,
    1509782400
]
_API_THROTTLE_IN_SECS = 5


# generate a set of coordinates within the corners
# of a salesperson's territory and create pairs between them
def generate_coord_pairs(num_pairs=500):
    min_lat = min([x[0] for x in _CORNERS])
    max_lat = max([x[0] for x in _CORNERS])
    min_lng = min([x[1] for x in _CORNERS])
    max_lng = max([x[1] for x in _CORNERS])

    res = []
    for i in range(0, num_pairs):
        start_lat = np.random.uniform(min_lat, max_lat)
        start_lng = np.random.uniform(min_lng, max_lng)
        end_lat = np.random.uniform(min_lat, max_lat)
        end_lng = np.random.uniform(min_lng, max_lng)
        res.append(((start_lat, start_lng), (end_lat, end_lng)))

    return res


# ping matrix API
def get_distance_matrix_response(coord_pairs, departure_time=None):
    N = len(coord_pairs)
    if N > 25:
        sys.exit('API can only handle 25 coordinate pairs at most!')
    origins = [x[0] for x in coord_pairs]
    origins = [','.join(map(str, x)) for x in origins]
    dests = [x[1] for x in coord_pairs]
    dests = [','.join(map(str, x)) for x in dests]
    if departure_time:
        payload = {
            'origins': '|'.join(origins),
            'destinations': '|'.join(dests),
            'mode': 'driving',
            'departure_time': departure_time,
            'api_key': _GOOGLE_API_KEY
        }
    else:
        payload = {
            'origins': '|'.join(origins),
            'destinations': '|'.join(dests),
            'mode': 'driving',
            'api_key': _GOOGLE_API_KEY
        }

    resp = requests.get(_BASE_URL, params=payload)

    # TODO: handle throttling limits / incorrect responses

    # construct the dataset
    data = json.loads(resp.text)
    res = []
    for idx, r in enumerate(data['rows']):
        dists = [x['distance']['value'] for x in r['elements']]
        durs = [x['duration']['value'] for x in r['elements']]
        status = [x['status'] for x in r['elements']]
        start_loc = [coord_pairs[idx][0]] * N
        start_lat = [x[0] for x in start_loc]
        start_lng = [x[1] for x in start_loc]
        end_loc = [x[1] for x in coord_pairs]
        end_lat = [x[0] for x in end_loc]
        end_lng = [x[1] for x in end_loc]
        start_adr = [data['origin_addresses'][idx]] * N
        end_adr = data['destination_addresses']
        ts = [departure_time] * N
        obs = zip(start_lat, start_lng, end_lat, end_lng, start_adr, end_adr, dists, durs, status, ts)
        cols = ['start_lat', 'start_lng', 'end_lat', 'end_lng', 'start_adr', 'end_adr', 'dists', 'durs', 'status',
                'departure_time']
        obs = [dict(zip(cols, x)) for x in obs]
        res.append(obs)
    res = [i for s in res for i in s]
    res = pd.DataFrame(res)

    return res


def main():
    res = pd.DataFrame()

    # ping salesperson region across timestamps of interest
    for ts in _TS_OF_INTEREST:
        time.sleep(_API_THROTTLE_IN_SECS)
        coord_pairs = generate_coord_pairs(10)
        data = get_distance_matrix_response(coord_pairs, ts)
        res = pd.concat([res, data])

    # save final data frame
    curr_date = datetime.strftime(datetime.now(), '%Y%m%d')
    os.mkdir('%s/data/' % os.curdir)
    res.to_csv('%s/data/%s_training_data.csv' % (os.curdir, curr_date), index=False)


if __name__ == '__main__':
    main()
