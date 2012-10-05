# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'florian'

from datetime import datetime
from fixture import DataSet

class VLanData(DataSet):
    class vlan_dummy1:
        name = "vlan_dom_2"
        tag = "1"

class DormitoryData(DataSet):
    class dummy_house1:
        number = "01"
        short_name = "abc"
        street = "dummy"
    class dummy_house2:
        number = "02"
        short_name = "def"
        street = "dummy"
        vlans = [VLanData.vlan_dummy1]


class RoomData(DataSet):
    class dummy_room1:
        number = 1
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house1
    class dummy_room2:
        number = 2
        level = 2
        inhabitable = True
        dormitory = DormitoryData.dummy_house2
    class dummy_room3:
        number = 2
        level = 2
        inhabitable = True
        dormitory = DormitoryData.dummy_house1


class UserData(DataSet):
    class dummy_user1:
        login = "test"
        name = "John Doe"
        registration_date = datetime.now()
        room = RoomData.dummy_room1

    class dummy_user2:
        login = "admin"
        name = "Sebsatian fucking Schrader"
        registration_date = datetime.now()
        room = RoomData.dummy_room3


class HostData(DataSet):
    class dummy_host1:
        hostname = "host1"
        user = UserData.dummy_user1
        room = RoomData.dummy_room1


class NetDeviceData(DataSet):
    class dummy_device:
        mac = "00:00:00:00:00:00"
        host = HostData.dummy_host1

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
    class dummy_subnet2:
        address = "141.30.203.0/24"
        gateway = "141.30.203.1"
        ip_type = "4"
        vlans = [VLanData.vlan_dummy1]

class IpData(DataSet):
    class dummy_ip1:
        address = "141.30.216.203"
        net_device = NetDeviceData.dummy_device
        subnet = SubnetData.dummy_subnet1
