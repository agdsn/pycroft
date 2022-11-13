import datetime
import json
from decimal import Decimal

import pytest

from pycroft.helpers.i18n import localized
from pycroft.helpers.i18n.types import Money
from pycroft.helpers.i18n.serde import serialize_param, deserialize_param
from pycroft.helpers.i18n.message import Message, ErroneousMessage
from pycroft.helpers.interval import UnboundedInterval, closed, closedopen, \
    openclosed, open

now = datetime.datetime.utcnow()
then = now + datetime.timedelta(days=1)


@pytest.mark.parametrize('value', [
    "test", True, 42, 0.5, Decimal('3.8e2'), Money(Decimal(20.0), "EUR"),
    datetime.datetime.utcnow(), datetime.date.today(), datetime.timedelta(1),
    datetime.datetime.utcnow().time(), UnboundedInterval, closed(now, then), closedopen(now, then),
    openclosed(now, then), open(now, then),
])
def test_valid_serialization(value):
    s = serialize_param(value)
    try:
        json.dumps(s)
    except (ValueError, TypeError):  # pragma: no cover
        pytest.fail(f"Param {value} cannot be serialized to JSON.")
    assert deserialize_param(s) == value


def test_serialize_unknown_type():
    with pytest.raises(TypeError):
        serialize_param(object())


@pytest.mark.parametrize(
    "json",
    [
        "not JSON",
        "{foo]))>",
        "24[4]",
    ],
)
def test_no_json(json: str):
    """Test that a non-json object deserializes as :cls:`ErroneousMessage`"""
    m = Message.from_json(json)
    l = localized(json)

    assert isinstance(m, ErroneousMessage)
    for t in (m.text, l):
        assert t == json


@pytest.mark.parametrize(
    "json",
    (
        "{}",
        '{"message": "", "args": "foo"}',
        '{"message": "", "unknown_field": "bar"}',
        '{"message": "", "args": [], "kwargs": []}',
    ),
)
def test_invalid_json(json: str):
    """Test that a non-schema-conforming json object deserializes as :cls:`ErroneousMessage`"""
    m = Message.from_json(json)
    l = localized(json)

    assert isinstance(m, ErroneousMessage)
    for t in (m.text.lower(), l.lower()):
        assert "message validation failed" in t
        assert "schema" in t


@pytest.mark.parametrize(
    "json",
    ('{ "message": "foo", "args": [{"type": "custom", "value": "#InvalidArg("}] }',),
)
def test_invalid_parameter(json):
    m = Message.from_json(json)
    l = localized(json)

    assert isinstance(m, ErroneousMessage)
    for t in (m.text.lower(), l.lower()):
        assert "parameter deserialization error" in t

@pytest.mark.parametrize("serialized", ("5", "42", "42.0", "7"))
def test_numerical_strings_get_deserialized(serialized: str):
    assert localized(serialized) == serialized
