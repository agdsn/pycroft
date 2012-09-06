# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'


from fixture import DataSet

from hosts_fixtures import NetDeviceData, HostData

# The following two fixtures are needed for generating A and
# AAAA DNSRecords


# Subnet fixtures
class SubnetData(DataSet):
    class subnet_v4:
        address = "141.30.216.0/24"
        gateway = "141.30.216.1"
        dns_domain = "wh12.tu-dresden.de"
        reserved_addresses = 10
        ip_type = "4"

    class subnet_v6:
        address = "2001:0db8:1234::/48"
        gateway = "2001:0db8:1234:0000:0000:0000:0000:0001"
        dns_domain = "wh13.tu-dresden.de"
        reserved_addresses = 10
        ip_type = "6"

# Ip fixtures
class IpData(DataSet):
    class ip_v4:
        subnet = SubnetData.subnet_v4
        net_device = NetDeviceData.dummy_device
        address = "141.30.216.10"

    class ip_v6:
        subnet = SubnetData.subnet_v6
        net_device = NetDeviceData.dummy_device
        address = "2001:0db8:1234:0000:0000:0000:0000:0010"


class ARecordData(DataSet):
    class dummy_record1:
        ip = IpData.ip_v4
        ip_id = 0
        content = "www.dummy.de."
        host_id = 0

    class dummy_record2(dummy_record1):
        time_to_live = 1000

class AAAARecordData(DataSet):
    class dummy_record1:
        ip = IpData.ip_v6
        ip_id = 1
        content = "www.dummy.de."
        host_id = 0

    class dummy_record2(dummy_record1):
        time_to_live = 1000

class MXRecordData(DataSet):
    class dummy_record:
        domain = "dummy.de."
        content = "mail.dummy.de."
        priority = "10"

class CNameRecordData(DataSet):
    class dummy_record:
        content = "dummy.net."
        alias_for = "dummy.de."

class NSRecordData(DataSet):
    class dummy_record1:
        content = "server.dummy.de."
        domain = "dummy.de."

    class dummy_record2(dummy_record1):
        time_to_live = "1000"
