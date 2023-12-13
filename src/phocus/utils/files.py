"""Utils for dealing with files"""
import csv
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

import phocus.model.location
import phocus.utils
import phocus.utils.constants
from phocus.utils.constants import DATA_PATH, OUTPUT_PATH, LONG_ISLAND_LOCATIONS_CSV_PATH

logger = logging.getLogger(__name__)


def long_island_data():
    return pd.read_csv(LONG_ISLAND_LOCATIONS_CSV_PATH).values


def raw_elena_data():
    logger.info('Reading Elena Data')
    rows = set()
    with open(DATA_PATH / 'elena_routing_2018_input.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['name'] and row['address']:
                rows.add(phocus.utils.HashableDict(row))

    return rows


def save_formatted_elena_data(city='Long Island', state='NY'):
    import phocus.utils.maps  # Avoid circular import
    raw_data = raw_elena_data()
    logger.info('Requesting lat and long for raw data')
    locations = set()
    maps_utils = phocus.utils.maps.MapsUtils()
    for row in raw_data:
        coord = maps_utils.get_lat_long(row['address'], components={'administrative_area': state, 'country': 'US',
                                                                    'locality': row['town']})
        locations.add(phocus.model.location.Location(
            doctor_name=row['name'],
            address=row['address'],
            lat=coord.lat,
            lon=coord.long,
            city=city,
            state=state,
            is_repeat=row['repeat'].lower() == 'yes'
        ))

    location_dicts = [vars(location) for location in locations]
    with REAL_LONG_ISLAND_JSON_PATH.open(mode='w') as f:
        json.dump(location_dicts, f, indent=2)


def make_output_dir(path: Path = OUTPUT_PATH):
    path.mkdir(parents=True, exist_ok=True)
    return path


REAL_LONG_ISLAND_JSON_PATH = make_output_dir() / 'formatted_elena.json'
DISTANCE_MATRIX_PATH = make_output_dir() / 'distance.json'


def real_long_island_data():
    return phocus.model.location.load_locations(REAL_LONG_ISLAND_JSON_PATH)


def save_distance_matrix_data(distance_matrix: np.ndarray):
    with open(DISTANCE_MATRIX_PATH, "w") as f:
        distance_matrix_json = distance_matrix.tolist()
        json.dump(distance_matrix_json, f, indent=2)


if __name__ == '__main__':
    phocus.utils.bootstrap_project()
    save_formatted_elena_data()
