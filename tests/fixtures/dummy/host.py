# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet
from ipaddr import IPv4Address, IPv6Address

from tests.fixtures.dummy.facilities import RoomData
from tests.fixtures.dummy.net import SubnetData
from tests.fixtures.dummy.user import UserData


class UserHostData(DataSet):
    class dummy:
        owner = UserData.dummy
        room = RoomData.dummy_room1


class UserInterfaceData(DataSet):
    class dummy:
        mac = "00:00:00:00:00:00"
        host = UserHostData.dummy


class PatchPortData(DataSet):
    class dummy_patch_port1:
        room = RoomData.dummy_room1
        name = "A20"

    class dummy_patch_port2:
        room = RoomData.dummy_room2
        name = "B25"


class SwitchData(DataSet):
    class dummy:
        name = "dummy_switch"
        user = UserData.privileged
        room = RoomData.dummy_room1
        management_ip = "141.30.216.15"


class SwitchInterfaceData(DataSet):
    class dummy:
        mac = "00:00:00:00:00:02"
        host = SwitchData.dummy


class SwitchPortData(DataSet):
    class dummy_switch_port1:
        name = "name"
        switch = SwitchData.dummy


class ServerHostData(DataSet):
    class dummy:
        user = UserData.dummy
        room = RoomData.dummy_room1


class ServerInterfaceData(DataSet):
    class dummy:
        mac = "00:00:00:00:00:03"
        host = ServerHostData.dummy
        switch_port = SwitchPortData.dummy_switch_port1


class IPData(DataSet):
    class dummy_user_ipv4:
        address = IPv4Address("192.168.0.42")
        interface = UserInterfaceData.dummy
        subnet = SubnetData.user_ipv4

    class dummy_user_ipv6:
        subnet = SubnetData.user_ipv6
        interface = UserInterfaceData.dummy
        address = IPv6Address("2001:db8::42")

    class dummy_switch_ip:
        address = IPv4Address("192.168.0.1")
        interface = SwitchInterfaceData.dummy
        subnet = SubnetData.user_ipv4

    class dummy_server_ip:
        address = IPv4Address("192.168.0.2")
        interface = ServerInterfaceData.dummy
        subnet = SubnetData.user_ipv4
