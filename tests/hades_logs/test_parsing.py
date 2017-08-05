from datetime import datetime
from unittest import TestCase

from hades_logs.parsing import RadiusLogEntry, parse_vlan, attrlist_to_dict, ParsingError


class UnauthTrafficEntryTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.raw_entry = [
            '00:de:ad:be:ef:00',
            'Access-Accept',
            ['traffic'],
            [['Egress-VLAN-Name', '"2hades-unauth"']],
            1501623826.391414,
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

    # TODO: test time
    # TODO: test invalid Values pass the `ParsingError`
    # TODO: test equality


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
