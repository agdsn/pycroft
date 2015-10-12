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
    def make_sort_key(building):
        s = re.split('(\d+)([a-zA-Z]?)', building.number)
        if len(s) != 4: return building.street, building.number #split unsuccessful
        return building.street, (int(s[1]), s[2].lower())

    sorted_buildings = sorted(buildings, key=make_sort_key)

    return sorted_buildings
