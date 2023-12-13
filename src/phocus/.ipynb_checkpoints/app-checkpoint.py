import logging
import os

import numpy as np
import pendulum
from connexion.resolver import RestyResolver
import connexion

from phocus.cp.cp_app import run_model
from phocus.model.appointment import Appointment
from phocus.model.location import Location
from phocus.utils import bootstrap_project
from phocus.utils.date_utils import combine_periods, convert_open_times_to_blackout_windows
from phocus.utils.maps import lat_lon

HOST = os.environ.get('API_HOST', 'localhost:8080')
logger = logging.getLogger(__name__)


def recalculate_lat_lon(doctor):
    result = doctor.copy()
    if not doctor.address:
        raise RuntimeError('Doctor should have an address')
    result.lat, result.lon = lat_lon(doctor.address)
    return result


def location_from_dict(d, start_datetime=None, work_time_delta=None, days=None, include_blackout_windows=True):
    loc = Location(
        d['name'],
        d.get('address', ''),
        d.get('lat'),
        d.get('lon'),
    )
    if 'id' in d:
        loc.id = d['id']
    if 'numTotalVisits' in d:
        loc.num_total_visits = d['numTotalVisits']
        loc.min_visit_gap_days = d.get('minVisitGapDays', 1)

    if include_blackout_windows:
        open_times = combine_periods([pendulum.parse(x['end']) - pendulum.parse(x['start'])
                                      for x in d.get('openTimes', [])])
        loc.blackout_windows = convert_open_times_to_blackout_windows(
            open_times=open_times,
            start_datetime=start_datetime,
            work_time_delta=work_time_delta,
            days=days,
        )

    return loc


def location_to_dict(location):
    d = {k: v for k, v in vars(location).items() if v is not None}
    d['name'] = location.doctor_name
    del d['doctor_name']
    if 'blackout_windows' in d:
        del d['blackout_windows']
    return d


# noinspection PyPep8Naming
def plan_route(routeParams: dict) -> dict:
    """
    Plan the route
    :param routeParams: The parameters for the route planning. If overrides is a key, those will be passed directly to run_model
    :return:
    """
    # TODO validate that open times are after close times
    logger.info('Plan Route called with %s', routeParams)

    start_datetime = pendulum.parse(routeParams['startDateTime'])
    work_time_delta = pendulum.duration(minutes=routeParams['workTimeMinutes'])
    days = routeParams['numDays']

    # Locations with startLocation as first item
    locations = [location_from_dict(routeParams['startLocation'], include_blackout_windows=False)]

    # Parse Doctor Locations
    appointments = []
    for doctor_dict in routeParams['locations']:
        loc = location_from_dict(
            doctor_dict,
            start_datetime=start_datetime,
            work_time_delta=work_time_delta,
            days=days,
        )
        locations.append(loc)

        # Parse Appointments
        if 'appointment' in doctor_dict:
            appointment = doctor_dict['appointment']
            appointments.append(Appointment(
                loc,
                pendulum.parse(appointment['start']),
                pendulum.parse(appointment['end']),
            ))

    # Parse distances
    distances = routeParams['distances']
    expected_num_distances = len(locations) * len(locations)
    if len(distances) != expected_num_distances:
        return 'Expected %d distances but got %d' % (expected_num_distances, len(distances)), 400

    id_to_locations_idx = {loc.id: idx for idx, loc in enumerate(locations)}

    distance_matrix = np.zeros(shape=(len(locations), len(locations)), dtype=np.int)
    for distance_pair in distances:
        origin_id = distance_pair['originId']
        dest_id = distance_pair['destId']
        distance = distance_pair['distance']
        distance_matrix[id_to_locations_idx[origin_id], id_to_locations_idx[dest_id]] = distance

    args = {
        'locations': locations,
        'distance_matrix': distance_matrix,
        'start_datetime': start_datetime,
        'appointments': appointments,
        'work_time_delta': work_time_delta,
        'days': days,
        'time_limit_ms': routeParams['maxRunMillis'],
        'service_time_duration': pendulum.duration(minutes=routeParams['serviceTimeMinutes']),
        'lunch_hour_start': routeParams['lunchStartHour'],
        'lunch_minutes': routeParams['lunchMinutes']
    }

    if 'solutionName' in routeParams:
        args['solution_name'] = routeParams['solutionName']

    args.update(routeParams.get('overrides', {}))

    solution = run_model(**args)
    metrics = solution.metrics
    result = {
        'route': [location_to_dict(loc) for loc in solution.route],
        'metrics': {
            'numDays': metrics['num_days'],
            'doctorsVisited': metrics['doctors_visited'],
            'candidateDoctors': metrics['candidate_doctors'],
            'travel_time': metrics['travel_time'],
            'avgTravelTime': metrics['avg_travel_time'],
            'runningTime': metrics['running_time']
        }
    }
    return result


def index():
    """Empty index for root of API for health checks"""
    return "ok"


if __name__ == '__main__':
    bootstrap_project()
    app = connexion.App(__name__)
    app.add_api(
        'swagger.yaml',
        resolver=RestyResolver('phocus.app'),
        arguments={'host': HOST},
        strict_validation=True,
    )
    app.run(host='0.0.0.0', port=8080, threaded=True)
