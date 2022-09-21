"""
pycroft.helpers.utc
~~~~~~~~~~~~~~~~~~~
"""
from datetime import datetime, time, timezone, date
from typing import NewType

TimeTz = NewType('TimeTz', time)
DateTimeTz = NewType('DateTimeTz', datetime)
DateTimeNoTz = NewType('DateTimeNoTz', datetime)


def time_min() -> TimeTz:
    return time.min.replace(tzinfo=timezone.utc)


def time_max() -> TimeTz:
    return time.max.replace(tzinfo=timezone.utc)


def datetime_min() -> DateTimeTz:
    return datetime.min.replace(tzinfo=timezone.utc)


def datetime_max() -> DateTimeTz:
    return datetime.max.replace(tzinfo=timezone.utc)


def with_min_time(d: date) -> DateTimeTz:
    """Return the datetime corresponding to 00:00 UTC at the given date."""
    return DateTimeTz(datetime.combine(d, time_min()))


def with_max_time(d: date) -> DateTimeTz:
    return DateTimeTz(datetime.combine(d, time_max()))


def safe_combine(d: date, t: TimeTz) -> DateTimeTz:
    return DateTimeTz(datetime.combine(d, t))


def ensure_tzinfo(t: time) -> TimeTz:
    if t.tzinfo is not None:
        return TimeTz(t)
    return TimeTz(t.replace(tzinfo=timezone.utc))


def combine_ensure_tzinfo(d: date, t: time) -> DateTimeTz:
    return safe_combine(d, ensure_tzinfo(t))


def combine_or_midnight(d: date, t: time | None) -> DateTimeTz:
    if t is not None:
        return combine_ensure_tzinfo(d, t)
    return with_min_time(d)
