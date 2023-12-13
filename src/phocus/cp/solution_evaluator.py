from collections import defaultdict
from typing import Sequence

import pendulum
from ortools.constraint_solver import pywrapcp

from phocus.utils.mixins import Base


class SolutionEvaluator(Base):
    """Solution Evaluator for evaluating an arc for the first solution"""
    def __init__(self, routing_model: pywrapcp.RoutingModel, locations, node_appointments):
        self.routing_model = routing_model
        self.locations = locations
        self.node_appointments = node_appointments
        self.node_blackout_seconds = defaultdict(lambda: 0)
        for node, loc in enumerate(self.locations):
            node_blackouts: Sequence[pendulum.Period] = getattr(loc, 'blackout_windows', [])
            for blackout in node_blackouts:
                self.node_blackout_seconds[node] += blackout.total_seconds()

    def evaluate(self, idx1, idx2):
        """Takes two indices and returns the index which should be preferred

        1. Choose first index with appointment
        2. Choose index with least amount of open time
        TODO: Add frequency considerations
        """
        node1, node2 = self.routing_model.IndexToNode(idx1), self.routing_model.IndexToNode(idx2)
        if node1 in self.node_appointments:
            return idx1
        if node2 in self.node_appointments:
            return idx2
        if self.node_blackout_seconds[node1] <= self.node_blackout_seconds[node2]:
            return idx1
        return idx2
