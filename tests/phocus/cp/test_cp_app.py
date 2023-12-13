from typing import List
from unittest.mock import MagicMock

import numpy as np
import pendulum
import pytest

from phocus.cp.cp_app import run_model, CP, EXAMPLE_START_DATETIME, EXAMPLE_APPOINTMENTS
from phocus.model.location import convert_date_str
from phocus.utils.date_utils import is_weekday, is_weekend
from phocus.utils.files import real_long_island_data


@pytest.fixture(autouse=True)
def mock_distance_matrix(monkeypatch):
    def distance_f(coordinates):
        return np.random.randint(1, 50 * 60, size=(len(coordinates), len(coordinates)))

    monkeypatch.setattr('phocus.cp.cp_app.load_distance_matrix_data', distance_f)


@pytest.fixture
def mock_save(monkeypatch):
    mock_save_instance = MagicMock()
    monkeypatch.setattr('phocus.cp.cp_app.Solution.save', mock_save_instance)
    return mock_save_instance


def test_simple_one_day_solution(mock_save):
    days = 1
    work_periods = example_work_periods_skipping_weekends(days)
    solution = run_model(
        work_periods=work_periods,
        solution_name='Simple Solution',
        time_limit_ms=500,
        appointments=EXAMPLE_APPOINTMENTS
    )
    mock_save.assert_called_once()

    # Check to see if the appointment was present
    assert len(EXAMPLE_APPOINTMENTS) == 1
    appointment = EXAMPLE_APPOINTMENTS[0]
    found_appointment = False
    for location in solution.route:
        arrival_time = convert_date_str(location.arrival_time)
        end_time = convert_date_str(location.end_time)
        if (location.is_same_doctor(appointment.location)
            and appointment.start_time == arrival_time
            and appointment.end_time == end_time):
            found_appointment = True
            break
    assert found_appointment


def test_weekend_travel_time_solution(mock_save):
    days = 6
    work_periods = example_work_periods_skipping_weekends(days)
    solution = run_model(
        work_periods=work_periods,
        solution_name='Weekend Solution',
        time_limit_ms=1000,
    )
    mock_save.assert_called_once()

    # Make sure there is no travel during weekend
    origin = solution.route[0]
    for location in solution.route:
        if location.is_same_doctor(origin):
            continue
        arrival_time = convert_date_str(location.arrival_time)
        end_time = convert_date_str(location.end_time)
        travel_to_time = int(location.travel_to_time)
        assert is_weekday(arrival_time)
        assert is_weekday(end_time)
        assert is_weekday(arrival_time - pendulum.duration(seconds=travel_to_time))


def example_work_periods_skipping_weekends(days: int) -> List[pendulum.Period]:
    current_period = (EXAMPLE_START_DATETIME + pendulum.duration(hours=8)) - EXAMPLE_START_DATETIME
    work_periods = []

    for x in range(days):
        work_periods.append(current_period)
        current_period = (current_period.end + pendulum.duration(days=1)) - (current_period.start + pendulum.duration(days=1))
        while is_weekend(current_period.start) or is_weekend(current_period.end):
            current_period = (current_period.end + pendulum.duration(days=1)) - (current_period.start + pendulum.duration(days=1))
    return work_periods


def test_locations_with_duplicate_origins_with_no_weekend():
    locations = real_long_island_data()
    days = 3
    work_periods = example_work_periods_skipping_weekends(days)
    locations_with_duplicates, repeat_locations = CP._locations_with_duplicates_and_origin(locations, work_periods)

    origin = locations_with_duplicates[0]

    for location in locations_with_duplicates[-1 * days:]:
        assert location.is_same_doctor(origin)

    assert not locations_with_duplicates[-1 * days - 2].is_same_doctor(origin)
