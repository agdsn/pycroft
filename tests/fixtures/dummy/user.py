# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime

from fixture import DataSet

from tests.fixtures.dummy.facilities import RoomData
from tests.fixtures.dummy.finance import FinanceAccountData


class UserData(DataSet):
    class dummy:
        login = "test"
        name = "John Doe"
        registered_at = datetime.utcnow()
        room = RoomData.dummy_room1
        finance_account = FinanceAccountData.dummy_user1

    class privileged:
        login = "admin"
        name = "BOfH"
        registered_at = datetime.utcnow()
        room = RoomData.dummy_room3
        finance_account = FinanceAccountData.dummy_user2
