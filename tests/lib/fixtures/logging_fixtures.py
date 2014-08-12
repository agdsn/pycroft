# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime
from fixture import DataSet


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


class FinanceAccountData(DataSet):
    class finance_account:
        name = ''
        type = 'ASSET'


class UserData(DataSet):
    class dummy_user1:
        login = "test"
        name = "John Doe"
        registered_at = datetime.utcnow()
        room = RoomData.dummy_room1
        finance_account = FinanceAccountData.finance_account


class UserLogEntryData(DataSet):
    class dummy_log_entry1:
        message = "dummy_user_log_entry"
        timestamp = datetime.utcnow()
        author = UserData.dummy_user1
        user = UserData.dummy_user1


class RoomLogEntryData(DataSet):
    class dummy_log_entry1:
        message = "dummy_room_log_entry"
        timestamp = datetime.utcnow()
        author = UserData.dummy_user1
        room = RoomData.dummy_room1
