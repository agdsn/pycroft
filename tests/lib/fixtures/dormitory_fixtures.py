__author__ = 'l3nkz'

from tests import DataSet

class DormitoryData(DataSet):
    class dummy_dormitory1:
        id = 1
        number = "100"
        short_name = "wu100"
        street = "wundstrasse"


class RoomData(DataSet):
    class dummy_room1:
        id = 1
        number = "101"
        level = 0
        inhabitable = True
        dormitory = DormitoryData.dummy_dormitory1


class SubnetData(DataSet):
    class dummy_subnet1:
        id = 1
        address = "192.168.1.1"
        gateway = "192.168.1.1"
        dns_domain = "dummy_domain"
        reserved_addresses = 0
        ip_type = "4"


class VLANData(DataSet):
    class dummy_vlan1:
        id = 1
        name = "dummy_vlan1"
        tag = 42