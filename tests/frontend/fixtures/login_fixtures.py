#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from fixture import DataSet
from pycroft.helpers.user import hash_password


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
        id = 1
        login = "test"
        name = "John Doe"
        passwd_hash = hash_password("password")
        registration_date = datetime.datetime.now()
        room = RoomData.dummy_room1


#class GroupData(DataSet):
#    class dummy_group1:
#        id = 1
#        name = "Finanzer"
#        discriminator = "propertygroup"


class PropertyGroupData(DataSet):
    class dummy_propertygroup1:
        id = 1
        name = "Finanzer"
        discriminator = "propertygroup"


class PropertyData(DataSet):
    class dummy_property1:
        name = "finance_show"
        granted = True
        property_group_id = 1


class MembershipData(DataSet):
    class dummy_membership1:
        start_date = datetime.datetime.now()
        end_date = None
        group_id = 1
        user_id = 1
