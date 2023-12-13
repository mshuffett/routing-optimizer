import pendulum

from phocus.model.location import Location


class WorkPeriod(pendulum.Period):
    """WorkPeriod extends `pendulum.Period` with concepts like startLocation and endLocation"""
    def __new__(cls, start, end, start_location_id, end_location_id):
        return super().__new__(cls, start, end)

    def __init__(self,
                 start,
                 end,
                 start_location_id: str,
                 end_location_id: str):
        super().__init__(start, end)
        self.start_location_id = start_location_id
        self.end_location_id = end_location_id

    def __eq__(self, other):
        return (self.start == other.start
                and self.end == other.end
                and self.start_location_id == other.start_location_id
                and self.end_location_id == other.end_location_id
                )

    def __lt__(self, other):
        return (self.start, self.end) < (other.start, other.end)

    def __hash__(self):
        return hash((self.start, self.end, self.start_location_id, self.end_location_id))