from datetime import datetime, time, timezone


def time_min():
    return time.min.replace(tzinfo=timezone.utc)


def time_max():
    return time.max.replace(tzinfo=timezone.utc)


def datetime_min():
    return datetime.min.replace(tzinfo=timezone.utc)


def datetime_max():
    return datetime.max.replace(tzinfo=timezone.utc)
