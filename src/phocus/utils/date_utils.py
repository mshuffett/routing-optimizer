import datetime
import operator
from collections import deque
from numbers import Number

import pendulum
from typing import Sequence


def sort_periods(periods: Sequence[pendulum.Period]) -> Sequence[pendulum.Period]:
    """Sort periods first by start time then by end time"""
    return sorted(periods, key=operator.attrgetter('start', 'end'))


def combine_periods(periods: Sequence[pendulum.Period]) -> Sequence[pendulum.Period]:
    """Combine overlapping periods

    The sequence is returned in sorted order
    """
    sorted_periods = sort_periods(set(periods))
    result = []
    i = 0
    while i < len(sorted_periods):
        current_period = sorted_periods[i]

        j = i + 1
        while j < len(sorted_periods):
            p2 = sorted_periods[j]
            if current_period.start < p2.start:
                # no overlap
                if current_period.end < p2.start:
                    break
                # some overlap
                else:
                    current_period = max(current_period.end, p2.end) - current_period.start

            # p2 is strictly larger
            elif current_period.start == p2.start:
                current_period = p2

            j += 1

        result.append(current_period)
        i = j

    return result


def are_periods_overlapping(periods: Sequence[pendulum.Period]) -> bool:
    sorted_periods = sort_periods(sort_periods(set(periods)))
    if len(sorted_periods) != len(periods):
        return True
    for p1, p2 in zip(sorted_periods, sorted_periods[1:]):
        if p1.start == p2.start or p1.end >= p2.start:
            return True
    return False


def is_weekday(dt: datetime.datetime) -> bool:
    return pendulum.instance(dt).day_of_week not in (pendulum.SATURDAY, pendulum.SUNDAY)


def is_weekend(dt: datetime.datetime) -> bool:
    return not is_weekday(dt)


def next_weekday(dt: datetime.datetime) -> pendulum.DateTime:
    result = dt + pendulum.duration(days=1)
    while not is_weekday(result):
        result += pendulum.duration(days=1)
    return result


def is_overlapping(p1: pendulum.Period, p2: pendulum.Period) -> bool:
    return p1.start in p2 or p1.end in p2 or p2.start in p1 or p2.end in p1


def convert_open_times_to_blackout_windows(
        open_times: Sequence[pendulum.Period],
        work_periods: Sequence[pendulum.Period],
) -> Sequence[pendulum.Period]:
    open_times = deque(combine_periods(open_times))
    work_periods = deque(combine_periods(work_periods))
    blackout_windows = []

    if not open_times:
        return list(work_periods)

    open_period = open_times.popleft()
    while work_periods:
        work_period = work_periods.popleft()
        current_blackout_start = None
        for work_minute in work_period.range('minutes'):
            if work_minute > open_period.end:
                if current_blackout_start:
                    blackout_windows.append(current_blackout_end - current_blackout_start)
                    current_blackout_start = current_blackout_end = None
                while open_times and work_minute > open_period.end:
                    open_period = open_times.popleft()
                if not open_times and work_minute > open_period.end:
                    blackout_windows.append(work_period.end - work_minute)
                    break
            if work_minute < open_period.start:
                if not current_blackout_start:
                    current_blackout_start = work_minute
                current_blackout_end = work_minute
            elif work_minute in open_period and current_blackout_start:
                blackout_windows.append(current_blackout_end - current_blackout_start)
                current_blackout_start = current_blackout_end = None
        if current_blackout_start and current_blackout_end:
            blackout_windows.append(current_blackout_end - current_blackout_start)

    if not open_times:
        blackout_windows.extend(work_periods)

    return combine_periods(blackout_windows)


def time_off_periods(work_periods: Sequence[pendulum.Period]):
    """Convert work_periods to time_off_periods"""
    work_periods = combine_periods(work_periods)
    start_of_time_off = work_periods[0].end
    time_off = []
    for work_period in work_periods[1:]:
        time_off.append(work_period.start - start_of_time_off.add(seconds=1))
        start_of_time_off = work_period.end

    return time_off


def convert_date_time_to_epoch_millis(dt: pendulum.DateTime) -> int:
    return int(dt.timestamp() * 1000)


def convert_epoch_millis_to_date_time(millis: Number) -> pendulum.DateTime:
    return pendulum.from_timestamp(millis / 1000)
