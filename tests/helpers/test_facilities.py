# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import unittest
from pycroft.helpers.facilities import sort_dormitories

class Test_010_SimpleDormitoryHelpers(unittest.TestCase):
    def test_0010_dormitory_name_sorting(self):
        before = ["41A", "41", "41B", "3", "5", "41D", "9", "11", "1", "7", "41C"]
        after = ["1", "3", "5", "7", "9", "11", "41", "41A", "41B", "41C", "41D"]

        class fake_dorm(object):
            def __init__(self, num):
                self.number = num

        sorted = sort_dormitories([fake_dorm(num) for num in before])
        self.assertEqual([d.number for d in sorted], after)
