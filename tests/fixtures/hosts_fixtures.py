# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime
from fixture import DataSet


class DormitoryData(DataSet):
    class dummy_house1:
        number = "01"
        short_name = "abc"
        street = "dummy"
    class dummy_house2:
        number = "02"
        short_name = "abcd"
        street = "dummy"


class VLanData(DataSet):
    class vlan1:
        name = "vlan1"
        tag = "1"
    class vlan2:
        name = "vlan2"
        tag = 2


class SubnetData(DataSet):
    class subnet1:
        address = "141.30.216.0/24"
        gateway = "141.30.216.1"
        dns_domain = "wh12.tu-dresden.de"
        reserved_addresses = 10
        ip_type = 4
    class subnet2:
        address = "141.30.227.0/24"
        gateway = "141.30.227.1"
        dns_domain = "wh13.tu-dresden.de"
        reserved_addresses = 10
        ip_type = 4


class RoomData(DataSet):
    class dummy_room:
        number = "1"
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house1
    class dummy_room2:
        number = "1"
        level = 2
        inhabitable = True
        dormitory = DormitoryData.dummy_house1
    class dummy_room3:
        number = "1"
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house2


class PatchPortData(DataSet):
    class dummy_port1:
        room = RoomData.dummy_room
    class dummy_port2:
        room = RoomData.dummy_room2
    class dummy_port3:
        room = RoomData.dummy_room3


class UserData(DataSet):
    class dummy_user:
        login = "test"
        name = "John Doe"
        registration_date = datetime.now()
        room = RoomData.dummy_room


class HostData(DataSet):
    class dummy_host1:
        id = 1
        user = UserData.dummy_user
        room = RoomData.dummy_room
    class dummy_host2:
        id = 2
        user = UserData.dummy_user
        room = RoomData.dummy_room


class NetDeviceData(DataSet):
    class dummy_device:
        mac = "00:00:00:00:00:00"
        host = HostData.dummy_host1


class IpData(DataSet):
    class dummy_ip:
        address = "141.30.216.2"
        net_device = NetDeviceData.dummy_device
        subnet = SubnetData.subnet1


class TrafficVolumeData(DataSet):
    class dummy_volume:
        size = 1000
        timestamp = datetime.now()
        type = "IN"
        ip = IpData.dummy_ip
