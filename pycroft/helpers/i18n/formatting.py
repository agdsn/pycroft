#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
pycroft.helpers.i18n.formatting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations

import typing
import typing as t
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from babel import numbers, dates

from .babel import get_locale, gettext
from .options import Options, TypeSpecificOptions, OptionPolicy
from .types import Money, Interval
from .utils import qualified_typename

P = typing.ParamSpec("P")


class Formattable(typing.Protocol):
    def __format__(self, format_spec: str) -> str:
        ...


if typing.TYPE_CHECKING:
    from _typeshed import SupportsAllComparisons

    T = typing.TypeVar("T", bound=SupportsAllComparisons)
else:
    T = typing.TypeVar("T")


class Formatter(typing.Protocol[T, P]):
    __option_policy__: OptionPolicy
    # first parameter is `Self`
    __call__: t.Callable[t.Concatenate[Formatter, T, P], Formattable]
    __name__: str


def type_specific_options(
    formatter: typing.Callable[typing.Concatenate[T, P], Formattable]
) -> Formatter[T, P]:
    formatter.__option_policy__ = "type-specific"  # type: ignore
    return typing.cast(Formatter[T, P], formatter)


def ignore_options(
    formatter: typing.Callable[typing.Concatenate[T, P], Formattable]
) -> Formatter[T, P]:
    formatter.__option_policy__ = "ignore"  # type: ignore
    return typing.cast(Formatter[T, P], formatter)


@type_specific_options
def format_number(n, insert_commas=True):
    if insert_commas:
        return numbers.format_decimal(n, locale=get_locale())
    else:
        return n


@type_specific_options
def format_decimal(d, format=None):
    return numbers.format_decimal(d, format=format, locale=get_locale())


@type_specific_options
def format_currency(money: Money, format=None):
    return numbers.format_currency(*money, format=format, locale=get_locale())


@type_specific_options
def format_date(d, format="medium"):
    return dates.format_date(d, format=format, locale=get_locale())


@type_specific_options
def format_datetime(d, format="medium", tzinfo=None):
    return dates.format_datetime(d, format=format, tzinfo=tzinfo, locale=get_locale())


@type_specific_options
def format_time(t, format="medium", tzinfo=None):
    return dates.format_time(t, format=format, tzinfo=tzinfo, locale=get_locale())


@type_specific_options
def format_timedelta(
    delta, granularity="second", threshold=0.85, add_direction=False, format="medium"
):
    return dates.format_timedelta(
        delta,
        granularity=granularity,
        threshold=threshold,
        add_direction=add_direction,
        format=format,
        locale=get_locale(),
    )


@ignore_options
def format_bool(v):
    return gettext("True") if v else gettext("False")


@ignore_options
def format_none(n):
    return gettext("None")


@type_specific_options
def format_interval(interval: Interval, **options: TypeSpecificOptions):
    lower_bound = interval.lower_bound
    upper_bound = interval.upper_bound
    assert type(lower_bound) == type(upper_bound)
    generic_options: Options = {type(lower_bound): options}
    return "{}{}, {}{}".format(
        "[" if lower_bound.closed else "(",
        format_param(lower_bound.value, generic_options)
        if not lower_bound.unbounded
        else "-∞",
        format_param(upper_bound.value, generic_options)
        if not upper_bound.unbounded
        else "∞",
        "]" if upper_bound.closed else ")",
    )


@ignore_options
def identity(x):
    return x


formatter_map: dict[type, Formatter] = {
    type(None): identity,
    bool: identity,
    str: identity,
    int: format_number,
    float: format_decimal,
    Decimal: format_decimal,
    Money: format_currency,
    date: format_date,
    datetime: format_datetime,
    time: format_time,
    timedelta: format_timedelta,
    Interval: format_interval,
}


def format_param(p, options: dict[type, dict[str, typing.Any]]) -> Formattable:
    concrete_type = type(p)
    formatters = (
        (type_, formatter_map[type_])
        for type_ in concrete_type.__mro__
        if type_ in formatter_map
    )
    try:
        type_, formatter = next(formatters)
    except StopIteration:
        raise TypeError(
            f"No formatter available for type {qualified_typename(concrete_type)}"
            " or any supertype."
        )
    option_policy: OptionPolicy | None = getattr(formatter, "__option_policy__", None)
    if option_policy == "ignore":
        formatter_options: dict[str, typing.Any] = {}
    elif option_policy == "type-specific":
        formatter_options = options.get(type_, {})
    else:
        raise RuntimeError(
            f"Invalid Value {option_policy!r} for {formatter.__name__}.__option_policy__"
        )
    return formatter(p, **formatter_options)
