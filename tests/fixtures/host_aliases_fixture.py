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
        address = IpData.ip_v4
        name = "www.dummy.de."
        host = HostData.dummy_host1

    class dummy_record2(dummy_record1):
        time_to_live = 1000

class AAAARecordData(DataSet):
    class dummy_record1:
        address = IpData.ip_v6
        name = "www.dummy.de."
        host = HostData.dummy_host1

    class dummy_record2(dummy_record1):
        time_to_live = 1000

class MXRecordData(DataSet):
    class dummy_record:
        domain = "dummy.de."
        server = "mail.dummy.de."
        priority = 10
        host = HostData.dummy_host1

class CNameRecordData(DataSet):
    class dummy_record:
        name = "dummy.net."
        alias_for = "dummy.de."
        host = HostData.dummy_host1

class NSRecordData(DataSet):
    class dummy_record1:
        server = "server.dummy.de."
        domain = "dummy.de."
        host = HostData.dummy_host1

    class dummy_record2(dummy_record1):
        time_to_live = 1000
