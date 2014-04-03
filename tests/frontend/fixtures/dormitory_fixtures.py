# -*- coding: utf-8 -*-
import datetime
from fixture import DataSet
from pycroft.helpers.user import hash_password

__author__ = 'Florian Österreich'


class DormitoryData(DataSet):
    class dummy_house1:
        id = 1
        number = "01"
        short_name = "abc"
        street = "dummy"


class RoomData(DataSet):
    class dummy_room1:
        id = 1
        number = 1
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house1

    class dummy_room2:
        id = 2
        number = 2
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house1


class UserData(DataSet):
    class dummy_user1:
        login = "test"
        name = "John Doe"
        passwd_hash = hash_password("password")
        registration_date = datetime.datetime.now()
        room = RoomData.dummy_room1
