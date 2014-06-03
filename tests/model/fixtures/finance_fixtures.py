# coding=utf-8
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime
from fixture import DataSet

__author__ = 'shreyder'


class FinanceAccountData(DataSet):
    class Dummy1:
        name = u"Dummy1"
        type = "ASSET"

    class Dummy2:
        name = u"Dummy2"
        type = "ASSET"


class DormitoryData(DataSet):
    class Dummy:
        number = "01"
        short_name = "abc"
        street = "dummy"


class RoomData(DataSet):
    class Dummy:
        number = 1
        level = 1
        inhabitable = True
        dormitory = DormitoryData.Dummy


class UserData(DataSet):
    class Dummy:
        login = "dummy"
        name = u"Dummy"
        registration_date = datetime.now()
        room = RoomData.Dummy
