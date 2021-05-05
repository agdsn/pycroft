from unittest import TestCase

from hades_logs import RadiusLogEntry


class EffectiveEqualityTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.timestamp = 1501623826.391414
        self.raw_entry = [
            '00:de:ad:be:ef:00',
            'Access-Accept',
            ['traffic'],
            [['Egress-VLAN-Name', '"2hades-unauth"']],
            self.timestamp,
        ]
        self.entry = RadiusLogEntry(*self.raw_entry)

    def assert_effective_equality_to_sample(self, other, equal=True):
        """Assert effective Equality of ``other`` to ``self.entry``"""
        do_assert = self.assertTrue if equal else self.assertFalse
        do_assert(RadiusLogEntry.effectively_equal(self.entry, other))

    def test_comparison_to_incomplete_type_gives_false(self):
        self.assert_effective_equality_to_sample(object(), equal=False)

    def test_idempotency(self):
        self.assert_effective_equality_to_sample(self.entry)

    def test_effectively_equal_different_time(self):
        good_entry = RadiusLogEntry(
            '00:de:ad:be:ef:00',
            'Access-Accept',
            ['traffic'],
            [['Egress-VLAN-Name', '"2hades-unauth"']],
            self.timestamp - 50,
        )
        self.assert_effective_equality_to_sample(good_entry)

    def test_not_effectively_equal_different_group(self):
        bad_entry = RadiusLogEntry(
            '00:de:ad:be:ef:00',
            'Access-Accept',
            ['violation'],
            [['Egress-VLAN-Name', '"2hades-unauth"']],
            self.timestamp - 50,
        )
        self.assert_effective_equality_to_sample(bad_entry, equal=False)

    def test_not_effectively_equal_different_group_same_time(self):
        bad_entry = RadiusLogEntry(
            '00:de:ad:be:ef:00',
            'Access-Accept',
            ['violation'],
            [['Egress-VLAN-Name', '"2hades-unauth"']],
            self.timestamp,
        )
        self.assert_effective_equality_to_sample(bad_entry, equal=False)
