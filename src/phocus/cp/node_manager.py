from phocus.model.work_period import WorkPeriod
from phocus.utils.mixins import Base


class NodeManager(Base):
    """Manage nodes from `Location`(s)

    :arg distance_matrix: The initial distance matrix passed from the API
    """
    def __init__(self, distance_matrix):
        self.distance_matrix = distance_matrix

        # FIXME add special origin node that has 0 distance from everything
        # Since we have variable start and end nodes per work period we need a ghost depot node

    def add_work_period(self, work_period: WorkPeriod):
        """"""
