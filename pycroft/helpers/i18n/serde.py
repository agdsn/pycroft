#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
pycroft.helpers.i18n.serde
~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations

import operator
import typing
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from .types import Interval, NegativeInfinity, PositiveInfinity, Bound, Money
from .utils import qualified_typename


def identity(x):
    return x


def deserialize_money(v):
    try:
        return Money(Decimal(v[0]), v[1])
    except IndexError:
        raise ValueError()


def serialize_interval(interval: Interval) -> dict[str, typing.Any]:
    lower = interval.lower_bound
    upper = interval.upper_bound
    lower_value = serialize_param(lower.value) if not lower.unbounded else None
    upper_value = serialize_param(upper.value) if not upper.unbounded else None
    return {
        "lower_closed": lower.closed,
        "lower_value": lower_value,
        "upper_closed": upper.closed,
        "upper_value": upper_value,
    }


# pycharm does not support building this dynamically.
# Thus, we need to hard-code this type alias.
Serializable = typing.Union[
    None,
    bool,
    str,
    int,
    float,
    Decimal,
    Money,
    date,
    datetime,
    time,
    timedelta,
    Interval,
]


# TODO be more specific about return type
serialize_map: dict[type, typing.Callable] = {
    type(None): identity,
    bool: identity,
    float: identity,
    str: identity,
    int: identity,
    Decimal: str,
    Money: lambda m: (str(m.value), m.currency),
    date: operator.methodcaller("isoformat"),
    datetime: operator.methodcaller("isoformat"),
    time: operator.methodcaller("isoformat"),
    timedelta: lambda v: {
        "days": v.days,
        "seconds": v.seconds,
        "microseconds": v.microseconds,
    },
    Interval: serialize_interval,
}


def deserialize_interval(value: dict[str, typing.Any]) -> Interval:
    try:
        lower_value = (
            deserialize_param(u)
            if (u := value["lower_value"]) is not None
            else NegativeInfinity
        )
        lower_closed = value["lower_closed"]
        upper_value = (
            deserialize_param(u)
            if (u := value["upper_value"]) is not None
            else PositiveInfinity
        )
        upper_closed = value["upper_closed"]
    except KeyError as e:
        raise ValueError("Could not deserialized from interval (missing key)") from e

    if not isinstance(lower_closed, bool):
        raise ValueError(
            "Could not deserialize to interval: "
            f"expected ['lower_closed'] to be bool, got {type(lower_closed)}"
        )
    if not isinstance(upper_closed, bool):
        raise ValueError(
            "Could not deserialize to interval: "
            f"expected ['upper_closed'] to be bool, got {type(upper_closed)}"
        )
    return Interval(
        lower_bound=Bound(lower_value, lower_closed),
        upper_bound=Bound(upper_value, upper_closed),
    )


_deserialize_type_map: dict[type, typing.Callable] = {
    type(None): identity,
    bool: identity,
    str: identity,
    int: identity,
    float: identity,
    Decimal: Decimal,
    Money: deserialize_money,
    date: date.fromisoformat,
    datetime: datetime.fromisoformat,
    time: time.fromisoformat,
    timedelta: lambda v: timedelta(**v),
    Interval: deserialize_interval,
}


# TODO be more specific
deserialize_map: dict[str, typing.Callable] = {
    qualified_typename(t): f for t, f in _deserialize_type_map.items()
}


def serialize_param(param):
    concrete_type = type(param)
    serializers = (
        (type_, serialize_map[type_])
        for type_ in concrete_type.__mro__
        if type_ in serialize_map
    )
    try:
        type_, serializer = next(serializers)
    except StopIteration:
        raise TypeError(
            "No serialization available for type {} or any"
            "supertype".format(qualified_typename(concrete_type))
        )
    return {"type": qualified_typename(type_), "value": serializer(param)}


def deserialize_param(param):
    type_name = param["type"]
    try:
        deserializer = deserialize_map[type_name]
    except KeyError:
        raise TypeError(f"No deserialization available for type {type_name}")
    return deserializer(param["value"])
