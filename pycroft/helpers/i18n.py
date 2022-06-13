# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import annotations
import typing
from datetime import date, datetime, time, timedelta
from functools import partial

import json
import operator
import traceback
from babel import Locale, dates, numbers
from babel.support import Translations
from decimal import Decimal
import collections
import jsonschema
from pycroft.helpers.interval import (
    Interval, Bound, NegativeInfinity, PositiveInfinity)

_unspecified_locale = Locale('en', 'US')
_null_translations = Translations()
_locale_lookup: typing.Callable[[], Locale] = lambda: _unspecified_locale
_translations_lookup: typing.Callable[[], Translations] = lambda: _null_translations


def get_locale() -> Locale:
    return _locale_lookup()


def get_translations() -> Translations:
    return _translations_lookup()


def set_locale_lookup(lookup_func: typing.Callable[[], Locale]) -> None:
    global _locale_lookup
    _locale_lookup = lookup_func


def set_translation_lookup(lookup_func: typing.Callable[[], Translations]) -> None:
    global _translations_lookup
    _translations_lookup = lookup_func


def gettext(message: str) -> str:
    return typing.cast(str, get_translations().ugettext(message))


def dgettext(domain: str, message: str) -> str:
    return typing.cast(str, get_translations().udgettext(domain, message))


def ngettext(singular: str, plural: str, n: int) -> str:
    return typing.cast(str, get_translations().ungettext(singular, plural, n))


def dngettext(domain: str, singular: str, plural: str, n: int) -> str:
    return typing.cast(str, get_translations().udngettext(domain, singular, plural, n))


T = typing.TypeVar("T", covariant=True)
P = typing.ParamSpec("P")


class Formattable(typing.Protocol):
    def __format__(self, format_spec: str) -> str:
        ...


OptionPolicy = typing.Literal["type-specific", "ignore"]
TypeSpecificOptions: typing.TypeAlias = dict[str, typing.Any]
Options: typing.TypeAlias = dict[type, TypeSpecificOptions]


class Formatter(typing.Protocol[T, P]):
    __option_policy__: OptionPolicy
    __call__: typing.Callable[typing.Concatenate[T, P], Formattable]
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


Money = collections.namedtuple("Money", ["value", "currency"])


@type_specific_options
def format_currency(money: Money, format=None):
    return numbers.format_currency(*money, format=format, locale=get_locale())


@type_specific_options
def format_date(d, format='medium'):
    return dates.format_date(d, format=format, locale=get_locale())


@type_specific_options
def format_datetime(d, format='medium', tzinfo=None):
    return dates.format_datetime(d, format=format, tzinfo=tzinfo,
                                 locale=get_locale())


@type_specific_options
def format_time(t, format='medium', tzinfo=None):
    return dates.format_time(t, format=format, tzinfo=tzinfo,
                             locale=get_locale())


@type_specific_options
def format_timedelta(delta, granularity='second', threshold=.85,
                     add_direction=False, format='medium'):
    return dates.format_timedelta(
        delta, granularity=granularity, threshold=threshold,
        add_direction=add_direction, format=format, locale=get_locale())


@ignore_options
def format_bool(v):
    return gettext("True") if v else gettext("False")


@ignore_options
def format_none(n):
    return gettext("None")


# NB: `interval` is actually generic in its (ordered) bound type,
#  so whether we have any type specific options or not cannot be determined statically.
#  however, we only have intervals of `date`s and `datetimes` in practice.
@type_specific_options
def format_interval(interval, **options: TypeSpecificOptions):
    lower_bound = interval.lower_bound
    upper_bound = interval.upper_bound
    assert type(lower_bound) == type(upper_bound)
    generic_options: Options = {type(lower_bound): options}
    return "{}{}, {}{}".format(
        '[' if lower_bound.closed else '(',
        format_param(lower_bound.value, generic_options)
        if not lower_bound.unbounded
        else '-∞',
        format_param(upper_bound.value, generic_options)
        if not upper_bound.unbounded
        else '∞',
        ']' if upper_bound.closed else ')',
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
    formatters = ((type_, formatter_map[type_])
                  for type_ in concrete_type.__mro__ if type_ in formatter_map)
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
    elif option_policy == 'type-specific':
        formatter_options = options.get(type_, {})
    else:
        raise RuntimeError(
            f"Invalid Value {option_policy!r} for {formatter.__name__}.__option_policy__"
        )
    return formatter(p, **formatter_options)


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
        'lower_closed': lower.closed,
        'lower_value': lower_value,
        'upper_closed': upper.closed,
        'upper_value': upper_value,
    }


def qualified_typename(type_: type) -> str:
    return type_.__module__ + '.' + type_.__name__


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
    timedelta: lambda v: {"days": v.days, "seconds": v.seconds,
                          "microseconds": v.microseconds},
    Interval: serialize_interval,
}


def deserialize_interval(value: dict[str, typing.Any]) -> Interval:
    try:
        lower_value = (deserialize_param(value['lower_value'])
                       if value['lower_value'] is not None
                       else NegativeInfinity)
        lower_bound = Bound(lower_value, value['lower_closed'])
        upper_value = (deserialize_param(value['upper_value'])
                       if value['upper_value'] is not None
                       else PositiveInfinity)
        upper_bound = Bound(upper_value, value['upper_closed'])
    except KeyError:
        raise ValueError()
    return Interval(lower_bound, upper_bound)


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
    serializers = ((type_, serialize_map[type_])
                   for type_ in concrete_type.__mro__
                   if type_ in serialize_map)
    try:
        type_, serializer = next(serializers)
    except StopIteration:
        raise TypeError("No serialization available for type {} or any"
                        "supertype".format(qualified_typename(concrete_type)))
    return {"type": qualified_typename(type_), "value": serializer(param)}


def deserialize_param(param):
    type_name = param["type"]
    try:
        deserializer = deserialize_map[type_name]
    except KeyError:
        raise TypeError("No deserialization available for type {}"
                        .format(type_name))
    return deserializer(param["value"])


schema = {
    "id": "http://agdsn.de/localized-schema#",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "description": "Message format for deferred localization.",
    "oneOf": [
        {"$ref": "#/definitions/simple"},
        {"$ref": "#/definitions/numerical"},
    ],
    "definitions": {
        "simple": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "message": {"type": "string"},
                "args": {"$ref": "#/definitions/args"},
                "kwargs": {"$ref": "#/definitions/kwargs"},
            },
            "required": ["message"],
            "additionalProperties": False,
        },
        "numerical": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "singular": {"type": "string"},
                "n": {"type": "integer"},
                "plural": {"type": "string"},
                "args": {"$ref": "#/definitions/args"},
                "kwargs": {"$ref": "#/definitions/kwargs"},
            },
            "required": ["singular", "plural", "n"],
            "additionalProperties": False,
        },
        "args": {
            "type": "array",
            "items": {"$ref": "#/definitions/param"}
        },
        "kwargs": {
            "type": "object",
            "patternProperties": {
                "^[a-zA-Z_][a-zA-Z0-9_]+": {"$ref": "#/definitions/param"}
            },
            "additionalProperties": False,
        },
        "param": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "value": {},
            },
            "required": ["type", "value"],
            "additionalProperties": False,
        },
    },
}

# TODO remove in py3.11 (replace `TSelf` by `Self`)
TMessage = typing.TypeVar("TMessage", bound="Message")


# TODO turn into ABC && properly type subclasses
class Message:
    __slots__ = ("domain", "args", "kwargs")

    @classmethod
    def from_json(cls, json_string: str) -> Message:
        try:
            obj = json.loads(json_string)
        except ValueError:
            return ErroneousMessage(json_string)
        try:
            jsonschema.validate(obj, schema)
        except jsonschema.ValidationError as e:
            return ErroneousMessage("Message validation failed: {} for "
                                    "message {}".format(e, json_string))
        args = obj.get("args", ())
        kwargs = obj.get("kwargs", {})
        try:
            args = tuple(deserialize_param(a) for a in args)
            kwargs = {k: deserialize_param(v) for k, v in kwargs.items()}
        except (TypeError, ValueError) as e:
            error = ''.join(traceback.format_exception_only(type(e), e))
            return ErroneousMessage("Parameter deserialization error: {} in "
                                    "message: {}".format(error, json_string))
        m: Message
        if 'plural' in obj:
            m = NumericalMessage(obj["singular"], obj["plural"], obj["n"],
                                 obj.get("domain"))
        else:
            m = SimpleMessage(obj["message"], obj.get("domain"))
        m.args = args
        m.kwargs = kwargs
        return m

    def __init__(self, domain: str | None = None):
        self.domain = domain
        self.args: typing.Iterable[Serializable] = ()
        self.kwargs: dict[str, Serializable] = {}

    def _base_dict(self) -> dict[str, typing.Any]:
        raise NotImplementedError()

    def _gettext(self) -> str:
        raise NotImplementedError()

    def to_json(self) -> str:
        obj = self._base_dict()
        if self.domain is not None:
            obj["domain"] = self.domain
        if self.args:
            obj["args"] = tuple(serialize_param(a) for a in self.args)
        if self.kwargs:
            obj["kwargs"] = {k: serialize_param(v)
                             for k, v in self.kwargs.items()}
        return json.dumps(obj, ensure_ascii=False)

    def format(self: TMessage, *args: Serializable, **kwargs: Serializable) -> TMessage:
        self.args = args
        self.kwargs = kwargs
        return self

    def localize(self, options: Options = None) -> str:
        if options is None:
            options = dict()

        msg = self._gettext()
        if not self.args and not self.kwargs:
            return msg
        f = partial(format_param, options=options)
        try:
            args = tuple(f(a) for a in self.args)
            kwargs = {k: f(v) for k, v in self.kwargs.items()}
            return msg.format(*args, **kwargs)
        except (TypeError, ValueError, IndexError, KeyError) as e:
            error = "".join(traceback.format_exception_only(type(e), e))
            return (
                gettext(
                    'Could not format message "{message}" '
                    "(args={args}, kwargs={kwargs}): {error}"
                )
                .format(message=msg, args=self.args, kwargs=self.kwargs, error=error)
            )


class ErroneousMessage(Message):
    def __init__(self, text):
        super().__init__(None)
        self.text = text

    def _base_dict(self):
        raise AssertionError()

    def _gettext(self):
        return self.text


class SimpleMessage(Message):
    __slots__ = ("message",)

    def __init__(self, message, domain=None):
        super().__init__(domain)
        self.message = message

    def _base_dict(self):
        return {"message": self.message}

    def _gettext(self):
        if self.domain:
            return dgettext(self.domain, self.message)
        else:
            return gettext(self.message)


class NumericalMessage(Message):
    __slots__ = ("singular", "plural", "n")

    def __init__(self, singular, plural, n, domain=None):
        super().__init__(domain)
        self.singular = singular
        self.plural = plural
        self.n = n

    def _base_dict(self):
        return {"singular": self.singular, "plural": self.plural, "n": self.n}

    def _gettext(self):
        if self.domain:
            return dngettext(self.domain, self.singular, self.plural, self.n)
        else:
            return ngettext(self.singular, self.plural, self.n)


def localized(json_string: str, options: Options | None = None):
    return Message.from_json(json_string).localize(options)


def deferred_gettext(message) -> SimpleMessage:
    return SimpleMessage(message)


def deferred_dgettext(domain: str, message: str) -> SimpleMessage:
    return SimpleMessage(message, domain)


def deferred_ngettext(singular, plural, n) -> NumericalMessage:
    return NumericalMessage(singular, plural, n)


def deferred_dngettext(domain, singular, plural, n) -> NumericalMessage:
    return NumericalMessage(singular, plural, n, domain)
