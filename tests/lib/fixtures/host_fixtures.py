# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'

from datetime import datetime
from tests import DataSet

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


class UserData(DataSet):
    class dummy_user1:
        login = "test"
        name = "John Doe"
        registration_date = datetime.utcnow()
        room = RoomData.dummy_room1


class UserHostData(DataSet):
    class dummy_user_host1:
        user = UserData.dummy_user1
        room = RoomData.dummy_room1


class ServerHostData(DataSet):
    class dummy_server_host1:
        user = UserData.dummy_user1
        room = RoomData.dummy_room1


class UserNetDeviceData(DataSet):
    class dummy_user_device1:
        mac = "00:00:00:00:00:01"
        host = UserHostData.dummy_user_host1


class SubnetData(DataSet):
    class dummy_subnet1:
        address = "141.30.216.0/24"
        gateway = "141.30.216.1"
        dns_domain = "wh12.tu-dresden.de"
        reserved_addresses = 10
        ip_type = 4


class SwitchData(DataSet):
    class dummy_switch1:
        name = "dummy_switch"
        user = UserData.dummy_user1
        room = RoomData.dummy_room1
        management_ip = "141.30.216.15"


class SwitchNetDeviceData(DataSet):
    class dummy_switch_device1:
        mac = "00:00:00:00:00:02"
        host = SwitchData.dummy_switch1


class SwitchPortData(DataSet):
    class dummy_switch_port1:
        name = "name"
        switch = SwitchData.dummy_switch1


class ServerNetDeviceData(DataSet):
    class dummy_server_device1:
        mac = "00:00:00:00:00:03"
        host = ServerHostData.dummy_server_host1
        switch_port = SwitchPortData.dummy_switch_port1


class IpData(DataSet):
    class dummy_ip1:
        address = "141.30.216.15"
        net_device = SwitchNetDeviceData.dummy_switch_device1
        subnet = SubnetData.dummy_subnet1
