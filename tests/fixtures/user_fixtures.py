# -*- coding: utf-8 -*-
__author__ = 'florian'

from datetime import datetime
from fixture import DataSet

class DormitoryData(DataSet):
    class dummy_house1:
        number = "01"
        short_name = "abc"
        street = "dummy"
    class dummy_house2:
        number = "02"
        short_name = "def"
        street = "dummy"


class RoomData(DataSet):
    class dummy_room1:
        number = 1
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house1
    class dummy_room2:
        number = 2
        level = 2
        inhabitable = True
        dormitory = DormitoryData.dummy_house2


class UserData(DataSet):
    class dummy_user1:
        login = "test"
        name = "John Doe"
        registration_date = datetime.now()
        room = RoomData.dummy_room1


class HostData(DataSet):
    class dummy_host1:
        hostname = "host1"
        user = UserData.dummy_user1
        room = RoomData.dummy_room1


class NetDeviceData(DataSet):
    class dummy_device:
        mac = "00:00:00:00:00:00"
        host = HostData.dummy_host1

class PatchPortData(DataSet):
    class dummy_patch_port:
        room = RoomData.dummy_room2


