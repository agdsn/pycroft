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

from pycroft.model.facilities import Building


def sort_buildings(buildings):
    def make_sort_key(building):
        s = re.split('(\d+)([a-zA-Z]?)', building.number)
        if len(s) != 4: return building.street, building.number #split unsuccessful
        return building.street, (int(s[1]), s[2].lower())

    sorted_buildings = sorted(buildings, key=make_sort_key)

    return sorted_buildings


def determine_building(shortname=None, id=None):
    """Determine building from shortname or id in this order.

    :param str shortname: The short name of the building
    :param int id: The id of the building

    :return: The unique building

    :raises: ValueError if none of both provided

    """
    if shortname:
        return Building.q.filter(Building.short_name == shortname).one()

    if id:
        return Building.q.get(id)

    raise ValueError("Either shortname or id must be given to identify the building!")
