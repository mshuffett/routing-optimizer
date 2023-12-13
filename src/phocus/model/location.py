import json
from collections import namedtuple
from logging import getLogger
from math import radians, cos, sin, asin, sqrt
from typing import Sequence, Dict

import pendulum

from phocus.utils.decorators import auto_assign_arguments
from phocus.utils.mixins import Base

logger = getLogger(__name__)
Doctor = namedtuple('Doctor', 'name address lat lon')


class Location(Base):
    @auto_assign_arguments
    def __init__(self, doctor_name, address, lat, lon, city=None, state=None, is_repeat=False, is_duplicate_origin=False, **kwargs):
        pass

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        return '<Location: %s>' % self.id

    def __copy__(self):
        return Location(**vars(self))

    def copy(self):
        return self.__copy__()

    def is_same_doctor(self, other):
        return self.key() == other.key()

    def key(self) -> Doctor:
        """Get a unique key for this location consisting of doctor_name, address, lat, lon"""
        return self.id


def locations_dicts(locations, blacklist={'blackout_windows', '_logger', 'time_off_period'}):
    """Get a dictionary per location omitting the blacklist fields"""
    return [{k: v for k, v in vars(loc).items() if k not in blacklist} for loc in locations]


def save_locations(locations, path):
    """Saves `locations` to `path`. Skips keys that cannot be converted."""
    dicts = locations_dicts(locations)
    with open(path, mode='w') as f:
        json.dump(dicts, f, indent=2, skipkeys=True)


def load_locations(path):
    logger.info('Loading locations from %s', path)

    with open(path) as f:
        location_json = json.load(f)

    locations = []
    for lj in location_json:
        kwargs = {}
        for key, value in lj.items():
            value = value.strip() if isinstance(value, str) else value
            kwargs[key] = value

        # Parse blackout_windows
        if 'blackout_windows' in kwargs:
            blackout_windows = []
            for window in kwargs['blackout_windows']:
                start = pendulum.parse(window['start'])
                end = pendulum.parse(window['end'])
                blackout_windows.append(end - start)
            kwargs['blackout_windows'] = blackout_windows

        # Allow locations to miss lat and lon
        try:
            locations.append(Location(**kwargs))
        except TypeError:
            if 'lat' in kwargs and 'lon' in kwargs:
                raise
            logger.info('Location "%s" was missing lat and lon', kwargs['doctor_name'])

    logger.info('%d out of %d locations loaded', len(locations), len(location_json))
    return locations


def haversine_distance(l1: Location, l2: Location):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lat1, lat2, lon1, lon2 = map(radians, [l1.lat, l2.lat, l1.lon, l2.lon])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    # Radius of earth in kilometers is 6371
    km = 6371 * c
    return km * 1000


def convert_date_str(date_str: str) -> pendulum.DateTime:
    """Convert a date string like arrival time into a datetime"""
    try:
        return pendulum.from_format(date_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return pendulum.parse(date_str)


def find_location_by_name(locations: Sequence[Location], name: str) -> Location:
    for location in locations:
        if location.doctor_name == name:
            return location

    raise RuntimeError('Expected to find %s', name)
