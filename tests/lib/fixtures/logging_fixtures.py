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


class UserLogEntryData(DataSet):
    class dummy_log_entry1:
        id = 1
        message = "dummy_user_log_entry"
        timestamp = datetime.utcnow()
        author = UserData.dummy_user1
        user = UserData.dummy_user1


class RoomLogEntryData(DataSet):
    class dummy_log_entry1:
        id = 1
        message = "dummy_room_log_entry"
        timestamp = datetime.utcnow()
        author = UserData.dummy_user1
        room = RoomData.dummy_room1
