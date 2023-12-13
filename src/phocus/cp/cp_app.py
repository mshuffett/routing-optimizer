import copy
import itertools
import logging
import random
import uuid
from datetime import datetime
from timeit import default_timer as timer
from typing import Tuple, Sequence, AbstractSet, Mapping, Optional, Any, Dict, List, Set

import numpy as np
import pendulum
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

import phocus.errors
from phocus.config import MIP_CONFIG
import phocus.cp.solution_validator
from phocus.cp.objective import ObjectiveCostEvaluator
from phocus.cp.time_dimension_converter import TimeDimensionConverter, Granularity
from phocus.cp.utils import RouteElement
from phocus.errors import NoSolutionFoundError
from phocus.model.appointment import Appointment
from phocus.model.location import Location
from phocus.model.solution import Solution
from phocus.solver import Solver
from phocus.utils import current_isotime_for_filename
from phocus.utils.date_utils import combine_periods, time_off_periods
from phocus.utils.files import real_long_island_data
from phocus.utils.distance_matrix_loader import load_distance_matrix_data
from phocus.utils.mixins import Base
from phocus.utils.ortools_utils import convert_first_solution_strategy_to_name, convert_search_heuristic_to_name

REAL_LONG_ISLAND_DATA = real_long_island_data()

EXAMPLE_APPOINTMENTS = [Appointment(REAL_LONG_ISLAND_DATA[4], pendulum.datetime(2018, 1, 1, hour=11),
                                    pendulum.datetime(2018, 1, 1, hour=12))]
EXAMPLE_START_DATETIME = pendulum.datetime(2018, 1, 1, hour=9)

SERVICE_TIME_DURATION = pendulum.duration(minutes=20)
TIME = 'Time'

logger = logging.getLogger(__name__)


class RepeatLocation(Base):
    def __init__(self, original_idx, gap_days, *duplicate_indices):
        self.original_idx = original_idx
        self.gap_days = gap_days
        self.duplicate_indices: Sequence[int] = duplicate_indices if duplicate_indices else []


class CP(Solver):
    """
    MIP main solver class

    :arg distance_matrix: The distance between points in seconds
    """

    def __init__(
            self,
            locations: Sequence[Location],
            distance_matrix,
            work_periods,
            time_dimension_granularity=Granularity.SECOND,
            appointments=None,
            num_vehicles=MIP_CONFIG['num_vehicles'],
            blackout_intervals: Optional[Sequence[pendulum.Period]] = None,
            time_limit_ms: int = 10 * 1000,
            solution_name: str = 'MIP',
            first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
    ):
        self.log.info('Initializing CP')
        super().__init__()
        if num_vehicles != 1:
            raise RuntimeError('Only supports 1 vehicle')
        self.work_periods: Sequence[pendulum.Period] = combine_periods(work_periods)
        self.log.info('Work Periods: %s', self.work_periods)
        self.time_off_periods = time_off_periods(self.work_periods)
        self.log.info('Time off periods: %s', self.time_off_periods)
        self.time_granularity = time_dimension_granularity
        self.assignment = None
        self.locations_no_duplicates = locations[:]
        start_datetime = self.work_periods[0].start
        self.time_dimension_converter: TimeDimensionConverter = TimeDimensionConverter(
            granularity=time_dimension_granularity, start_datetime=start_datetime)
        self.metrics: Dict['str', Any] = {'num_work_periods': len(self.work_periods)}
        self.log.info('Number of work periods: %s', len(self.work_periods))
        self.log.info('Start datetime %s', start_datetime)
        self.log.info('End datetime %s', self.work_periods[-1].end)
        self.locations, self.repeat_locations, self.fake_origin_idx = self._locations_with_duplicates_and_origin(locations, self.time_off_periods)

        # map of node index to time-off in the case of duplicate origins at end of work_periods
        self.node_time_off_map = {}
        for i, loc, in enumerate(self.locations):
            if loc.is_duplicate_origin:  # FIXME start locations should have 0 travel time to them and end locations should have 0 travel time from them
                self.node_time_off_map[i] = self.time_dimension_converter.duration_to_time_dimension(
                    loc.time_off_period.as_timedelta())
                loc.visit_time_seconds = self.node_time_off_map[i]
        self.log.info('%d locations with duplicates', len(self.locations))
        self.repeat_to_original_indices = {rep: loc.original_idx for loc in self.repeat_locations for rep in
                                           loc.duplicate_indices}
        self.appointments = appointments if appointments else []
        self.num_vehicles = num_vehicles
        self.blackout_windows = blackout_intervals if blackout_intervals else []
        self.time_limit_ms = time_limit_ms
        self.solution_name = solution_name
        # TODO if various granularities are supported this should be divided by the granularity
        self.distance_matrix = distance_matrix
        self._travel_time_callback_object = CreateTravelTimeCallback(self.distance_matrix,
                                                                     self.repeat_to_original_indices)
        self.travel_time_callback = self._travel_time_callback_object.get_travel_time

        self.node_appointments = make_node_appointments_map(self.locations, self.appointments)
        self.node_appointment_times = {
            node: self.time_dimension_converter.duration_to_time_dimension(appointment.duration)
            for node, appointment in self.node_appointments.items()
        }

        location_visit_times = self.calculate_location_visit_times()

        service_times = CreateServiceTimeCallback(location_visit_times)
        self.service_time_callback = service_times.get_service_time
        num_locations = len(self.locations)
        # FIXME probably have to make this a special node with 0 distance from every other node
        depot_idx = MIP_CONFIG['depot_idx']
        self.log.info('Specifying model with %d locations and %d vehicles', len(self.locations), self.num_vehicles)
        self.routing_model = pywrapcp.RoutingModel(num_locations, self.num_vehicles, depot_idx)
        self.solver = self.routing_model.solver()

        self.first_solution_strategy = first_solution_strategy
        self.metrics['first_solution_strategy'] = convert_first_solution_strategy_to_name(self.first_solution_strategy)

    @staticmethod
    def _locations_with_duplicates_and_origin(locations, time_off) -> Tuple[Sequence[Location], Sequence[RepeatLocation]]:
        locations = locations[:]

        # Add repeat visits
        repeat_idx = len(locations)
        repeat_locations = []
        duplicate_locations_to_add_to_locations = []
        for orig_idx, loc in enumerate(locations):
            if getattr(loc, 'num_total_visits', 1) > 1:
                total_visits = loc.num_total_visits
                min_visit_gap_days = loc.min_visit_gap_days
                repeat_location = RepeatLocation(orig_idx, min_visit_gap_days)
                repeat_locations.append(repeat_location)
                for _ in range(total_visits - 1):
                    duplicate_locations_to_add_to_locations.append(loc.copy())
                    repeat_location.duplicate_indices.append(repeat_idx)
                    repeat_idx += 1
        locations.extend(duplicate_locations_to_add_to_locations)

        fake_origin_idx = len(locations)
        locations.append(Location('fake origin', 'fake origin', 'fake origin', 'fake origin', id=str(uuid.uuid1())))
        # FIXME add test for 0 distance to this location

        # Add duplicate origin nodes
        # FIXME change time off for work period nodes
        for period in time_off:
            duplicate_origin = locations[0].copy()
            duplicate_origin.is_duplicate_origin = True
            duplicate_origin.time_off_period = period
            locations.append(duplicate_origin)

        # Add final location
        # FIXME
        duplicate_origin = locations[0].copy()
        duplicate_origin.is_duplicate_origin = True
        duplicate_origin.time_off_period = pendulum.Duration(seconds=0)
        locations.append(duplicate_origin)

        return locations, repeat_locations, fake_origin_idx

    def _specify_model(self):
        # grab search parameters
        if MIP_CONFIG['use_default_search_params']:
            search_parameters = self.routing_model.DefaultSearchParameters()
        else:
            raise RuntimeError('Only support default routing search params. Please try again.')

        search_parameters.time_limit_ms = self.time_limit_ms
        # PATH_CHEAPEST_ARC doesn't find a solution
        # Apparently best heuristics are PARALLEL_CHEAPEST_INSERTION, SAVINGS, PATH_CHEAPEST_ARC
        # Based on a small test, SAVINGS is faster than PARALLEL_CHEAPEST_INSERTION
        # However during testing SAVINGS seems to be somewhat unreliable, often producing solution that don't
        # include all of the constraints or throwing SEGV errors
        # Update: With limited trials, AUTOMATIC seems faster than PARALLEL_CHEAPEST_INSERTION and
        # LOCAL_CHEAPEST_INSERTION is the fastest, but LOCAL_CHEAPEST_INSERTION does not honor disjunctions well
        # ALL_UNPERFORMED seems to be the best trade-off
        # PATH_MOST_CONSTRAINED performed the best at 60 seconds
        # At 10 seconds PARALLEL_CHEAPEST_INSERTION is still the best
        # See optimization_exploration.ipynb in optimizer/notebooks
        # https://developers.google.com/optimization/routing/routing_options
        search_parameters.first_solution_strategy = self.first_solution_strategy
        search_heuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_parameters.local_search_metaheuristic = search_heuristic
        self.metrics['search_meta_heuristic'] = convert_search_heuristic_to_name(search_heuristic)

        # See https://github.com/google/or-tools/blob/master/ortools/constraint_solver/routing_parameters.proto
        # search_parameters.local_search_operators.use_tsp_opt = True
        # search_parameters.local_search_operators.use_tsp_lns = True

        # search_parameters.use_light_propagation = True
        # search_parameters.log_search = True

        # self.routing_model.SetPrimaryConstrainedDimension('Time')
        # solution_evaluator = SolutionEvaluator(self.solver, self.locations, self.node_appointments)
        # search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.EVALUATOR_STRATEGY
        # self.routing_model.SetFirstSolutionEvaluator(solution_evaluator.evaluate)

        # time dimension callbacks
        # for a given node, time is comprised of service time for that node +
        # time to travel to the next node
        total_times = CreateTotalTimeCallback(self.travel_time_callback, self.service_time_callback)
        total_time_callback = total_times.get_total_time
        self.routing_model.SetArcCostEvaluatorOfAllVehicles(self.travel_time_callback)

        # add the time dimension
        max_time_dimension = self.time_dimension_converter.datetime_to_time_dimension(self.work_periods[-1].end)
        self.routing_model.AddDimension(
            total_time_callback,
            max_time_dimension,
            max_time_dimension,
            MIP_CONFIG['fix_start_cumul_to_zero_time'],
            TIME
        )
        self.time = self.routing_model.GetDimensionOrDie(TIME)
        # This isn't needed since the final and start times are set
        # self.time.SetGlobalSpanCostCoefficient(100)
        self.routing_model.AddVariableMinimizedByFinalizer(
            self.routing_model.CumulVar(self.routing_model.End(0), TIME))

        # FIXME
        self.duplicate_origin_indices = [node for node in
                                         range(len(self.locations) - len(self.work_periods), len(self.locations))]
        self._add_required_constraints()
        self._add_all_blackouts()
        self._add_duplicate_origin_constraints()
        self._add_appointments()
        self._add_repeat_visit_constraints()
        self._add_disjunction()
        self.log.info('Getting assignment')
        # initial_route = self._initial_route_from_high_priority_nodes()
        # initial_assignment = self.routing_model.ReadAssignmentFromRoutes(initial_route, True)
        self.assignment = self.routing_model.SolveWithParameters(search_parameters)
        # self.assignment = self.routing_model.SolveFromAssignmentWithParameters(initial_assignment, search_parameters)

    def _add_repeat_visit_constraints(self):
        self.log.info('Adding repeat visit constraints')
        time = self.routing_model.GetDimensionOrDie('Time')
        for rep in self.repeat_locations:
            self.log.info('Adding repeat visit constraints for %s', rep)
            repeat_indices = {self.routing_model.NodeToIndex(rep.original_idx)}.union(
                {self.routing_model.NodeToIndex(dupe_node) for dupe_node in rep.duplicate_indices})

            for combo in itertools.combinations(repeat_indices, 2):
                t0 = time.CumulVar(combo[0])
                t1 = time.CumulVar(combo[1])
                gap_time = self.time_dimension_converter.duration_to_time_dimension(
                    pendulum.duration(days=rep.gap_days))
                self.solver.Add(abs(t1 - t0) >= gap_time)

    def _add_all_blackouts(self):
        """Add global and location specific blackout windows. It is important to add both at the same time because
        otherwise no solution is found.
        """
        global_blackouts = self._global_blackout_windows()

        time = self.routing_model.GetDimensionOrDie('Time')

        for node, loc in enumerate(self.locations):
            node_blackouts: Sequence[pendulum.Period] = getattr(loc, 'blackout_windows', [])

            # We have to subtract service time here otherwise you can arrive less than the amount of time it
            # takes to service doctor
            location_service_time = self.service_time_callback(node, node)
            location_service_duration = self.time_dimension_converter.time_dimension_to_duration(location_service_time)
            node_blackouts = [b.end - (b.start - location_service_duration) for b in node_blackouts]
            joined_blackouts = combine_periods(node_blackouts + global_blackouts)

            # Doesn't work if less than 1
            blackout_starts = [max(0, self.time_dimension_converter.datetime_to_time_dimension(b.start)) for b in
                               joined_blackouts]
            blackout_ends = [self.time_dimension_converter.datetime_to_time_dimension(b.end) for b in joined_blackouts]

            # Filter entries where end is less than start
            blackout_ends_greater_than_start = [end > start for start, end in zip(blackout_starts, blackout_ends)]
            blackout_starts = [start for start, end_greater in zip(blackout_starts, blackout_ends_greater_than_start) if
                               end_greater]
            blackout_ends = [end for end, end_greater in zip(blackout_ends, blackout_ends_greater_than_start) if
                             end_greater]

            node_time = time.CumulVar(self.routing_model.NodeToIndex(node))
            self.solver.AddConstraint(
                self.solver.NotMemberCt(
                    node_time,
                    blackout_starts, blackout_ends
                )
            )

    def _global_blackout_windows(self) -> Sequence[pendulum.Period]:
        blackout_windows = copy.deepcopy(self.blackout_windows)
        blackout_windows.extend(self.time_off_periods)
        self.log.info('Adding global blackouts: %s', blackout_windows)
        return blackout_windows

    def _add_duplicate_origin_constraints(self):
        # FIXME
        time = self.routing_model.GetDimensionOrDie('Time')
        for node, eod_datetime in zip(self.duplicate_origin_indices, [p.end for p in self.work_periods]):
            node_time = time.CumulVar(self.routing_model.NodeToIndex(node))
            time_constraint = self.time_dimension_converter.datetime_to_time_dimension(eod_datetime)
            self.log.info(
                'Adding origin constraint: %s offset %s for node %d %s',
                eod_datetime.isoformat(),
                time_constraint,
                node,
                self.locations[node],
            )
            self.solver.Add(node_time == time_constraint)

        end_node = self.routing_model.End(0)
        self.log.info('Adding end node constraint to node: %d', end_node)
        self.solver.Add(
            self.routing_model.CumulVar(end_node, TIME)
            == self.time_dimension_converter.datetime_to_time_dimension(eod_datetime))

    def _add_appointments(self):
        if not self.appointments:
            self.log.info('No appointments')
            return

        self.log.info('Adding %d appointments', len(self.appointments))
        time = self.routing_model.GetDimensionOrDie('Time')

        for appointment in self.appointments:
            node = self.locations.index(appointment.location)
            node_time = time.CumulVar(self.routing_model.NodeToIndex(node))
            start = self.time_dimension_converter.datetime_to_time_dimension(appointment.start_time)
            self.log.info('Adding appointment: %s with offset %s for node %d', appointment, start, node)
            self.solver.Add(node_time == start)

    def _nodes_involved_in_repeats(self) -> AbstractSet[int]:
        """All nodes releated to repeat locations"""
        nodes = set()
        for repeat in self.repeat_locations:
            nodes.add(repeat.original_idx)
            nodes.update(repeat.duplicate_indices)
        return nodes

    def _add_disjunction(self):
        # FIXME
        self.log.info('Adding disjunctions')
        origin_location = self.locations[0]
        base_penalty = 100000
        repeat_nodes = self._nodes_involved_in_repeats()
        for node, location in enumerate(self.locations):
            if (location.is_same_doctor(origin_location)
                    or location in {app.location for app in self.appointments}
                    or node in repeat_nodes
                    or getattr(location, 'is_required', False)
            ):
                self.routing_model.AddDisjunction([node], 100000000)
            else:
                multiplier = getattr(location, 'skip_cost_multiplier', 1)
                penalty = int(multiplier * base_penalty)
                self.routing_model.AddDisjunction([node], penalty)

    def _route_indices(self) -> List[RouteElement]:
        """Get an list of the route indices"""
        if not self.assignment:
            raise NoSolutionFoundError('No assignment was found')

        indices = []
        index = self.routing_model.Start(0)
        while not self.routing_model.IsEnd(index):
            node_index = self.routing_model.IndexToNode(index)
            indices.append(RouteElement(index, node_index))
            index = self.assignment.Value(self.routing_model.NextVar(index))

        node_index = self.routing_model.IndexToNode(index)
        indices.append(RouteElement(index, node_index))

        return indices

    def _solve(self):
        time_dimension = self.routing_model.GetDimensionOrDie(TIME)
        route = []

        start_index = self.routing_model.Start(0)
        plan_output = 'Route {0}:'.format(0)
        start_node = self.locations[self.routing_model.IndexToNode(start_index)]
        num_doctors_visited = 0
        total_travel_time = 0
        prev_node = None

        route_indices = self._route_indices()
        if (len(route_indices) >= 2
                and self.locations[route_indices[-1].node_index].is_same_doctor(start_node)
                and self.locations[route_indices[-2].node_index].is_same_doctor(start_node)):
            self.log.info('Removing duplicate duplicate origin node at end of route')
            del route_indices[-1]

        for route_idx in route_indices:
            index, node_index = route_idx.index, route_idx.node_index
            if not self.locations[node_index].is_same_doctor(start_node):
                num_doctors_visited += 1
            time_var = time_dimension.CumulVar(index)
            min_time = self.assignment.Min(time_var)
            location = copy.copy(self.locations[node_index])
            arrival_time = min_time
            location.arrival_time = str(self.time_dimension_converter.time_dimension_to_datetime(arrival_time))
            end_time = self.service_time_callback(node_index, None) + arrival_time
            location.end_time = str(self.time_dimension_converter.time_dimension_to_datetime(end_time))
            route.append(location)
            plan_output += \
                " {node_index} Time({tmin}, {tmax}) -> ".format(
                    node_index=node_index,
                    tmin=str(min_time),
                    tmax=str(self.assignment.Max(time_var)))
            if prev_node is not None:
                total_travel_time += int(self.travel_time_callback(prev_node, node_index))
                location.travel_to_time = int(self.travel_time_callback(prev_node, node_index))
            prev_node = node_index

        # FIXME fix doctors count and visited count
        self.metrics['doctors_visited'] = 0
        self.metrics['candidate_doctors'] = 0
        self.metrics['total_travel_time'] = total_travel_time
        self.metrics['avg_travel_time'] = (total_travel_time / num_doctors_visited) if num_doctors_visited else 0
        self.metrics['total_visit_time'] = sum(
            self.service_time_callback(route_idx.node_index, route_idx.node_index)
            for route_idx in route_indices
            if route_idx.node_index not in self.duplicate_origin_indices and route_idx.node_index != 0
        )
        self.metrics['total_work_time'] = sum(wp.in_seconds() for wp in self.work_periods)
        self.metrics['total_idle_time'] = self.metrics['total_work_time'] - self.metrics['total_visit_time'] - self.metrics['total_travel_time']

        objective_cost_evaluator = ObjectiveCostEvaluator(self.locations, route_indices, self.routing_model)
        self.metrics['objective_costs'] = {
            'travel': objective_cost_evaluator.total_travel_cost(),
            'disjunctive': objective_cost_evaluator.total_disjunctive_cost(),
            'total': objective_cost_evaluator.total_cost(),
        }

        self.log.info(plan_output)
        self.log.info(self.metrics)

        return Solution(self.solution_name, datetime.now(), route, metrics=self.metrics)

    def solve(self):
        try:
            start = timer()
            self._specify_model()
            solution = self._solve()
            end = timer()
            running_time = end - start
            solution.metrics['running_time'] = running_time
            return solution
        except Exception:
            self.log.exception('Error encountered while running MIP')
            raise

    def calculate_location_visit_times(self):
        # FIXME
        assert vars(self.locations[0]).get('visit_time_seconds', 0) == 0
        self.locations[0].visit_time_seconds = 0

        visit_times = []
        for node, location in enumerate(self.locations):
            if node == 0:
                visit_times.append(0)
            elif node in self.node_appointment_times:
                visit_times.append(self.node_appointment_times[node])
            elif node in self.node_time_off_map:
                visit_times.append(self.node_time_off_map[node])
            elif 'visit_time_seconds' in vars(location):
                visit_times.append(location.visit_time_seconds)
            elif node in self.repeat_to_original_indices and 'visit_time_seconds' in vars(
                    self.locations[self.repeat_to_original_indices[node]]):
                visit_times.append(self.locations[self.repeat_to_original_indices[node]].visit_time_seconds)
            else:
                visit_times.append(self.time_dimension_converter.duration_to_time_dimension(SERVICE_TIME_DURATION))

        return visit_times

    def _initial_route_from_high_priority_nodes(self):
        route = []
        route_ids = []
        for node, loc in enumerate(self.locations):
            multiplier = getattr(loc, 'skip_cost_multiplier', 1)
            if multiplier > 1:
                route.append(node)
                route_ids.append(loc.id)
        random.shuffle(route)
        self.log.info('Using initial route from high priority locations: %s', route_ids)
        return [route]

    def _add_required_constraints(self):
        required_nodes = [node for node, loc in enumerate(self.locations) if getattr(loc, 'is_required', False)]
        for node in required_nodes:
            index = self.routing_model.NodeToIndex(node)
            self.solver.Add(self.routing_model.ActiveVar(index) == 1)


class CreateTravelTimeCallback(object):
    def __init__(
            self,
            distance_matrix: np.ndarray,
            repeat_to_original_indices: Optional[Mapping[int, int]] = None,
    ):
        self.distance_matrix = distance_matrix
        self.repeat_to_original_indices = repeat_to_original_indices if repeat_to_original_indices else {}

    def get_travel_time(self, from_node, to_node):
        def transform_node(node):
            if node in self.repeat_to_original_indices:
                return self.repeat_to_original_indices[node]
            if node < len(self.distance_matrix):
                return node
            # Any node greater than distance matrix not in repeat indices is origin node
            return None

        from_node = transform_node(from_node)
        to_node = transform_node(to_node)

        if from_node is None or to_node is None:
            return 0

        return self.distance_matrix[from_node, to_node]


def make_node_appointments_map(locations, appointments):
    """Creates a node -> appointment map from appointments"""
    node_appointments = {}
    for appointment in appointments:
        node = locations.index(appointment.location)
        node_appointments[node] = appointment
    return node_appointments


class CreateServiceTimeCallback(object):
    def __init__(self, location_visit_times: List[int]):
        self.location_visit_times = location_visit_times

    # noinspection PyUnusedLocal
    def get_service_time(self, from_node, to_node):
        return self.location_visit_times[from_node]


class CreateTotalTimeCallback(object):
    """Create callback to get total times between locations."""

    def __init__(self, service_time_callback, travel_time_callback):
        self.service_time_callback = service_time_callback
        self.travel_time_callback = travel_time_callback

    def get_total_time(self, from_node, to_node):
        service_time = self.service_time_callback(from_node, to_node)
        travel_time = self.travel_time_callback(from_node, to_node)
        return service_time + travel_time


def run_model(
        solution_name,
        work_periods: Sequence[pendulum.Period],
        distance_matrix=None,
        time_limit_ms=10 * 1000,
        locations=REAL_LONG_ISLAND_DATA,
        appointments=None,
        lunch_hour_start=None,
        lunch_minutes=None,
        **kwargs,
) -> Solution:
    locations = copy.deepcopy(locations)

    distance_matrix = distance_matrix if distance_matrix is not None else load_distance_matrix_data(locations)

    # Lunch is from noon to 1 PM but we subtract service time from the beginning
    # so that a node cannot start lunch during its service time.
    lunch_intervals: Sequence[pendulum.Period] = []
    if lunch_hour_start and lunch_minutes:
        # All of the dates where work is performed
        work_dates = {p.start.date() for p in work_periods}
        work_dates.update(p.end.date() for p in work_periods)

        for dt in work_dates:
            lunch_start = pendulum.datetime(year=dt.year, month=dt.month, day=dt.day,
                                            hour=lunch_hour_start) - SERVICE_TIME_DURATION
            lunch_end = lunch_start + pendulum.duration(minutes=lunch_minutes)
            lunch_intervals.append(lunch_end - lunch_start)

    cp = CP(
        locations,
        work_periods=work_periods,
        distance_matrix=distance_matrix,
        appointments=appointments,
        blackout_intervals=lunch_intervals,
        solution_name=solution_name,
        time_limit_ms=time_limit_ms,
        **kwargs
    )
    solution = cp.solve()

    validator = phocus.cp.solution_validator.SolutionValidator(cp.appointments, cp.locations, cp.repeat_locations,
                                                               solution)
    is_valid = validator.validate(_raise=False)

    solution_filename = 'mip-%s-%s.json' % (current_isotime_for_filename(), solution_name)
    solution.save(solution_filename)
    if not is_valid:
        raise phocus.errors.InvalidSolutionError('Invalid solutions found during CP solution')
    return solution
