from typing import NewType
from datetime import datetime, time, timezone, date


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
