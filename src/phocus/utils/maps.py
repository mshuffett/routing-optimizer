import logging
import math
import os
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Sequence, Optional

import googlemaps
import numpy as np

import pendulum
import progressbar
from tenacity import retry, wait_random_exponential, stop_after_delay

from phocus.utils.mixins import Base
from phocus.utils import memory


_client = None


def get_client():
    global _client
    if not _client:
        api_key = os.environ.get('GOOGLE_API_KEY')
        _client = googlemaps.Client(key=api_key)

    return _client


Coordinate = namedtuple('Coordinate', 'lat long')
NEXT_MONDAY_8_AM_EASTERN = pendulum.now('US/Eastern').next(pendulum.MONDAY).set(hour=8)

logger = logging.getLogger(__name__)


@memory.cache
def gmaps_distance_matrix(
    origins,
    destinations,
    departure_time=NEXT_MONDAY_8_AM_EASTERN,
    origin_offset=None,
    origin_end=None,
    dest_offset=None,
    dest_end=None,
):
    client = get_client()

    @retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_delay(5 * 60))
    def distance_matrix_with_retry():
        return client.distance_matrix(
            origins=origins,
            destinations=destinations,
            departure_time=departure_time,
        ), origin_offset, origin_end, dest_offset, dest_end

    return distance_matrix_with_retry()


class AmbiguousAddressError(RuntimeError):
    """The address was ambiguous"""
    pass


@memory.cache
def lat_lon(address, components=None):
    client = get_client()
    logger.info('Getting lat and long from %s', address)
    result = client.geocode(address, components=components)
    if len(result) == 0:
        raise RuntimeError("Address Not Found: %d" % address)
    else:
        location = result[0]['geometry']['location']
        coordinates = Coordinate(lat=location['lat'], long=location['lng'])
        if len(result) != 1:
            addresses = set(x['formatted_address'] for x in result)
            if len(addresses) > 1:
                raise AmbiguousAddressError('Expected length of result to be 1 but was %d. Address: %s' % (len(result), address))
    return coordinates


class MapsUtils(Base):
    @staticmethod
    def get_lat_long(address, components=None):
        return lat_lon(address, components=components)

    def get_distance_matrix(
        self,
        coordinates: Sequence[Coordinate],
        departure_time: Optional[pendulum.DateTime] = NEXT_MONDAY_8_AM_EASTERN,
    ) -> np.ndarray:

        num_locations = len(coordinates)
        self.log.info('Getting pairwise distance for %d locations', num_locations)
        distance_matrix = np.zeros(shape=(num_locations, num_locations), dtype=np.int)

        # Fetch one 10x10 block at a time
        futures = []
        with ThreadPoolExecutor(max_workers=5) as e:
            for left_idx in range(int(math.ceil(num_locations / 10))):
                origin_offset = left_idx * 10
                origin_end = min(num_locations, origin_offset + 10)
                origin_query = coordinates[origin_offset: origin_end]
                for right_idx in range(int(math.ceil(num_locations / 10))):
                    dest_offset = right_idx * 10
                    dest_end = min(num_locations, dest_offset + 10)
                    dest_query = coordinates[dest_offset: dest_end]
                    futures.append(e.submit(
                        gmaps_distance_matrix,
                        origins=origin_query,
                        destinations=dest_query,
                        departure_time=departure_time,
                        origin_offset=origin_offset,
                        origin_end=origin_end,
                        dest_offset=dest_offset,
                        dest_end=dest_end,
                    ))

            bar = progressbar.ProgressBar(max_value=len(futures)).start()
            for i, completed_future in enumerate(as_completed(futures)):
                bar.update(i + 1)
                result, origin_offset, origin_end, dest_offset, dest_end = completed_future.result()
                result_matrix: Sequence[Sequence[int]] = list(map(
                    lambda row: list(map(
                        lambda el: el['duration']['value'],
                        row['elements']
                    )),
                    result['rows'],
                ))
                # Fill in corresponding block in the distance_matrix
                distance_matrix[origin_offset:origin_end, dest_offset:dest_end] = result_matrix

        return distance_matrix
