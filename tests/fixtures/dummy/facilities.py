# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet

from .address import AddressData


class SiteData(DataSet):
    class dummy:
        name = "dummy"


class BuildingData(DataSet):
    class dummy_house1:
        site = SiteData.dummy
        street = "dummy"
        number = "01"
        short_name = "abc"

    class dummy_house2:
        site = SiteData.dummy
        street = "dummy"
        number = "02"
        short_name = "def"


class RoomData(DataSet):
    class dummy_room1:
        number = "1"
        level = 1
        inhabitable = True
        building = BuildingData.dummy_house1
        address = AddressData.dummy_address1

    class dummy_room2:
        number = "2"
        level = 2
        inhabitable = True
        building = BuildingData.dummy_house2
        address = AddressData.dummy_address2

    class dummy_room3:
        number = "2"
        level = 2
        inhabitable = True
        building = BuildingData.dummy_house1
        address = AddressData.dummy_address3

    class dummy_room4(dummy_room1):
        number = "2"
        address = AddressData.dummy_address4

    class dummy_room5(dummy_room1):
        number = "2"
        address = AddressData.dummy_address5

