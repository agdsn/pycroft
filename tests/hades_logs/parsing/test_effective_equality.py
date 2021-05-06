import pytest

from hades_logs import RadiusLogEntry


class TestEffectiveEquality:
    @pytest.fixture(scope='class')
    def timestamp(self):
        return 1501623826.391414

    @pytest.fixture(scope='class')
    def entry(self, timestamp):
        return RadiusLogEntry(
            '00:de:ad:be:ef:00',
            'Access-Accept',
            ['traffic'],
            [['Egress-VLAN-Name', '"2hades-unauth"']],
            timestamp,
        )

    def test_comparison_to_incomplete_type_gives_false(self, entry):
        assert not RadiusLogEntry.effectively_equal(entry, object())

    def test_reflexivity(self, entry):
        assert RadiusLogEntry.effectively_equal(entry, entry)

    def test_effectively_equal_different_time(self, entry, timestamp):
        good_entry = RadiusLogEntry(
            '00:de:ad:be:ef:00',
            'Access-Accept',
            ['traffic'],
            [['Egress-VLAN-Name', '"2hades-unauth"']],
            timestamp - 50,
        )
        assert RadiusLogEntry.effectively_equal(entry, good_entry)

    def test_not_effectively_equal_different_group(self, entry, timestamp):
        bad_entry = RadiusLogEntry(
            '00:de:ad:be:ef:00',
            'Access-Accept',
            ['violation'],
            [['Egress-VLAN-Name', '"2hades-unauth"']],
            timestamp - 50,
        )
        assert not RadiusLogEntry.effectively_equal(entry, bad_entry)

    def test_not_effectively_equal_different_group_same_time(self, entry, timestamp):
        bad_entry = RadiusLogEntry(
            '00:de:ad:be:ef:00',
            'Access-Accept',
            ['violation'],
            [['Egress-VLAN-Name', '"2hades-unauth"']],
            timestamp,
        )
        assert not RadiusLogEntry.effectively_equal(entry, bad_entry)
