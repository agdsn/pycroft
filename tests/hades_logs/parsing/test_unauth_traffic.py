from datetime import datetime, timezone

import pytest

from hades_logs import RadiusLogEntry
from hades_logs.parsing import ParsingError


@pytest.fixture(scope='module')
def timestamp():
    return 1501623826.391414

@pytest.fixture(scope='module')
def raw_entry(timestamp):
    return [
        '00:de:ad:be:ef:00',
        'Access-Accept',
        ['traffic'],
        [['Egress-VLAN-Name', '"2hades-unauth"']],
        timestamp,
    ]


@pytest.fixture(scope='module')
def entry(raw_entry):
    return RadiusLogEntry(*raw_entry)


def test_mac(entry):
    assert entry.mac == "00:de:ad:be:ef:00"

def test_vlan(entry):
    assert entry.vlans == ["hades-unauth (untagged)"]

def test_accepted(entry):
    assert entry.accepted
    assert entry

def test_time(entry, raw_entry):
    assert entry.time == \
      datetime.fromtimestamp(raw_entry[-1], tz=timezone.utc)

def test_groups(entry):
    assert entry.groups == ['traffic']

def test_timestamp_parsing_works(entry, timestamp):
    assert entry.time.timestamp() == pytest.approx(timestamp, 0.001)


@pytest.fixture
def invalid_entry(raw_entry):
    invalid_entry = raw_entry.copy()
    invalid_entry[3][0][1] = '3Invalid'
    return RadiusLogEntry(*invalid_entry)


def test_invalid_vlan_name_raises(invalid_entry):
    with pytest.raises(ParsingError):
        # noinspection PyStatementEffect
        invalid_entry.vlans  # noqa: B018
