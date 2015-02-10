# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'florian'

from datetime import datetime, timedelta
from fixture import DataSet

class VLANData(DataSet):
    class vlan_dummy1:
        name = "vlan_dom_1"
        tag = "1"

    class vlan_dummy2:
        name = "vlan_dom_2"
        tag = "2"

class DormitoryData(DataSet):
    class dummy_house1:
        number = "01"
        short_name = "abc"
        street = "dummy"
        vlans = [VLANData.vlan_dummy1]
    class dummy_house2:
        number = "02"
        short_name = "def"
        street = "dummy"
        vlans = [VLANData.vlan_dummy2]


class RoomData(DataSet):
    class dummy_room1:
        number = "1"
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house1
    class dummy_room2:
        number = "2"
        level = 2
        inhabitable = True
        dormitory = DormitoryData.dummy_house2
    class dummy_room3:
        number = "2"
        level = 2
        inhabitable = True
        dormitory = DormitoryData.dummy_house1


today = datetime.utcnow().date()


class SemesterData(DataSet):
    class dummy_semester1:
        name = "first semester"
        registration_fee = 2500
        regular_semester_fee = 1500
        reduced_semester_fee = 450
        late_fee = 250
        grace_period = timedelta(62)
        reduced_semester_fee_threshold = timedelta(62)
        payment_deadline = timedelta(31)
        allowed_overdraft = 500
        begins_on = today
        ends_on = today + timedelta(days=180)


class FinanceAccountData(DataSet):
    class dummy_finance_account1:
        name = "finance account 1"
        type = "EXPENSE"

    class dummy_finance_account2:
        name = "finance account 2"
        type = "EXPENSE"

    class user_account:
        name = ''
        type = 'ASSET'


class UserData(DataSet):
    class dummy_user1:
        login = "test"
        name = "John Doe"
        registered_at = datetime.utcnow()
        room = RoomData.dummy_room1
        finance_account = FinanceAccountData.user_account

    class dummy_user2:
        login = "admin"
        name = "Sebsatian fucking Schrader"
        registered_at = datetime.utcnow()
        room = RoomData.dummy_room3
        finance_account = FinanceAccountData.user_account


class TrafficGroupData(DataSet):
    class standard_traffic:
        name = "standard_traffic"
        traffic_limit = 7000


class UserHostData(DataSet):
    class dummy_host1:
        hostname = "host1"
        user = UserData.dummy_user1
        room = RoomData.dummy_room1


class UserNetDeviceData(DataSet):
    class dummy_device:
        mac = "00:00:00:00:00:00"
        host = UserHostData.dummy_host1


class PatchPortData(DataSet):
    class dummy_patch_port1:
        room = RoomData.dummy_room1
        name = "A20"

    class dummy_patch_port2:
        room = RoomData.dummy_room2
        name = "B25"


class SubnetData(DataSet):
    class dummy_subnet1:
        address = "141.30.216.0/24"
        gateway = "141.30.216.1"
        ip_type = "4"
        vlans = [VLANData.vlan_dummy1]

    class dummy_subnet2:
        address = "141.30.203.0/24"
        gateway = "141.30.203.1"
        ip_type = "4"
        vlans = [VLANData.vlan_dummy2]


class IpData(DataSet):
    class dummy_ip1:
        address = "141.30.216.203"
        net_device = UserNetDeviceData.dummy_device
        subnet = SubnetData.dummy_subnet1
