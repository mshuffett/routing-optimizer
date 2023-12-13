"""Experiments in optimizations"""
import copy
import itertools
import json
import logging
from enum import Enum

from ortools.constraint_solver import routing_enums_pb2

from phocus.app import plan_route
from phocus.errors import NoSolutionFoundError
from phocus.cp.time_dimension_converter import Granularity
from phocus.utils import bootstrap_project, memory
from phocus.utils.constants import DATA_PATH
from phocus.utils.mixins import Base

logger = logging.getLogger(__name__)


def full_api_params():
    with open(DATA_PATH / 'test_data' / 'full_api_frequency.json') as f:
        return json.load(f)


def full_api_frequency_params():
    with open(DATA_PATH / 'test_data' / 'full_api_frequency.json') as f:
        return json.load(f)


@memory.cache
def _run_cached(experiment):
    return plan_route(experiment.params)


class Strategy(Enum):
    SAVINGS = routing_enums_pb2.FirstSolutionStrategy.SAVINGS
    PARALLEL_CHEAPEST_INSERTION = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    PATH_MOST_CONSTRAINED_ARC = routing_enums_pb2.FirstSolutionStrategy.PATH_MOST_CONSTRAINED_ARC


class Experiment(Base):
    def __init__(self, params, granularity, strategy: Strategy, max_run_millis: int, metrics=None):
        self.granularity = granularity
        self.strategy = strategy
        self.params = copy.deepcopy(params)
        self.params['maxRunMillis'] = max_run_millis
        self.params['overrides'] = {
            'time_dimension_granularity': granularity,
            'first_solution_strategy': strategy.value,
        }
        self._metrics = metrics if metrics else {}
        self._solution = None

    def run(self):
        self._solution = _run_cached(self)
        self._metrics.update(self._solution['metrics'])
        return self._metrics

    @property
    def solution(self):
        if not self._solution:
            self.run()
        return self._solution

    @property
    def metrics(self):
        if not self._metrics:
            self.run()
        return self._metrics


def run_experiments():
    time_dimension_granularities = [Granularity.SECOND, Granularity.MINUTE]
    experiments = []
    max_runtimes = [1000, 3000, 5000, 10000]
    params_by_name = {
        'No Frequency': full_api_params(),
        'Frequency': full_api_frequency_params()
    }
    for granularity, strategy, runtime, (params_name, params) in itertools.product(time_dimension_granularities, Strategy, max_runtimes, params_by_name.items()):
        logger.info('Granularity: %s, Strategy: %s, Params: %s', granularity, strategy, params_name)
        experiment = Experiment(params, granularity, strategy, runtime, metrics={'params': params_name})
        try:
            metrics = experiment.run()
            logger.info(metrics)
            experiments.append(experiment)
        except NoSolutionFoundError:
            logger.info('No solution found')
    return experiments


if __name__ == '__main__':
    bootstrap_project(log_title='optimization')
    run_experiments()
