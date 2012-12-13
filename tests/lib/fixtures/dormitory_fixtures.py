# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'

from tests import DataSet

class DormitoryData(DataSet):
    class dummy_dormitory1:
        id = 1
        number = "100"
        short_name = "wu100"
        street = "wundstrasse"

class RoomData(DataSet):
    class dummy_room1:
        id = 1
        number = "101"
        level = 0
        inhabitable = True
        dormitory = DormitoryData.dummy_dormitory1

