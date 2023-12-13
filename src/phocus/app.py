import logging
import os
from typing import Sequence

import numpy as np
import pendulum
from connexion.resolver import RestyResolver
import connexion

from phocus.cp.cp_app import run_model
from phocus.model.appointment import Appointment
from phocus.model.location import Location
from phocus.model.work_period import WorkPeriod
from phocus.utils import bootstrap_project
from phocus.utils.api_validator import APIValidator, start_location_validator
from phocus.utils.constants import END_LOCATION, START_LOCATION, LOCATIONS
from phocus.utils.date_utils import combine_periods, convert_open_times_to_blackout_windows, \
    convert_date_time_to_epoch_millis, are_periods_overlapping
from phocus.utils.maps import lat_lon

HOST = os.environ.get('API_HOST', 'localhost:8080')
logger = logging.getLogger(__name__)


def recalculate_lat_lon(doctor):
    result = doctor.copy()
    if not doctor.address:
        raise RuntimeError('Doctor should have an address')
    result.lat, result.lon = lat_lon(doctor.address)
    return result


def parse_period(period_dict) -> pendulum.Period:
    """Parse an API Period parameter

    If the end is before the start; raises a RuntimeError"""
    period = pendulum.from_timestamp(period_dict['end'] / 1000) - pendulum.from_timestamp(period_dict['start'] / 1000)
    if period.start >= period.end:
        raise RuntimeError('Periods should end after start but found %s -> %s' % (period.start, period.end))
    return period


def parse_and_combine_periods(period_dict_list) -> Sequence[pendulum.Period]:
    return combine_periods([parse_period(x) for x in period_dict_list])


def location_from_dict(d, work_periods=None, include_blackout_windows=True):
    loc = Location(
        d['name'],
        d.get('address', ''),
        d.get('lat'),
        d.get('lon'),
    )

    loc.id = d['id']

    if 'numTotalVisits' in d:
        loc.num_total_visits = d['numTotalVisits']
        loc.min_visit_gap_days = d.get('minVisitGapDays', 1)
    if 'visitTimeSeconds' in d:
        loc.visit_time_seconds = d['visitTimeSeconds']
    if 'skipCostMultiplier' in d:
        loc.skip_cost_multiplier = d['skipCostMultiplier']
    if 'isRequired' in d:
        loc.is_required = d['isRequired']

    if include_blackout_windows:
        open_times = parse_and_combine_periods(d.get('openTimes', []))
        loc.blackout_windows = convert_open_times_to_blackout_windows(
            open_times=open_times,
            work_periods=work_periods,
        )

    return loc


def location_to_dict(location):
    d = {k: v for k, v in vars(location).items() if v is not None}
    d['name'] = location.doctor_name
    del d['doctor_name']
    if 'blackout_windows' in d:
        del d['blackout_windows']

    d['arrival_time'] = convert_date_time_to_epoch_millis(pendulum.parse(d['arrival_time']))
    d['end_time'] = convert_date_time_to_epoch_millis(pendulum.parse(d['end_time']))

    if 'time_off_period' in d:
        del d['time_off_period']

    return d


def make_validator():
    validator = APIValidator()
    validator.validators.append(start_location_validator)
    return validator


app_validator = make_validator()


# noinspection PyPep8Naming
def plan_route(routeParams: dict) -> dict:
    """
    Plan the route
    :param routeParams: The parameters for the route planning. If overrides is a key, those will be passed directly to run_model
    :return:
    """
    logger.info('Plan Route called with %s', routeParams)

    app_validator.validate(routeParams)

    params = APIParams(routeParams)
    work_periods = params.work_periods

    args = {
        LOCATIONS: params.locations,
        'distance_matrix': params.distance_matrix,
        'appointments': params.appointments,
        'time_limit_ms': routeParams['maxRunMillis'],
        'lunch_hour_start': routeParams['lunchStartHour'],
        'lunch_minutes': routeParams['lunchMinutes'],
        'work_periods': work_periods,
    }

    if 'solutionName' in routeParams:
        args['solution_name'] = routeParams['solutionName']

    args.update(routeParams.get('overrides', {}))

    solution = run_model(**args)
    metrics = solution.metrics
    route_location_ids = {location.id for location in solution.route}
    original_location_ids = {location.id for location in params.locations}

    result = {
        'route': [location_to_dict(loc) for loc in solution.route],
        'metrics': metrics,
        'unroutedLocationIDs': sorted(original_location_ids - route_location_ids),
    }

    return result


class APIParams:
    """Wrapper for API params

    Things should gradually be refactored to use this"""
    def __init__(self, api_json):
        self.params = api_json
        self._work_periods = None

        # Get start and end locations
        self.start_and_end_location_ids = set()
        for wp in self.params['workPeriods']:
            self.start_and_end_location_ids.add(wp[START_LOCATION])
            self.start_and_end_location_ids.add(wp[END_LOCATION])

        # Parse Doctor Locations
        self.appointments = []
        self.locations = []
        for doctor_dict in self.params[LOCATIONS]:
            if doctor_dict['id'] in self.start_and_end_location_ids:
                loc = location_from_dict(
                    doctor_dict,
                    include_blackout_windows=False
                )
                loc.visit_time_seconds = 0

            else:
                loc = location_from_dict(
                    doctor_dict,
                    work_periods=self.work_periods,
                )

                # Parse Appointments
                if 'appointment' in doctor_dict:
                    appointment = doctor_dict['appointment']
                    self.appointments.append(Appointment(
                        loc,
                        pendulum.from_timestamp(appointment['start'] / 1000),
                        pendulum.from_timestamp(appointment['end'] / 1000),
                    ))
            self.locations.append(loc)

        self.id_to_locations_idx = {loc.id: idx for idx, loc in enumerate(self.locations)}

        # FIXME adjust time off for start and end nodes
        # FIXME need to duplicate any repeated work period nodes

        # Parse distances
        self.distance_matrix = self._parse_distance_matrix()

    def _parse_distance_matrix(self):
        distances = self.params['distances']
        expected_num_distances = len(self.locations) * len(self.locations)
        if len(distances) != expected_num_distances:
            return 'Expected %d distances but got %d' % (expected_num_distances, len(distances)), 400

        distance_matrix = np.zeros(shape=(len(self.locations), len(self.locations)), dtype=np.int)
        for distance_pair in distances:
            origin_id = distance_pair['originId']
            dest_id = distance_pair['destId']
            distance = distance_pair['distance']
            distance_matrix[self.id_to_locations_idx[origin_id], self.id_to_locations_idx[dest_id]] = distance

        # Adjust distance matrix for start and end nodes
        # All start nodes should have distances to them as 0 and all end nodes should have distances leaving them as 0
        for wp in self.work_periods:
            start_index = self.id_to_locations_idx[wp.start_location_id]
            distance_matrix[:, start_index] = 0
            end_index = self.id_to_locations_idx[wp.end_location_id]
            distance_matrix[end_index, :] = 0

        return distance_matrix

    def location_from_id(self, id):
        return self.locations[self.id_to_locations_idx[id]]

    @property
    def work_periods(self):
        if self._work_periods:
            return self._work_periods

        self._work_periods = []

        for wp in self.params['workPeriods']:
            period = parse_period(wp)
            start_loc_id = wp[START_LOCATION]
            end_loc_id = wp['endLocation']
            self._work_periods.append(WorkPeriod(period.start, period.end, start_loc_id, end_loc_id))

        self._work_periods.sort()

        if not self._work_periods:
            raise RuntimeError('Expected at least one work period')

        if are_periods_overlapping(self._work_periods):
            raise RuntimeError('Overlapping work times are not supported')

        for period in self._work_periods:
            if period.start >= period.end:
                raise RuntimeError('Work periods should end after start but found %s -> %s' % (period.start, period.end))

        return self._work_periods


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
