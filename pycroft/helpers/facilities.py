# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.helpers.facilities
~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
import re
import typing as t

from pycroft.model.facilities import Building


def sort_buildings(buildings: t.Iterable[Building]) -> list[Building]:
    def make_sort_key(building: Building) -> tuple[str, str | tuple[int, str]]:
        s = re.split(r'(\d+)([a-zA-Z]?)', building.number)
        if len(s) != 4: return building.street, building.number #split unsuccessful
        return building.street, (int(s[1]), s[2].lower())

    return sorted(buildings, key=make_sort_key)


def determine_building(shortname: str | None = None, id: int | None = None) -> Building:
    """Determine building from shortname or id in this order.

    :param shortname: The short name of the building
    :param id: The id of the building

    :return: The unique building
    """
    if shortname:
        return t.cast(Building, Building.q.filter(Building.short_name == shortname).one())
    if id:
        return Building.get(id)
    raise ValueError("Either shortname or id must be given to identify the building!")
