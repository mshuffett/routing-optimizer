import abc

from phocus.utils.mixins import Base


class Solver(Base):
    __meta__ = abc.ABCMeta
    """
    Abstract class for a geospatial routing solver
    Initialize needed variables
    """

    def __init__(self, *args, **kwargs):
        self.routing_model = None
        self.routing_solution = None

    """
    Compute the solution: this function should return a routing solution

    Requires read_data() and specify_model() to have been called
    """
    @abc.abstractmethod
    def solve(self):
        pass
