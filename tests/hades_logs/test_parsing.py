from datetime import datetime
from unittest import TestCase

from hades_logs.parsing import RadiusLogEntry, parse_vlan, attrlist_to_dict, \
    ParsingError, reduce_to_first_occurrence


class UnauthTrafficEntryTestCase(TestCase):
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

    def test_mac(self):
        self.assertEqual(self.entry.mac, "00:de:ad:be:ef:00")

    def test_vlan(self):
        self.assertEqual(self.entry.vlans, ["hades-unauth (untagged)"])

    def test_accepted(self):
        self.assertTrue(self.entry.accepted)
        self.assertTrue(self.entry)

    def test_time(self):
        self.assertEqual(self.entry.time,
                         datetime.fromtimestamp(self.raw_entry[-1]))

    def test_groups(self):
        self.assertEqual(self.entry.groups, ['traffic'])

    def test_timestamp_parsing_works(self):
        self.assertAlmostEqual(self.entry.time.timestamp(), self.timestamp,
                               places=3)

    def test_invalid_vlan_name_raises(self):
        invalid_entry = self.raw_entry.copy()
        invalid_entry[3][0][1] = '3Invalid'
        entry = RadiusLogEntry(*invalid_entry)
        with self.assertRaises(ParsingError):
            entry.vlans  # pylint: disable=pointless-statement


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


class EntryRejectionTestCase(TestCase):
    def assert_acceptance_from_reply(self, reply, should_accept=False):
        entry = RadiusLogEntry(mac=None, reply=reply, groups=None,
                               raw_attributes=None, timestamp=None)
        if should_accept:
            self.assertTrue(entry.accepted)
            self.assertTrue(entry)
        else:
            self.assertFalse(entry.accepted)
            self.assertFalse(entry)

    def test_explicit_reject(self):
        self.assert_acceptance_from_reply("Access-Reject")

    def test_implicit_reject(self):
        self.assert_acceptance_from_reply("SomeBogusValue")

    def test_accept(self):
        self.assert_acceptance_from_reply("Access-Accept", should_accept=True)


class VLANParsingTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.parse = parse_vlan

    def test_correct_untagged(self):
        self.assertEqual(self.parse('"2hades-unauth"'), "hades-unauth (untagged)")

    def test_correct_untagged_unstriped(self):
        self.assertEqual(self.parse("2Wu5"), "Wu5 (untagged)")

    def test_correct_tagged(self):
        self.assertEqual(self.parse("1toothstone"), "toothstone (tagged)")

    def test_bad_taggedness_raises_parsingerror(self):
        with self.assertRaises(ParsingError):
            self.parse('"3some-vlan"')

    def test_empty_name_raises_parsingerror(self):
        with self.assertRaises(ParsingError):
            self.parse('"2"')


class AttrListConversionTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.to_dict = attrlist_to_dict

    def test_assert_unhashable_key_raises_typeerror(self):
        with self.assertRaises(TypeError):
            self.to_dict([(["listsarebadaskeys"], "valuedoesntmatter")])

    def test_all_values_parsed_correctly(self):
        dict_gotten = self.to_dict([
            ('Egress-VLAN-Name', "2hades-unauth"),
            ('Egress-VLAN-Name', "1toothstone"),
            ('Egress-VLAN-Name2', "2Wu5"),
            ('Other-Attribute', '')
        ])
        self.assertEqual(dict_gotten, {
            'Egress-VLAN-Name': ["2hades-unauth", "1toothstone"],
            'Egress-VLAN-Name2': ["2Wu5"],
            'Other-Attribute': [''],
        })


class ReductionTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.func = reduce_to_first_occurrence
        self.elements = [0, 2, 1, 1, 1, 3, 4, 1, 1, 3, 3, 5, 5, 5, 0, 0]


    def test_simple_reduction(self):
        self.assertEqual(list(self.func(self.elements)),
                         [0, 2, 1, 3, 4, 1, 3, 5, 0])

    def test_nontrivial_equivalence_gives_first_representative(self):
        def _eq(a, b):
            """Return whether a and b are equivalent modulo 2"""
            return (a - b) % 2 == 0

        self.assertEqual(list(self.func(self.elements, comparator=_eq)),
                         [0, 1, 4, 1, 0])

    def test_radius_logs_work_as_well(self):
        timestamp = 1501623826.391414
        entries = [RadiusLogEntry(*e) for e in [
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
        reduced = list(self.func(entries, comparator=RadiusLogEntry.effectively_equal))
        self.assertEqual(len(reduced), 2)
        self.assertEqual(reduced[0], entries[0])
        self.assertEqual(reduced[-1], entries[-1])
