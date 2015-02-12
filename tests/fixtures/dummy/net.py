# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet

from tests.fixtures.dummy.facilities import VLANData, RoomData
from tests.fixtures.dummy.user import UserData


class SubnetData(DataSet):
    class user_ipv4:
        address = "141.30.216.0/24"
        gateway = "141.30.216.1"
        dns_domain = "wh12.tu-dresden.de"
        reserved_addresses = 10
        ip_type = "4"
        vlans = [VLANData.vlan_dummy1]

    class user_ipv6:
        address = "2001:0db8:1234::/48"
        gateway = "2001:0db8:1234::1"
        dns_domain = "wh12.tu-dresden.de"
        reserved_addresses = 10
        ip_type = "6"
        vlans = [VLANData.vlan_dummy1]

    class dummy_subnet2:
        address = "141.30.203.0/24"
        gateway = "141.30.203.1"
        dns_domain = "wh13.tu-dresden.de"
        reserved_addresses = 10
        ip_type = "4"
        vlans = [VLANData.vlan_dummy2]


class UserHostData(DataSet):
    class dummy_host1:
        user = UserData.dummy
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


class SwitchData(DataSet):
    class dummy_switch1:
        name = "dummy_switch"
        user = UserData.privileged
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


class ServerHostData(DataSet):
    class dummy_server_host1:
        user = UserData.dummy
        room = RoomData.dummy_room1


class ServerNetDeviceData(DataSet):
    class dummy_server_device1:
        mac = "00:00:00:00:00:03"
        host = ServerHostData.dummy_server_host1
        switch_port = SwitchPortData.dummy_switch_port1


class IpData(DataSet):
    class dummy_user_ipv4:
        address = "141.30.216.203"
        net_device = UserNetDeviceData.dummy_device
        subnet = SubnetData.user_ipv4

    class dummy_user_ipv6:
        subnet = SubnetData.user_ipv6
        net_device = UserNetDeviceData.dummy_device
        address = "2001:0db8:1234:0000:0000:0000:0000:0010"

    class dummy_switch_ip:
        address = "141.30.216.1"
        net_device = SwitchNetDeviceData.dummy_switch_device1
        subnet = SubnetData.user_ipv4

    class dummy_server_ip:
        address = "141.30.216.2"
        net_device = ServerNetDeviceData.dummy_server_device1
        subnet = SubnetData.user_ipv4
