from ortools.constraint_solver import routing_enums_pb2


def convert_first_solution_strategy_to_name(strategy: int) -> str:
    return routing_enums_pb2.FirstSolutionStrategy.Value.Name(strategy)


def convert_search_heuristic_to_name(heuristic: int) -> str:
    return routing_enums_pb2.LocalSearchMetaheuristic.Value.Name(heuristic)
