# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import pytest

from pycroft.lib.facilities import sort_buildings


@pytest.fixture
def before():
    return ["41A", "41", "41B", "3", "5", "41D", "9", "11", "1", "7", "41C"]


@pytest.fixture
def after():
    return ["1", "3", "5", "7", "9", "11", "41", "41A", "41B", "41C", "41D"]


@pytest.fixture
def fake_dorm():
    class fake_dorm:
        def __init__(self, num):
            self.number = num
            self.street = "fake street"
    return fake_dorm


def test_building_name_sorting(fake_dorm, before, after):
    sorted = sort_buildings([fake_dorm(num) for num in before])
    assert [d.number for d in sorted] == after
