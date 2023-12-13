"""Conversion utils for the time dimension"""
import datetime
from enum import Enum

import pendulum

from phocus.utils.mixins import Base


class Granularity(Enum):
    """A time granularity for time dimension conversion"""
    SECOND = 1
    MINUTE = 2


class TimeDimensionConverter(Base):
    def __init__(self, granularity, start_datetime: pendulum.DateTime):
        self.granularity = granularity
        self.start_datetime = start_datetime
        
        if self.granularity not in (Granularity.SECOND, Granularity.MINUTE):
            raise NotImplementedError('Time dimension converter is not implemented for granularity: %s' % granularity)

    def duration_to_time_dimension(self, duration: pendulum.Duration):
        if self.granularity is Granularity.SECOND:
            return int(duration.total_seconds())
        if self.granularity is Granularity.MINUTE:
            return int(duration.total_minutes())

    def datetime_to_time_dimension(self, dt: datetime.datetime) -> int:
        return self.duration_to_time_dimension(pendulum.instance(dt) - self.start_datetime)

    def time_dimension_to_datetime(self, time_dimension: int) -> pendulum.DateTime:
        return self.start_datetime + self.time_dimension_to_duration(time_dimension)

    def time_dimension_to_duration(self, time_dimension: int) -> pendulum.Duration:
        """Convert time dimension to duration

        This is useful with service times for example
        """
        if self.granularity is Granularity.SECOND:
            return pendulum.duration(seconds=time_dimension)
        elif self.granularity is Granularity.MINUTE:
            return pendulum.duration(minutes=time_dimension)
        else:
            raise NotImplementedError('Time dimension converter is not implemented for granularity: %s' % self.granularity)
