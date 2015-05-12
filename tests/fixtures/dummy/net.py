# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet
from ipaddr import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from tests.fixtures.dummy.facilities import DormitoryData
from tests.fixtures.dummy.dns_zones import DNSZoneData


class VLANData(DataSet):
    class vlan_dummy1:
        name = "vlan_dom_1"
        vid = "1"

    class vlan_dummy2:
        name = "vlan_dom_2"
        vid = "2"


class SubnetData(DataSet):
    class user_ipv4:
        address = IPv4Network("192.168.0.0/24")
        gateway = IPv4Address("192.168.0.1")
        primary_dns_zone = DNSZoneData.example_com
        reverse_dns_zone = DNSZoneData.reverse_192_168_0
        reserved_addresses = 10
        vlan = VLANData.vlan_dummy1

    class user_ipv6:
        address = IPv6Network("2001:db8:0::/48")
        gateway = IPv6Address("2001:db8:0::1")
        primary_dns_zone = DNSZoneData.example_com
        reverse_dns_zone = DNSZoneData.reverse_2001_cdba_0000
        reserved_addresses = 10
        vlan = VLANData.vlan_dummy1

    class dummy_subnet2:
        address = IPv4Network("192.168.1.0/24")
        primary_dns_zone = DNSZoneData.example_com
        reverse_dns_zone = DNSZoneData.reverse_192_168_1
        reserved_addresses = 10
        vlan = VLANData.vlan_dummy2
