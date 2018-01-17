# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet
from ipaddr import IPv4Address, IPv6Address

from tests.fixtures.dummy.facilities import RoomData
from tests.fixtures.dummy.net import SubnetData
from tests.fixtures.dummy.user import UserData


class HostData(DataSet):
    class dummy:
        owner = UserData.dummy
        room = RoomData.dummy_room1

    class dummy_switch:
        owner = UserData.privileged
        room = RoomData.dummy_room1

class InterfaceData(DataSet):
    class dummy:
        mac = "00:00:00:00:00:00"
        host = HostData.dummy


class SwitchData(DataSet):
    class dummy:
        host = HostData.dummy_switch
        name = "dummy_switch"
        management_ip = "141.30.216.15"


class SwitchPortData(DataSet):
    class dummy_port1:
        name = "A20"
        mac = "00:00:00:00:00:14"
        switch = SwitchData.dummy
        subnets = [SubnetData.dummy_subnet3]

    class dummy_port2:
        name = "A21"
        mac = "00:00:00:00:00:15"
        switch = SwitchData.dummy
        subnets = [SubnetData.dummy_subnet4]

    class dummy_port3:
        name = "A23"
        mac = "00:00:00:00:00:16"
        switch = SwitchData.dummy

    class dummy_port4(dummy_port3):
        name = "A24"
        mac = "00:00:00:00:00:fe"
        subnets = [SubnetData.dummy_subnet3, SubnetData.dummy_subnet4]

    class vlan:
        name = "VLAN-42"
        mac = "00:00:00:00:00:17"
        switch = SwitchData.dummy


class SwitchPatchPortData(DataSet):
    class dummy_patch_port1:
        room = RoomData.dummy_room1
        name = "D1"
        switch_port = SwitchPortData.dummy_port1

    class dummy_patch_port2:
        room = RoomData.dummy_room2
        name = "D2"
        switch_port = SwitchPortData.dummy_port2

    class dummy_patch_port3:
        room = RoomData.dummy_room3
        name = "D3"
        switch_port = SwitchPortData.dummy_port3


class IPData(DataSet):
    class dummy_user_ipv4:
        address = IPv4Address("192.168.0.42")
        interface = InterfaceData.dummy
        subnet = SubnetData.user_ipv4

    class dummy_user_ipv6:
        subnet = SubnetData.user_ipv6
        interface = InterfaceData.dummy
        address = IPv6Address("2001:db8::42")
