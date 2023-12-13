from dataclasses import dataclass


@dataclass
class RouteElement:
    index: int
    node_index: int