import unittest

from pycroft.model.base import _Base

__author__ = 'shreyder'


class Test_010_SnakeCaseConversion(unittest.TestCase):

    def test_0010_single_noun(self):
        self.assertEqual(_Base._to_snake_case("Noun"), "noun")

    def test_0020_single_acronym(self):
        self.assertEqual(_Base._to_snake_case("HTML"), "html")

    def test_0020_single_acronym_number(self):
        self.assertEqual(_Base._to_snake_case("HTML40"), "html40")

    def test_0030_acronym_noun(self):
        self.assertEqual(_Base._to_snake_case("HTMLParser"), "html_parser")

    def test_0030_acronym_number_noun(self):
        self.assertEqual(_Base._to_snake_case("HTML40Parser"), "html40_parser")

    def test_0040_noun_acronym(self):
        self.assertEqual(_Base._to_snake_case("SafeHTML"), "safe_html")

    def test_0040_noun_number_acronym(self):
        self.assertEqual(_Base._to_snake_case("Version2CSV"), "version2_csv")
