from enum import auto, Enum

from dataclasses import dataclass
from typing import List

from ortools.constraint_solver.pywrapcp import RoutingModel

from phocus.cp.utils import RouteElement
from phocus.model.location import Location


class CostType(Enum):
    """An enum representing the type of cost"""
    TRAVEL = auto()
    DISJUNCTIVE = auto()


@dataclass
class Cost:
    type: CostType
    value: int


@dataclass
class ObjectiveCostEvaluator:
    """Evaluate various objective costs"""
    locations: List[Location]
    route: List[RouteElement]
    routing_model: RoutingModel

    def __post_init__(self):
        self.missing_nodes = set(range(len(self.locations))) - set(r.node_index for r in self.route)
        self.missing_indices = map(self.routing_model.NodeToIndex, self.missing_nodes)

        indices = [r.index for r in self.route]
        index_pairs = {i: j for i, j in zip(indices, indices[1:])}
        self.costs = []
        for node, _ in enumerate(self.locations):
            index = self.routing_model.NodeToIndex(node)
            if node in self.missing_nodes:
                self.costs.append(Cost(CostType.DISJUNCTIVE, self.routing_model.UnperformedPenalty(index)))
            elif index in index_pairs:
                self.costs.append(Cost(CostType.TRAVEL, self.routing_model.GetCost(index, index_pairs[index], v=0)))

    def cost(self, node) -> Cost:
        return self.costs[node]

    def total_travel_cost(self):
        return sum(c.value for c in self.costs if c.type is CostType.TRAVEL)

    def total_disjunctive_cost(self):
        return sum(c.value for c in self.costs if c.type is CostType.DISJUNCTIVE)

    def total_cost(self):
        return sum(c.value for c in self.costs)
