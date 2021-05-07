# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import datetime
import json
import traceback
from decimal import Decimal

import jsonschema
import pytest

from pycroft.helpers.i18n import (
    ErroneousMessage, Message, NumericalMessage, SimpleMessage,
    deserialize_param, serialize_param, schema, deferred_dgettext,
    deferred_dngettext, deferred_gettext, deferred_ngettext, format_datetime,
    Money)
from pycroft.helpers.interval import (
    UnboundedInterval, closed, closedopen, openclosed, open)


now = datetime.datetime.utcnow()
then = now + datetime.timedelta(days=1)


@pytest.mark.parametrize('value', [
    "test",
    True,
    42,
    0.5,
    Decimal('3.8e2'),
    Money(Decimal(20.0), "EUR"),
    datetime.datetime.utcnow(),
    datetime.date.today(),
    datetime.timedelta(1),
    datetime.datetime.utcnow().time(),
    UnboundedInterval,
    closed(now, then),
    closedopen(now, then),
    openclosed(now, then),
    open(now, then),
])
def test_valid_serialization(value):
    s = serialize_param(value)
    try:
        json.dumps(s)
    except (ValueError, TypeError):
        pytest.fail(f"Param {value} cannot be serialized to JSON.")
    assert deserialize_param(s) == value


def test_serialize_unknown_type():
    with pytest.raises(TypeError):
        serialize_param(object())


def assertMessageEquals(m, domain, args, kwargs, expected_result):
    assert m.domain == domain
    assert m.args == args
    assert m.kwargs == kwargs
    assert m.localize() == expected_result


validator = jsonschema.Draft4Validator(schema)


def assertValidJSON(json_string):
    try:
        obj = json.loads(json_string)
    except (ValueError, TypeError):
        pytest.fail()
    try:
        validator.validate(obj)
    except jsonschema.ValidationError as e:
        pytest.fail(f"Export failed schema validation: {e}")


def assertSimpleMessageCorrect(m, message, domain, args, kwargs,
                               expected_result):
    assert isinstance(m, SimpleMessage)
    assert m.message == message
    assertMessageEquals(m, domain, args, kwargs, expected_result)
    json_string = m.to_json()
    assertValidJSON(json_string)
    m2 = Message.from_json(json_string)
    assert isinstance(m2, SimpleMessage)
    assertMessageEquals(m2, domain, args, kwargs, expected_result)


def assertNumericMessageCorrect(m, singular, plural, n, domain,
                                args, kwargs, expected_result):
    assert isinstance(m, NumericalMessage)
    assert m.singular == singular
    assert m.plural == plural
    assert m.n == n
    assertMessageEquals(m, domain, args, kwargs, expected_result)
    json_string = m.to_json()
    assertValidJSON(json_string)
    m2 = Message.from_json(json_string)
    assert isinstance(m2, NumericalMessage)
    assertMessageEquals(m2, domain, args, kwargs, expected_result)


@pytest.mark.parametrize('json', [
    "not JSON",
    '{"key": "value"}',
])
def test_erroneous_json(json: str):
    assert isinstance(Message.from_json("not JSON"), ErroneousMessage)


def get_format_error_message(message, args, kwargs):
    try:
        message.format(*args, **kwargs)
    except (TypeError, ValueError, IndexError, KeyError) as e:
        return u''.join(traceback.format_exception_only(type(e), e))
    else:
        raise AssertionError()


class TestSimpleMessages:
    def test_simple(self):
        message = "test"
        m = deferred_gettext(message)
        assertSimpleMessageCorrect(m, message, None, (), {}, message)

    def test_simple_with_domain(self):
        message = "test"
        domain = "domain"
        m = deferred_dgettext(domain, message)
        assertSimpleMessageCorrect(m, message, domain, (), {}, message)

    def test_simple_format_args(self):
        message = "test {} at {}"
        arg1 = "arg1"
        arg2 = datetime.datetime.utcnow()
        m = deferred_gettext(message).format(arg1, arg2)
        expected_result = message.format(arg1, format_datetime(arg2))
        assertSimpleMessageCorrect(m, message,
                                   None, (arg1, arg2), {}, expected_result)

    def test_simple_format_kwargs(self):
        message = "test {arg1} at {arg2}"
        arg1 = "arg1"
        arg2 = datetime.datetime.utcnow()
        m = deferred_gettext(message).format(arg1=arg1, arg2=arg2)
        expected_result = message.format(arg1=arg1, arg2=format_datetime(arg2))
        assertSimpleMessageCorrect(m, message,
                                   None, (), {"arg1": arg1, "arg2": arg2}, expected_result)


class TestNumericMessages:
    def test_singular(self):
        singular = "singular"
        plural = "plural"
        n = 1
        m = deferred_ngettext(singular, plural, n)
        assertNumericMessageCorrect(m, singular, plural, n, None, (), {}, singular)

    def test_singular_domain(self):
        singular = "singular"
        plural = "plural"
        n = 1
        domain = "domain"
        m = deferred_dngettext(domain, singular, plural, n)
        assertNumericMessageCorrect(m, singular, plural, n, domain, (), {}, singular)

    def test_plural(self):
        singular = "singular"
        plural = "plural"
        n = 1000
        domain = "domain"
        m = deferred_dngettext(domain, singular, plural, n)
        assertNumericMessageCorrect(m, singular, plural, n, domain, (), {}, plural)


class TestErrorFormatting:
    def test_missing_positional_argument(self):
        message = u"{0} {1}"
        args = (1,)
        kwargs = {}
        error = get_format_error_message(message, args, kwargs)
        m = deferred_gettext(message).format(*args)
        text = (u'Could not format message "{}" (args={}, kwargs={}): {}'
                .format(message, args, kwargs, error))
        assertSimpleMessageCorrect(m, message, None, args, kwargs, text)

    def test_missing_keyword_argument(self):
        message = u"{foo}"
        args = (1,)
        kwargs = {}
        error = get_format_error_message(message, args, kwargs)
        m = deferred_gettext(message).format(*args)
        text = (u'Could not format message "{}" (args={}, kwargs={}): {}'
                .format(message, args, kwargs, error))
        assertSimpleMessageCorrect(m, message, None, args, kwargs, text)
