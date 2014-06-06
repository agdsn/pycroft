# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from tests import DataSet
from datetime import datetime


class DormitoryData(DataSet):
    class dummy_house1:
        number = "01"
        short_name = "abc"
        street = "dummy"


class RoomData(DataSet):
    class dummy_room1:
        id = 1
        number = "1"
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house1


class UserData(DataSet):
    class dummy_user1:
        id = 1
        login = "test"
        name = "John Doe"
        registration_date = datetime.utcnow()
        room = RoomData.dummy_room1


class SwitchData(DataSet):
    class dummy_switch1:
        id = 10
        name = "dummy_switch"
        user = UserData.dummy_user1
        room = RoomData.dummy_room1
        management_ip = "141.30.216.15"


class DestinationPortData(DataSet):
    class dummy_destination_port1:
        id = 1
        name = "D100"


class PatchPortData(DataSet):
    class dummy_patch_port1:
        id = 2
        name = "P100"
        destination_port_id = DestinationPortData.dummy_destination_port1.id
        room = RoomData.dummy_room1


class PhonePortData(DataSet):
    class dummy_phone_port:
        id = 3
        name = "P200"


class SwitchPortData(DataSet):
    class dummy_switch_port:
        id = 4
        name = "S100"
        switch = SwitchData.dummy_switch1
