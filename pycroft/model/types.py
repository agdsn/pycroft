# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.types
~~~~~~~~~~~~~~~~~~~
"""

import typing as t
from datetime import datetime
from decimal import Decimal
from numbers import Number
from typing import Any

import netaddr
from sqlalchemy import TypeDecorator, Integer, DateTime, literal, ColumnElement
from sqlalchemy.dialects.postgresql import INET, Range
from sqlalchemy.dialects.postgresql.ranges import TSTZRANGE
from sqlalchemy.sql.type_api import _ComparatorFactory

from pycroft.helpers.interval import Interval
from pycroft.model.exc import PycroftModelException


# NOTES
# In the type decorators below, `dialect` will be `sqlalchemy.dialects.postgresql.base.PGDialect`.


class _IPType[T](TypeDecorator[T]):
    impl = INET
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """"""
        if value is None:
            return value
        return str(value)


class IPAddress(_IPType[netaddr.IPAddress]):
    #:
    cache_ok = True

    @property
    @t.override
    def python_type(self):
        """"""
        return netaddr.IPAddress

    def process_result_value(self, value, dialect):
        """"""
        if value is None:
            return value
        return netaddr.IPAddress(str(value))


class IPNetwork(_IPType[netaddr.IPNetwork]):
    #:
    cache_ok = True

    @property
    @t.override
    def python_type(self):
        """"""
        return netaddr.IPNetwork

    def process_result_value(self, value, dialect):
        """"""
        if value is None:
            return value
        return netaddr.IPNetwork(str(value))


class Money(TypeDecorator[Decimal]):
    impl = Integer
    #:
    cache_ok = True

    @property
    @t.override
    def python_type(self):
        """"""
        return Decimal

    @staticmethod
    def process_bind_param(value, dialect):
        """"""
        if not isinstance(value, Number):
            raise ValueError(f"{repr(value)} is not a valid money amount")
        cents = Decimal(value).scaleb(2)
        if int(cents) != cents:
            raise ValueError(f"{Decimal(value)} is not a valid money amount")
        else:
            return int(cents)

    @staticmethod
    def process_result_value(value, dialect):
        """"""
        return Decimal(value).scaleb(-2)


# TODO actually this is _tz-aware datetime_
class TsTzRange(TypeDecorator[Interval[datetime]]):
    impl = TSTZRANGE
    #:
    cache_ok = True

    @property
    @t.override
    def python_type(self):
        """"""
        return Interval

    @t.override
    def process_literal_param(self, value, dialect):
        """"""
        if value is None:
            return None
        return f"'{str(value)}'"

    def process_bind_param(self, value: Interval[datetime] | None, dialect) -> str | None:
        """gets PY TYPE, returns DB TYPE"""
        if value is None:
            return None

        return str(value)

    def process_result_value(
        self, value: Range[datetime] | None, dialect
    ) -> Interval[datetime] | None:
        """"""
        if value is None:
            return None
        if isinstance(value, Range):
            return Interval[datetime].from_explicit_data(
                value.lower, value.lower_inc, value.upper, value.upper_inc
            )

        # see https://github.com/sqlalchemy/sqlalchemy/discussions/6942
        raise PycroftModelException(
            f"Unable to deserialize TsTzRange value {value!r} of type {type(value)}."
            " Usually, this value should've been deserialized by psycopg2 into a"
            " DatetimeTzRange.  Did you make a mistake in your query?"
            " Note that you may have to use `cast(…, TsTzRange)` to let sqlalchemy know"
            " of the return type –– even if you specified the type in `literal()` already!"
        )

    class _Comparator(TSTZRANGE.comparator_factory):
        def contains(self, other: Any, **kwargs) -> ColumnElement[bool]:
            """Provide the functionality of the `@>` operator for Intervals.

            :param other: can be an interval, a tz-aware datetime,
               or column-like sql expressions with these types.

            If any `.contains()` call does not work, you can add support here.
            """
            if other is None:
                raise PycroftModelException("You cannot use `.contains()` with `null` (`None`)!")

            if isinstance(other, datetime):
                if other.utcoffset() is None:
                    raise PycroftModelException(
                        "You cannot use `.contains()` with a non-timezone-aware datetime"
                        f" ({other})!"
                    )
                return super().contains(literal(other, type_=DateTimeTz), **kwargs)

            return super().contains(other, **kwargs)

        def overlaps(self, other: Any, **kwargs):
            """Provide the functionality of the `&&` operator for Intervals."""
            if other is None:
                raise PycroftModelException(
                    "You cannot use `.overlaps()`/`&` with `null` (`None`)!"
                )
            return super().overlaps(other, **kwargs)

        __and__ = overlaps

    comparator_factory: _ComparatorFactory[t.Any] = _Comparator


class InvalidMACAddressException(PycroftModelException, ValueError):
    pass


class DateTimeTz(DateTime):
    """A sqlalchemy type decorator corresponding to `datetime` types with time zone.

    In other words, a `mapped_column(DateTimeTz)` produces python objects of type
    :class:`pycroft.helpers.utc.DateTimeTz`.
    """

    def __init__(self):
        super().__init__(timezone=True)
