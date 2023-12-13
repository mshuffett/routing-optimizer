import copy
import json
from collections import Counter

import pendulum
import pytest
from typing import List

from joblib import Parallel, delayed

from phocus.app import plan_route
from phocus.errors import SolutionError
from phocus.utils.constants import TEST_DATA_PATH
from phocus.utils.date_utils import convert_epoch_millis_to_date_time


@pytest.fixture
def params():
    with open(TEST_DATA_PATH / 'simple_api_input.json') as f:
        return json.load(f)


@pytest.fixture
def full_params():
    with open(TEST_DATA_PATH / 'full_api_input.json') as f:
        return json.load(f)


@pytest.fixture
def full_freq():
    with open(TEST_DATA_PATH / 'full_api_frequency.json') as f:
        return json.load(f)


@pytest.fixture
def full_freq_across_weekend():
    with open(TEST_DATA_PATH / 'full_api_frequency_across_weekend.json') as f:
        return json.load(f)


@pytest.fixture
def full_freq_gap_day_zero():
    with open(TEST_DATA_PATH / 'full_api_frequency_gap_day_zero.json') as f:
        return json.load(f)


@pytest.fixture
def full_freq_every_day():
    with open(TEST_DATA_PATH / 'full_api_frequency_every_day_fo.json') as f:
        return json.load(f)


@pytest.fixture
def full_freq_every_day_plus_one():
    with open(TEST_DATA_PATH / 'full_api_frequency_every_day_fo_plus_one.json') as f:
        return json.load(f)


@pytest.fixture
def frequency_params():
    with open(TEST_DATA_PATH / 'full_api_frequency_four_days.json') as f:
        return json.load(f)


def route_arrival_dates(route) -> List[pendulum.Date]:
    """Gets the unique arrival date strings for the route"""
    return sorted({location_arrival_date(loc) for loc in route})


def location_arrival_date(loc):
    return convert_epoch_millis_to_date_time(loc['arrival_time']).date()


def location_visit_time(loc) -> int:
    arrival_time = convert_epoch_millis_to_date_time(loc['arrival_time'])
    end_time = convert_epoch_millis_to_date_time(loc['end_time'])
    return (end_time - arrival_time).in_seconds()


def test_simple_plan_route(params):
    result = plan_route(params)
    metrics = result['metrics']
    assert metrics['doctors_visited'] == 1
    assert len(route_arrival_dates(result['route'])) == 1
    assert location_visit_time(result['route'][1]) == 20 * 60, 'Default visit time should be 20 minutes'
    assert result['unroutedLocationIDs'] == []


def test_frequency_plan_route(frequency_params):
    result = plan_route(frequency_params)
    metrics = result['metrics']
    assert metrics['doctors_visited'] == 2
    assert len(route_arrival_dates(result['route'])) == 4


def test_full_api(full_params):
    result = plan_route(full_params)
    metrics = result['metrics']
    assert metrics['doctors_visited'] > 50
    assert len(route_arrival_dates(result['route'])) == 5


def test_full_api_frequency(full_freq):
    result = plan_route(full_freq)
    metrics = result['metrics']
    assert metrics['doctors_visited'] > 50
    assert len(route_arrival_dates(result['route'])) == 5


def test_full_api_frequency_over_weekend(full_freq_across_weekend):
    result = plan_route(full_freq_across_weekend)
    metrics = result['metrics']
    assert metrics['doctors_visited'] > 50
    assert len(route_arrival_dates(result['route'])) == 6

    # Verify that Fo, Corey is visited twice on the only possible days (each monday)
    route = result['route']
    fo_instances = [loc_dict for loc_dict in route if loc_dict['name'] == 'Fo, Corey']
    assert len(fo_instances) == 2
    assert str(location_arrival_date(fo_instances[0])) == '2018-06-18'
    assert str(location_arrival_date(fo_instances[1])) == '2018-06-25'

    # Verify unrouted locations
    original_location_ids = set([loc['id'] for loc in full_freq_across_weekend['locations']] + [full_freq_across_weekend['startLocation']['id']])
    route_location_ids = {loc['id'] for loc in route}
    expected_unrouted_ids = original_location_ids - route_location_ids
    assert len(expected_unrouted_ids) > 0
    assert set(result['unroutedLocationIDs']) == expected_unrouted_ids


def test_plan_route_fails_if_too_many_frequencies(full_freq):
    """We add frequency to every node where the route barely can fit in every node without frequency"""
    for loc in full_freq['locations']:
        loc['numTotalVisits'] = 2
        loc['minVisitGapDays'] = 1

    with pytest.raises(SolutionError):
        plan_route(full_freq)


def test_frequency_with_gap_day_zero_visits_on_same_day(full_freq_gap_day_zero):
    result = plan_route(full_freq_gap_day_zero)
    metrics = result['metrics']
    assert metrics['doctors_visited'] > 50
    assert len(route_arrival_dates(result['route'])) == 5

    # Verify that Fo, Corey is visited twice on the same day since he only has availability on that day
    route = result['route']
    fo_instances = [loc_dict for loc_dict in route if loc_dict['name'] == 'Fo, Corey']
    assert len(fo_instances) == 2

    # Make sure the dates are the same
    assert len(set(route_arrival_dates(fo_instances))) == 1


def test_frequency_with_visits_on_every_day(full_freq_every_day):
    result = plan_route(full_freq_every_day)
    metrics = result['metrics']
    assert metrics['doctors_visited'] > 50
    assert len(route_arrival_dates(result['route'])) == 5

    # Verify that Fo, Corey is visited every day
    route = result['route']
    fo_instances = [loc_dict for loc_dict in route if loc_dict['name'] == 'Fo, Corey']
    assert len(fo_instances) == 5

    # Make sure the dates are the same
    fo_dates = [str(rd) for rd in route_arrival_dates(fo_instances)]
    assert fo_dates == ['2018-06-18', '2018-06-19', '2018-06-20', '2018-06-21', '2018-06-22']


def test_frequency_with_visits_on_every_day_plus_one(full_freq_every_day_plus_one):
    with pytest.raises(SolutionError):
        plan_route(full_freq_every_day_plus_one)


def test_frequency_with_half_nodes_frequency_half_non_frequency(full_params):
    """Only the frequency ones should survive"""
    full_params['maxRunMillis'] = 5000
    # Pick the first 10 that have more than one day availability
    num_freq_added = 0
    for loc in full_params['locations']:
        if len(loc['openTimes']) > 1:
            loc['numTotalVisits'] = 2
            loc['minVisitGapDays'] = 1
            num_freq_added += 1
            if num_freq_added == 10:
                break

    result = plan_route(full_params)
    metrics = result['metrics']
    assert metrics['doctors_visited'] > 50
    assert len(route_arrival_dates(result['route'])) == 5

    route = result['route']
    doctor_counts = Counter(loc['name'] for loc in route if loc['name'] != 'Sam')
    repeat_counts = sum(1 for (e, count) in doctor_counts.items() if count > 1)

    assert repeat_counts == 10


def test_node_visit_time():
    with open(TEST_DATA_PATH / 'api_node_visit_time.json') as f:
        api_params = json.load(f)

    result = plan_route(api_params)
    metrics = result['metrics']
    assert metrics['doctors_visited'] > 50
    route = result['route']
    assert len(route_arrival_dates(route)) == 5

    # In the test set location names are suffixed with the number of minutes
    for location in route:
        name = location['name']
        try:
            duration = pendulum.Duration(minutes=int(name[-2:]))
            actual_visit_time = location_visit_time(location)
            assert duration.in_seconds() == actual_visit_time
        except ValueError:
            pass


def plan_routes(input_data: List, parallel=True):
    if parallel:
        return Parallel(n_jobs=len(input_data))(delayed(plan_route)(d) for d in input_data)
    else:
        return [plan_route(d) for d in input_data]


def load_json(filename):
    with open(TEST_DATA_PATH / filename) as f:
        return json.load(f)


def reset_all_skip_costs(input_json):
    result = copy.deepcopy(input_json)
    for location in result['locations']:
        if 'skipCostMultiplier' in location:
            del location['skipCostMultiplier']
    return result


def set_skip_cost(input_json, location_id, multiplier):
    result = copy.deepcopy(input_json)
    for location in result['locations']:
        if location['id'] == location_id:
            location['skipCostMultiplier'] = multiplier
            return result

    raise RuntimeError("Didn't find location_id in input_json")


class TestSkipCostMultiplier:
    def test_higher_multiplier_causes_node_to_not_be_visited(self):
        """Location 119602684 is not normally visited, but we added a 2x skip cost,
        so it should be visited. The test data set was based on the full_frequency_every_day test data.
        """
        # Compare against result with no multiplier
        with open(TEST_DATA_PATH / 'skip_cost_2x_no_skip_cost.json') as f:
            input_data = json.load(f)
        result = plan_route(input_data)
        metrics = result['metrics']
        original_visited = metrics['doctors_visited']
        assert original_visited > 50
        assert '119602684' in result['unroutedLocationIDs']

        with open(TEST_DATA_PATH / 'skip_cost_2x.json') as f:
            input_data = json.load(f)
        result = plan_route(input_data)
        metrics = result['metrics']
        assert abs(metrics['doctors_visited'] - original_visited) < 3
        assert '119602684' not in result['unroutedLocationIDs']

    def test_higher_multiplier_with_enough_capacity_has_no_effect(self):
        data = [
            load_json('skip_cost_high_capacity_no_skip_cost.json'),
            load_json('skip_cost_high_capacity.json'),
        ]
        results = plan_routes(data)

        # Compare against result with no multiplier
        doctors_visited = [result['metrics']['doctors_visited'] for result in results]
        assert abs(doctors_visited[0] - doctors_visited[1]) < 3
        assert doctors_visited[0] > 50


def test_top_level_and_work_period_start_location_raises_RuntimeError():
    """If the top level startLocation is passed and the workPeriod startLocation is passed an error is raised"""
    with open(TEST_DATA_PATH / 'start_location_top_and_work_period_api.json') as f:
        data = json.load(f)

    with pytest.raises(RuntimeError):
        plan_route(data)


def test_all_or_no_work_period_locations_present(params):
    del params['startLocation']
    params['workPeriods'] = json.loads("""
    [
        {
          "start": 1529326800000,
          "end": 1529355600000,
          "startLocation": {
            "address": "900 Madison St, Hewlett Neck, NY",
            "lat": 40.624505,
            "lon": -73.697592,
            "name": "Rep Name",
            "id": "start"
          },
          "endLocation": {
            "address": "900 Madison St, Hewlett Neck, NY",
            "lat": 40.624505,
            "lon": -73.697592,
            "name": "Rep Name",
            "id": "start"
          }
        },
        {
          "start": 1529413200000,
          "end": 1529442000000
        }
    ]
    """)

    with pytest.raises(RuntimeError):
        plan_route(params)

    params['workPeriods'] = json.loads("""
    [
        {
          "start": 1529326800000,
          "end": 1529355600000,
          "startLocation": {
            "address": "900 Madison St, Hewlett Neck, NY",
            "lat": 40.624505,
            "lon": -73.697592,
            "name": "Rep Name",
            "id": "start"
          },
          "endLocation": {
            "address": "900 Madison St, Hewlett Neck, NY",
            "lat": 40.624505,
            "lon": -73.697592,
            "name": "Rep Name",
            "id": "start"
          }
        },
        {
          "start": 1529413200000,
          "end": 1529442000000,
          "startLocation": {
            "address": "900 Madison St, Hewlett Neck, NY",
            "lat": 40.624505,
            "lon": -73.697592,
            "name": "Rep Name",
            "id": "start"
          }
        }
    ]
    """)

    with pytest.raises(RuntimeError):
        plan_route(params)

    params['workPeriods'] = json.loads("""
    [
        {
          "start": 1529326800000,
          "end": 1529355600000,
          "startLocation": {
            "address": "900 Madison St, Hewlett Neck, NY",
            "lat": 40.624505,
            "lon": -73.697592,
            "name": "Rep Name",
            "id": "start"
          },
          "endLocation": {
            "address": "900 Madison St, Hewlett Neck, NY",
            "lat": 40.624505,
            "lon": -73.697592,
            "name": "Rep Name",
            "id": "start"
          }
        },
        {
          "start": 1529413200000,
          "end": 1529442000000,
          "startLocation": {
            "address": "900 Madison St, Hewlett Neck, NY",
            "lat": 40.624505,
            "lon": -73.697592,
            "name": "Rep Name",
            "id": "start"
          },
          "endLocation": {
            "address": "900 Madison St, Hewlett Neck, NY",
            "lat": 40.624505,
            "lon": -73.697592,
            "name": "Rep Name",
            "id": "start"
          }
        }
    ]
    """)

    plan_route(params)


def test_different_start_and_end_locations():
    assert False
