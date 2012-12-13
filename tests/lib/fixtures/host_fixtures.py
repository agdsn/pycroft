# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'

from datetime import datetime
from tests import DataSet

class DormitoryData(DataSet):
    class dummy_house1:
        number = "01"
        short_name = "abc"
        street = "dummy"


class RoomData(DataSet):
    class dummy_room1:
        number = "1"
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house1


class UserData(DataSet):
    class dummy_user1:
        id=1
        login = "test"
        name = "John Doe"
        registration_date = datetime.now()
        room = RoomData.dummy_room1


class UserHostData(DataSet):
    class dummy_host1:
        id = 1
        user = UserData.dummy_user1
        room = RoomData.dummy_room1


class UserNetDeviceData(DataSet):
    class dummy_device1:
        id=1
        mac = "00:00:00:00:00:00"
        host = UserHostData.dummy_host1
