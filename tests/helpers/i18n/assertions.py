import json

import jsonschema
import pytest

from pycroft.helpers.i18n import schema, SimpleMessage, Message, NumericalMessage


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
