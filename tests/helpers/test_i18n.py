# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import datetime
import json
import traceback
import unittest
from unittest import TestCase
import jsonschema
from pycroft.helpers.i18n import (
    ErroneousMessage, Message, NumericalMessage, SimpleMessage,
    deserialize_param, serialize_param, schema, deferred_dgettext,
    deferred_dngettext, deferred_gettext, deferred_ngettext, format_datetime)
from pycroft.helpers.interval import (
    UnboundedInterval, closed, closedopen, openclosed, open)


class TestParameterSerialization(unittest.TestCase):
    def assertValidSerialization(self, param):
        s = serialize_param(param)
        try:
            json.dumps(s)
        except (ValueError, TypeError):
            self.fail("Param {} cannot be serialized to JSON.".format(param))
        self.assertEqual(deserialize_param(s), param)

    def test_serialize_string(self):
        self.assertValidSerialization("test")

    def test_serialize_unicode(self):
        self.assertValidSerialization(u"test")

    def test_serialize_bool(self):
        self.assertValidSerialization(True)

    def test_serialize_int(self):
        self.assertValidSerialization(42)

    def test_serialize_float(self):
        self.assertValidSerialization(0.5)

    def test_serialize_datetime(self):
        self.assertValidSerialization(datetime.datetime.utcnow())

    def test_serialize_date(self):
        self.assertValidSerialization(datetime.date.today())

    def test_serialize_timedelta(self):
        self.assertValidSerialization(datetime.timedelta(1))

    def test_serialize_time(self):
        self.assertValidSerialization(datetime.datetime.utcnow().time())

    def test_serialize_interval(self):
        self.assertValidSerialization(UnboundedInterval)
        now = datetime.datetime.utcnow()
        then = now + datetime.timedelta(1)
        self.assertValidSerialization(closed(now, then))
        self.assertValidSerialization(closedopen(now, then))
        self.assertValidSerialization(openclosed(now, then))
        self.assertValidSerialization(open(now, then))

    def test_serialize_unknown_type(self):
        self.assertRaises(TypeError, serialize_param, object())


class DeferredMessageTestCase(TestCase):
    validator = jsonschema.Draft4Validator(schema)

    def assertValidJSON(self, json_string):
        try:
            obj = json.loads(json_string)
        except (ValueError, TypeError):
            self.fail()
        try:
            self.validator.validate(obj)
        except jsonschema.ValidationError as e:
            self.fail("Export failed schema validation: {}".format(e))

    def assertMessageEquals(self, m, domain, args, kwargs, expected_result):
        self.assertEqual(m.domain, domain)
        self.assertEqual(m.args, args)
        self.assertEqual(m.kwargs, kwargs)
        self.assertEqual(m.localize(), expected_result)

    def assertSimpleMessageCorrect(self, m, message, domain, args, kwargs,
                                   expected_result):
        self.assertIsInstance(m, SimpleMessage)
        self.assertEqual(m.message, message)
        self.assertMessageEquals(m, domain, args, kwargs, expected_result)
        json_string = m.to_json()
        self.assertValidJSON(json_string)
        m2 = Message.from_json(json_string)
        self.assertIsInstance(m2, SimpleMessage)
        self.assertMessageEquals(m2, domain, args, kwargs, expected_result)

    def assertNumericMessageCorrect(self, m, singular, plural, n, domain,
                                    args, kwargs, expected_result):
        self.assertIsInstance(m, NumericalMessage)
        self.assertEqual(m.singular, singular)
        self.assertEqual(m.plural, plural)
        self.assertEqual(m.n, n)
        self.assertMessageEquals(m, domain, args, kwargs, expected_result)
        json_string = m.to_json()
        self.assertValidJSON(json_string)
        m2 = Message.from_json(json_string)
        self.assertIsInstance(m2, NumericalMessage)
        self.assertMessageEquals(m2, domain, args, kwargs, expected_result)


class TestJSONExport(DeferredMessageTestCase):
    def test_invalid_json(self):
        self.assertIsInstance(Message.from_json("not JSON"), ErroneousMessage)

    def test_wrong_json(self):
        json_string = json.dumps({"key": "value"})
        self.assertIsInstance(Message.from_json(json_string), ErroneousMessage)

    def test_simple(self):
        message = "test"
        m = deferred_gettext(message)
        self.assertSimpleMessageCorrect(m, message, None, (), {}, message)

    def test_simple_with_domain(self):
        message = "test"
        domain = "domain"
        m = deferred_dgettext(domain, message)
        self.assertSimpleMessageCorrect(m, message, domain, (), {}, message)

    def test_simple_format_args(self):
        message = "test {} at {}"
        arg1 = "arg1"
        arg2 = datetime.datetime.utcnow()
        m = deferred_gettext(message).format(arg1, arg2)
        expected_result = message.format(arg1, format_datetime(arg2))
        self.assertSimpleMessageCorrect(m, message, None, (arg1, arg2), {},
                                        expected_result)

    def test_simple_format_kwargs(self):
        message = "test {arg1} at {arg2}"
        arg1 = "arg1"
        arg2 = datetime.datetime.utcnow()
        m = deferred_gettext(message).format(arg1=arg1, arg2=arg2)
        expected_result = message.format(arg1=arg1, arg2=format_datetime(arg2))
        self.assertSimpleMessageCorrect(m, message, None, (),
                                        {"arg1": arg1, "arg2": arg2},
                                        expected_result)

    def test_singular(self):
        singular = "singular"
        plural = "plural"
        n = 1
        m = deferred_ngettext(singular, plural, n)
        self.assertNumericMessageCorrect(m, singular, plural, n, None, (), {},
                                         singular)

    def test_singular_domain(self):
        singular = "singular"
        plural = "plural"
        n = 1
        domain = "domain"
        m = deferred_dngettext(domain, singular, plural, n)
        self.assertNumericMessageCorrect(m, singular, plural, n, domain, (), {},
                                         singular)

    def test_plural(self):
        singular = "singular"
        plural = "plural"
        n = 1000
        domain = "domain"
        m = deferred_dngettext(domain, singular, plural, n)
        self.assertNumericMessageCorrect(m, singular, plural, n, domain, (), {},
                                         plural)

    def get_format_error_message(self, message, args, kwargs):
        try:
            message.format(*args, **kwargs)
        except (TypeError, ValueError, IndexError, KeyError) as e:
            return u''.join(traceback.format_exception_only(type(e), e))
        else:
            raise AssertionError()

    def test_missing_positional_argument(self):
        message = u"{0} {1}"
        args = (1,)
        kwargs = {}
        error = self.get_format_error_message(message, args, kwargs)
        m = deferred_gettext(message).format(*args)
        text = (u'Could not format message "{}" (args={}, kwargs={}): {}'
                .format(message, args, kwargs, error))
        self.assertSimpleMessageCorrect(m, message, None, args, kwargs, text)

    def test_missing_keyword_argument(self):
        message = u"{foo}"
        args = (1,)
        kwargs = {}
        error = self.get_format_error_message(message, args, kwargs)
        m = deferred_gettext(message).format(*args)
        text = (u'Could not format message "{}" (args={}, kwargs={}): {}'
                .format(message, args, kwargs, error))
        self.assertSimpleMessageCorrect(m, message, None, args, kwargs, text)
