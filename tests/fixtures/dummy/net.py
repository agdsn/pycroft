# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet
from tests.fixtures.dummy.facilities import VLANData


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
