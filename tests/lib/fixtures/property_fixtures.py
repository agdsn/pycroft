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


class PropertyGroupData(DataSet):
    class dummy_property_group1:
        id = 1
        name = "dummy_property_group"
    class dummy_property_group2:
        id = 3
        name = "empty_property_group"


class TrafficGroupData(DataSet):
    class dummy_traffic_group1:
        id = 2
        name = "dummy_traffic_group"
        traffic_limit = 100000000


class MembershipData(DataSet):
    class dummy_membership1:
        id = 1
        start_data = datetime.utcnow()
        end_data = datetime.utcnow()
        group = PropertyGroupData.dummy_property_group1
        user = UserData.dummy_user1


class PropertyData(DataSet):
    class dummy_property1:
        id = 1
        granted = True
        name = "dummy_property"
        property_group = PropertyGroupData.dummy_property_group1
