# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'

from fixture import DataSet
from datetime import datetime

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
        registered_at = datetime.utcnow()
        room = RoomData.dummy_room1


class UserHostData(DataSet):
    class dummy_host1:
        id = 1
        user = UserData.dummy_user1
        room = RoomData.dummy_room1


class UserNetDeviceData(DataSet):
    class dummy_device1:
        mac = "00:00:00:00:00:00"
        host = UserHostData.dummy_host1

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
        net_device = UserNetDeviceData.dummy_device1
        address = "141.30.216.10"

    class ip_v6:
        id = 2
        subnet = SubnetData.subnet_v6
        net_device = UserNetDeviceData.dummy_device1
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


class CNAMERecordData(DataSet):
    class dummy_record:
        id = 100
        name = "dummy.net."
        record_for = ARecordData.dummy_record1
        host = UserHostData.dummy_host1

    class dummy_record2:
        id = 101
        name = "dummy2.net."
        record_for = AAAARecordData.dummy_record1
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
