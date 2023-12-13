from datetime import datetime, timedelta

from pendulum import Duration

from phocus.model.location import Location
from phocus.utils.mixins import Base


class Appointment(Base):
    def __init__(self, location: Location, start_time: datetime, end_time: datetime):
        self.end_time = end_time
        self.start_time = start_time
        self.location = location
        self.duration: Duration = end_time - start_time

    def __eq__(self, other):
        return (self.start_time, self.end_time) == (other.start_time, other.end_time) and self.location.is_same_doctor(other.location)

    def __str__(self):
        return '<Appointment: %s %s - %s' % (self.location, self.start_time.isoformat(), self.end_time.isoformat())

    def __hash__(self):
        return hash((self.start_time, self.end_time, self.location.key()))
