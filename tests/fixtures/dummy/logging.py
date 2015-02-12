# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet

from tests.fixtures.dummy.dormitory import RoomData
from tests.fixtures.dummy.user import UserData


class UserLogEntryData(DataSet):
    class dummy_log_entry1:
        message = "dummy_user_log_entry"
        author = UserData.dummy
        user = UserData.dummy


class RoomLogEntryData(DataSet):
    class dummy_log_entry1:
        message = "dummy_room_log_entry"
        author = UserData.dummy
        room = RoomData.dummy_room1
