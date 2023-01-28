# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.types
~~~~~~~~~~~~~~~~~~~
"""
from datetime import datetime
from decimal import Decimal
from numbers import Number
from typing import Any

import ipaddr
from psycopg2._range import DateTimeTZRange
from sqlalchemy import String, TypeDecorator, Integer, DateTime, literal
from sqlalchemy.dialects.postgresql import MACADDR, INET, Range
from sqlalchemy.dialects.postgresql.ranges import TSTZRANGE

from pycroft.helpers.interval import Interval
from pycroft.helpers.net import mac_regex
from pycroft.model.exc import PycroftModelException


# NOTES
# In the type decorators below, `dialect` will be `sqlalchemy.dialects.postgresql.base.PGDialect`.

class _IPType(TypeDecorator):
    impl = String(50)
    #:
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """"""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(INET)
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        """"""
        if value is None:
            return value
        return str(value)


class IPAddress(_IPType):
    #:
    cache_ok = True

    def python_type(self):
        """"""
        return ipaddr._BaseIP

    def process_result_value(self, value, dialect):
        """"""
        if value is None:
            return value
        return ipaddr.IPAddress(value)


class IPNetwork(_IPType):
    #:
    cache_ok = True

    def python_type(self):
        """"""
        return ipaddr._BaseNet

    def process_result_value(self, value, dialect):
        """"""
        if value is None:
            return value
        return ipaddr.IPNetwork(value)


class MACAddress(TypeDecorator):
    impl = String(10)
    #:
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """"""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(MACADDR)
        else:
            return dialect.type_descriptor(self.impl)

    def process_result_value(self, value, dialect):
        """"""
        if dialect.name == 'postgresql':
            return value
        return "{}:{}:{}:{}:{}:{}".format(value[0:2], value[2:4], value[4:6],
                                          value[6:8], value[8:10], value[10:12])

    def process_bind_param(self, value, dialect):
        """"""
        if value is None:
            return value
        m = mac_regex.match(value)
        if m is None:
            raise ValueError(f'"{value}" is not a valid MAC address.')
        groups = m.groupdict()
        return "".join((groups["byte1"], groups["byte2"], groups["byte3"],
                        groups["byte4"], groups["byte5"], groups["byte6"]))

    def python_type(self):
        """"""
        return str


class Money(TypeDecorator):
    impl = Integer
    #:
    cache_ok = True

    def python_type(self):
        """"""
        return Decimal

    @staticmethod
    def process_bind_param(value, dialect):
        """"""
        if not isinstance(value, Number):
            raise ValueError("{} is not a valid money amount".format(
                repr(value)))
        cents = Decimal(value).scaleb(2)
        if int(cents) != cents:
            raise ValueError("{} is not a valid money amount".format(
                Decimal(value)))
        else:
            return int(cents)

    @staticmethod
    def process_result_value(value, dialect):
        """"""
        return Decimal(value).scaleb(-2)


class TsTzRange(TypeDecorator):
    impl = TSTZRANGE
    #:
    cache_ok = True

    def python_type(self):
        """"""
        return Interval

    def process_literal_param(self, value, dialect):
        """"""
        if value is None:
            return None
        return f"'{str(value)}'"

    def process_bind_param(self, value: Interval | None, dialect) -> str | None:
        """gets PY TYPE, returns DB TYPE"""
        if value is None:
            return None

        return str(value)

    def process_result_value(self, value: DateTimeTZRange | None, dialect)\
            -> Interval | None:
        """"""
        if value is None:
            return None
        if isinstance(value, (Range, DateTimeTZRange)):
            return Interval.from_explicit_data(
                value.lower, value.lower_inc,
                value.upper, value.upper_inc
            )

        # see https://github.com/sqlalchemy/sqlalchemy/discussions/6942
        raise PycroftModelException(
            f"Unable to deserialize TsTzRange value {value!r} of type {type(value)}."
            " Usually, this value should've been deserialized by psycopg2 into a"
            " DatetimeTzRange.  Did you make a mistake in your query?"
            " Note that you may have to use `cast(…, TsTzRange)` to let sqlalchemy know"
            " of the return type –– even if you specified the type in `literal()` already!"
        )

    class comparator_factory(TSTZRANGE.Comparator):
        def contains(self, other: Any, **kwargs) -> None:
            """Provide the functionality of the `@>` operator for Intervals.

            :param other: can be an interval, a tz-aware datetime,
               or column-like sql expressions with these types.

            If any `.contains()` call does not work, you can add support here.
            """
            if other is None:
                raise PycroftModelException('You cannot use `.contains()` with `null` (`None`)!')

            op = self.op('@>', is_comparison=True)
            if isinstance(other, datetime):
                if not other.tzinfo:
                    raise PycroftModelException(
                        'You cannot use `.contains()` with a non-timezone-aware datetime'
                        f' ({other})!'
                    )
                return op(literal(other, type_=DateTimeTz))

            return op(other)

        def overlaps(self, other: Any, **kwargs):
            """Provide the functionality of the `&&` operator for Intervals. """
            if other is None:
                raise PycroftModelException(
                    'You cannot use `.overlaps()`/`&` with `null` (`None`)!'
                )
            return self.op('&&', is_comparison=True)(other)

        __and__ = overlaps


class InvalidMACAddressException(PycroftModelException, ValueError):
    pass


class DateTimeTz(DateTime):
    def __init__(self):
        super().__init__(timezone=True)
