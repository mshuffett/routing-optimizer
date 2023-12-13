"""Validate a given solution"""
from collections import defaultdict

import pendulum
from typing import Sequence

import phocus.cp.cp_app
from phocus.errors import InvalidSolutionError
from phocus.model.appointment import Appointment
from phocus.model.location import Location, convert_date_str
from phocus.model.solution import Solution
from phocus.utils.mixins import Base


def _period_from_solution(solution_location) -> pendulum.Period:
    return pendulum.parse(solution_location.end_time) - pendulum.parse(solution_location.arrival_time)


class SolutionValidator(Base):
    def __init__(
            self,
            appointments: Sequence[Appointment],
            locations: Sequence[Location],
            repeat_locations: 'Sequence[phocus.cp.cp_app.RepeatLocation]',
            solution: Solution
    ):
        self.appointments = appointments
        self.locations = locations
        self.repeat_locations = repeat_locations
        self.solution = solution

    def _is_location_an_appointment(self, location: Location):
        return any(location.is_same_doctor(loc) for loc in self.solution.route)

    def _validate_location_blackout_windows(self):
        solution_route_by_key = {loc.key(): loc for loc in self.solution.route}
        input_doctors_by_key = {doc.key(): doc for doc in self.locations}
        invalid_solutions = []
        for key, loc in solution_route_by_key.items():
            doc = input_doctors_by_key.get(key)
            if not doc:
                continue
            solution_period = _period_from_solution(loc)
            blackouts: Sequence[pendulum.Period] = getattr(doc, 'blackout_windows', [])
            for blackout in blackouts:
                # offset times so that they don't return a false positive on overlap due to inclusive check
                blackout = (blackout.end - pendulum.duration(seconds=1)) - blackout.start
                if solution_period.start in blackout or solution_period.end in blackout or (solution_period.start < blackout.start and solution_period.end > blackout.end):
                    invalid_solutions.append(
                        f'Solution ({solution_period}) for doctor ({doc}) was in blackout ({blackout})')

        return invalid_solutions

    def _validate_repeat_visits(self):
        error_messages = []
        for rep in self.repeat_locations:
            original_location = self.locations[rep.original_idx]
            name = original_location.doctor_name
            location_instances = [l for l in self.locations if l.is_same_doctor(original_location)]
            # Make sure we have the right number of repeats
            # Add 1 to include the original (non-repeat)
            expected_instances = len(rep.duplicate_indices) + 1
            if len(location_instances) != expected_instances:
                error_messages.append(
                    f'Expected {expected_instances:d} instances of {name} in input locations, but got {len(location_instances):d}')

            solution_instances = [l for l in self.solution.route if l.is_same_doctor(original_location)]
            if len(solution_instances) != expected_instances:
                error_messages.append(f'Expected {expected_instances:d} instances of {name} in solution, but got {len(solution_instances):d}')
            solution_periods = [_period_from_solution(l) for l in solution_instances]
            solution_starts = [p.start for p in solution_periods]
            for i, s1 in enumerate(solution_starts[:-1]):
                s2 = solution_starts[i + 1]
                days_diff = (s2 - s1).total_days()
                if days_diff < rep.gap_days:
                    error_messages.append(f'Expected {rep.gap_days} days between {name} but got {days_diff} days')
        return error_messages

    def _validate_appointments(self):
        error_messages = []
        if not self.appointments:
            return error_messages

        location_appointment_times = {}
        for app in self.appointments:
            location_appointment_times.setdefault(app.location.key(), set()).add((app.start_time, app.end_time))

        found_location_times = set()
        for loc in self.solution.route:
            times = location_appointment_times.get(loc.key(), [])
            arrival_time = convert_date_str(loc.arrival_time)
            end_time = convert_date_str(loc.end_time)

            for start, end in times:
                if arrival_time == start and end_time == end:
                    found_location_times.add((loc.key(), start, end))

        expected_location_times = {(app.location.key(), app.start_time, app.end_time) for app in self.appointments}
        missing_location_times = expected_location_times - found_location_times
        for missing in missing_location_times:
            error_messages.append('Expected appointment with %s at %s - %s' % (missing[0][0], missing[1], missing[2]))

        return error_messages

    def validate(self, _raise=True):
        """Validate the solution or throw and InvalidSolutionError"""
        error_messages = self._validate_location_blackout_windows() + self._validate_repeat_visits() + self._validate_appointments()
        if error_messages:
            for message in error_messages:
                self.log.error(message)
            if _raise:
                raise InvalidSolutionError('Invalid solutions found during CP solution')
            else:
                return False

        self.log.info('Validation passed')
        return True
