import datetime
import json
from decimal import Decimal

import pytest

from pycroft.helpers.i18n import Money, serialize_param, deserialize_param, \
    Message, ErroneousMessage
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
    except (ValueError, TypeError):
        pytest.fail(f"Param {value} cannot be serialized to JSON.")
    assert deserialize_param(s) == value


def test_serialize_unknown_type():
    with pytest.raises(TypeError):
        serialize_param(object())


@pytest.mark.parametrize('json', [
    "not JSON",
    '{"key": "value"}',
])
def test_erroneous_json(json: str):
    assert isinstance(Message.from_json("not JSON"), ErroneousMessage)
