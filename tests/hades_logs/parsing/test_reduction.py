import pytest

from hades_logs import RadiusLogEntry
from hades_logs.parsing import reduce_to_first_occurrence


@pytest.fixture(scope='module')
def func():
    return reduce_to_first_occurrence


@pytest.fixture(scope='module')
def elements():
    return [0, 2, 1, 1, 1, 3, 4, 1, 1, 3, 3, 5, 5, 5, 0, 0]


def test_simple_reduction(elements, func):
    assert list(func(elements)) == [0, 2, 1, 3, 4, 1, 3, 5, 0]


def test_nontrivial_equivalence_gives_first_representative(elements, func):
    def _eq(a, b):
        """Return whether a and b are equivalent modulo 2"""
        return (a - b) % 2 == 0

    assert list(func(elements, comparator=_eq)) == [0, 1, 4, 1, 0]


class TestRadiusLogsWorkAsWell:
    @pytest.fixture(scope='class')
    def entries(self):
        timestamp = 1501623826.391414
        return [RadiusLogEntry(*e) for e in [
            ('00:de:ad:be:ef:00',
             'Access-Accept',
             ['traffic'],
             [['Egress-VLAN-Name', '"2hades-unauth"']],
             timestamp),
            ('00:de:ad:be:ef:00',
             'Access-Accept',
             ['traffic'],
             [['Egress-VLAN-Name', '"2hades-unauth"']],
             timestamp - 50),
            ('00:de:ad:be:ef:00',
             'Access-Accept',
             ['violation'],
             [['Egress-VLAN-Name', '"2hades-unauth"']],
             timestamp - 100),
        ]]

    @pytest.fixture(scope='class')
    def reduced(self, entries, func):
        return list(func(entries, comparator=RadiusLogEntry.effectively_equal))

    def test_length(self, reduced):
        assert len(reduced) == 2

    def test_first_entry(self, entries, reduced):
        assert reduced[0] == entries[0]

    def test_last_entry(self, entries, reduced):
        assert reduced[-1] == entries[-1]
