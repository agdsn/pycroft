from unittest import TestCase

from hades_logs.parsing import parse_vlan, ParsingError


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
