from datetime import datetime, timezone
from unittest import TestCase

from hades_logs import RadiusLogEntry
from hades_logs.parsing import ParsingError


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
                         datetime.fromtimestamp(self.raw_entry[-1],
                                                tz=timezone.utc))

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
