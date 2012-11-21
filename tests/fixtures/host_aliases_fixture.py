__author__ = 'l3nkz'


from fixture import DataSet

from hosts_fixtures import UserNetDeviceData, UserHostData

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
        id = 1
        subnet = SubnetData.subnet_v4
        net_device = UserNetDeviceData.dummy_device
        address = "141.30.216.10"

    class ip_v6:
        id = 2
        subnet = SubnetData.subnet_v6
        net_device = UserNetDeviceData.dummy_device
        address = "2001:0db8:1234:0000:0000:0000:0000:0010"


class ARecordData(DataSet):
    class dummy_record1:
        address = IpData.ip_v4
        name = "www.dummy.de."
        host = UserHostData.dummy_host1

    class dummy_record2(dummy_record1):
        time_to_live = 1000

class AAAARecordData(DataSet):
    class dummy_record1:
        address = IpData.ip_v6
        name = "www.dummy.de."
        host = UserHostData.dummy_host1

    class dummy_record2(dummy_record1):
        time_to_live = 1000

class MXRecordData(DataSet):
    class dummy_record:
        domain = "dummy.de."
        server = "mail.dummy.de."
        priority = 10
        host = UserHostData.dummy_host1

class CNameRecordData(DataSet):
    class dummy_record:
        id = 100
        name = "dummy.net."
        alias_for = ARecordData.dummy_record1
        host = UserHostData.dummy_host1

    class dummy_record2:
        id = 101
        name = "dummy2.net."
        alias_for =  AAAARecordData.dummy_record1
        host = UserHostData.dummy_host1

class NSRecordData(DataSet):
    class dummy_record1:
        server = "server.dummy.de."
        domain = "dummy.de."
        host = UserHostData.dummy_host1

    class dummy_record2(dummy_record1):
        time_to_live = 1000


class SRVRecordData(DataSet):
    class dummy_record1:
        service = "_xmpp._tcp.dummy.de."
        priority = 10
        weight = 50
        port = 5050
        target = "xmpp.dummy.de."
        host = UserHostData.dummy_host1

    class dummy_record2(dummy_record1):
        time_to_live = 1000