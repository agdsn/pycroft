# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import unittest
from pycroft.helpers.errorcode import digits, Type1Code, Type2Code


class Test_010_digits(unittest.TestCase):
    def test_0010_zero(self):
        self.assertEqual([0], list(digits(0)))

    def test_0020_multiple(self):
        self.assertEqual([4, 3, 2, 1], list(digits(1234)))

    def test_0030_negative(self):
        self.assertEqual([4, 3, 2, 1], list(digits(-1234)))


class Test_010_Type1Code(unittest.TestCase):
    def test_0010_calculate_zero(self):
        self.assertEqual(0, Type1Code.calculate(0))

    def test_0020_calculate_mod10(self):
        self.assertEqual(0, Type1Code.calculate(1234))

    def test_0030_validate_zero(self):
        self.assertTrue(Type1Code.is_valid(0, 0))

    def test_0040_validate_mod10(self):
        self.assertTrue(Type1Code.is_valid(1234, 0))


class Test_010_Type2Code(unittest.TestCase):
    def test_0010_calculate_zero(self):
        self.assertEqual(98, Type2Code.calculate(0))

    def test_0020_calculate_mod10(self):
        self.assertEqual(82, Type2Code.calculate(1234))

    def test_0030_validate_zero(self):
        self.assertTrue(Type2Code.is_valid(0, 98))

    def test_0040_validate_mod10(self):
        self.assertTrue(Type2Code.is_valid(1234, 82))
