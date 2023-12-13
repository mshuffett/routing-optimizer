import pendulum

from phocus.utils.date_utils import sort_periods, combine_periods, convert_open_times_to_blackout_windows, next_weekday

DAY1 = pendulum.datetime(2018, 1, 1)
DAY2 = pendulum.datetime(2018, 1, 2)
DAY3 = pendulum.datetime(2018, 1, 3)
DAY4 = pendulum.datetime(2018, 1, 4)
DAY5 = pendulum.datetime(2018, 1, 5)
DAY6 = pendulum.datetime(2018, 1, 6)

ONE_TWO = DAY2 - DAY1
ONE_THREE = DAY3 - DAY1
ONE_FOUR = DAY4 - DAY1
TWO_THREE = DAY3 - DAY2
TWO_FOUR = DAY4 - DAY2
FOUR_FIVE = DAY5 - DAY4
FOUR_SIX = DAY6 - DAY4
FIVE_SIX = DAY6 - DAY5

WORK_TIME_DELTA = pendulum.duration(hours=8)


def test_sort_periods():
    assert sort_periods([TWO_THREE, ONE_THREE, ONE_TWO]) == [ONE_TWO, ONE_THREE, TWO_THREE]
    assert sort_periods([TWO_THREE, ONE_TWO, FOUR_FIVE, FIVE_SIX]) == [ONE_TWO, TWO_THREE, FOUR_FIVE, FIVE_SIX]


def test_combine_periods():
    assert combine_periods([TWO_THREE, TWO_THREE, ONE_THREE, ONE_TWO]) == [ONE_THREE]
    assert combine_periods([TWO_THREE, ONE_TWO, FOUR_FIVE, FIVE_SIX]) == [ONE_THREE, FOUR_SIX]
    assert combine_periods([ONE_THREE, TWO_FOUR]) == [ONE_FOUR]
    assert combine_periods([ONE_FOUR, TWO_THREE]) == [ONE_FOUR]


def test_pendulum_period_inclusive_in():
    period = DAY2 - DAY1
    assert DAY1 in period
    assert DAY2 in period


def test_convert_open_times_to_blackout_windows():
    assert convert_open_times_to_blackout_windows(
        open_times=[DAY2 - DAY1],
        work_periods=[(DAY1 + WORK_TIME_DELTA) - DAY1]
    ) == [], 'One day no blackouts'

    start = pendulum.datetime(2018, 1, 1, 9)
    end = pendulum.datetime(2018, 1, 1, 17)
    work_periods = [(start + WORK_TIME_DELTA) - start]
    assert convert_open_times_to_blackout_windows(
        open_times=[end - start],
        work_periods=work_periods,
    ) == [], 'One day working hours no blackouts'

    work_periods.append((start.add(days=1) + WORK_TIME_DELTA) - start.add(days=1))
    assert convert_open_times_to_blackout_windows(
        open_times=[pendulum.datetime(2018, 1, 1, 17) - pendulum.datetime(2018, 1, 1, 9)],
        work_periods=work_periods,
    ) == [pendulum.datetime(2018, 1, 2, 17) - pendulum.datetime(2018, 1, 2, 9)], 'Two days all blackout on 2nd day'


def create_work_periods(start: pendulum.DateTime, days: int):
    work_periods = []
    current_day = start

    for _ in range(days):
        work_periods.append((current_day + WORK_TIME_DELTA) - current_day)
        current_day = next_weekday(current_day)

    return work_periods


def test_complex_convert_open_times_to_blackout_windows():
    start = pendulum.datetime(2018, 1, 1, 9)
    work_periods = create_work_periods(start, 2)
    assert convert_open_times_to_blackout_windows(
        open_times=[
            pendulum.datetime(2018, 1, 1, 10) - pendulum.datetime(2018, 1, 1, 9),
            pendulum.datetime(2018, 1, 1, 12) - pendulum.datetime(2018, 1, 1, 11, 30),
            pendulum.datetime(2018, 1, 1, 19) - pendulum.datetime(2018, 1, 1, 15),
        ],
        work_periods=work_periods,
    ) == [
        pendulum.datetime(2018, 1, 1, 11, 29) - pendulum.datetime(2018, 1, 1, 10, 1),
        pendulum.datetime(2018, 1, 1, 14, 59) - pendulum.datetime(2018, 1, 1, 12, 1),
        pendulum.datetime(2018, 1, 2, 17) - pendulum.datetime(2018, 1, 2, 9)
    ], 'Complex example'


def test_different_timezone():
    assert convert_open_times_to_blackout_windows(
        open_times=[],
        work_periods=create_work_periods(pendulum.datetime(2018, 6, 18, 13), 1),
    ) == [pendulum.datetime(2018, 6, 18, 21) - pendulum.datetime(2018, 6, 18, 13)], 'Different starting time'

    assert convert_open_times_to_blackout_windows(
        open_times=[pendulum.datetime(2018, 6, 20, 22) - pendulum.datetime(2018, 6, 20, 18)],
        work_periods=create_work_periods(pendulum.datetime(2018, 6, 18, 13), 5)
    ) == [
        pendulum.datetime(2018, 6, 18, 21) - pendulum.datetime(2018, 6, 18, 13),
        pendulum.datetime(2018, 6, 19, 21) - pendulum.datetime(2018, 6, 19, 13),
        pendulum.datetime(2018, 6, 20, 17, 59) - pendulum.datetime(2018, 6, 20, 13),
        pendulum.datetime(2018, 6, 21, 21) - pendulum.datetime(2018, 6, 21, 13),
        pendulum.datetime(2018, 6, 22, 21) - pendulum.datetime(2018, 6, 22, 13),
    ], 'Different starting time'
