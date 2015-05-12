# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.helpers.building_helper
    ~~~~~~~~~~~~~~

    :copyright: (c) 2012 by AG DSN.
"""
import re


def sort_buildings(buildings):
    number_re = re.compile(r"[0-9]+")
    letter_re = re.compile(r"[a-z]")

    def make_sort_key(building):
        number = number_re.search(building.number)
        letter = letter_re.search(building.number.lower())

        if letter:
            return ord(letter.group(0)) + 256 * int(number.group(0))

        return 256 * int(number.group(0))

    sorted_buildings = sorted(buildings, key=make_sort_key)

    return sorted_buildings
