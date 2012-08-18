from datetime import datetime
from fixture import DataSet


class DormitoryData(DataSet):
    class dummy_house:
        number = "01"
        short_name = "abc"
        street = "dummy"


class VLanData(DataSet):
    class vlan1:
        name = "vlan1"
        tag = "1"
    class vlan2:
        name = "vlan2"
        tag = 2


class SubnetData(DataSet):
    class subnet1:
        address = "141.30.216.0/24"
        gateway = "141.30.216.1"
        dns_domain = "wh12.tu-dresden.de"
        reserved_addresses = 10
    class subnet2:
        address = "141.30.227.0/24"
        gateway = "141.30.227.1"
        dns_domain = "wh13.tu-dresden.de"
        reserved_addresses = 10


class RoomData(DataSet):
    class dummy_room:
        number = 1
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house


class UserData(DataSet):
    class dummy_user:
        login = "test"
        name = "John Doe"
        registration_date = datetime.now()
        room = RoomData.dummy_room


class HostData(DataSet):
    class dummy_host1:
        hostname = "host1"
        user = UserData.dummy_user
        room = RoomData.dummy_room
    class dummy_host2:
        hostname = "host2"
        user = UserData.dummy_user
        room = RoomData.dummy_room


class NetDeviceData(DataSet):
    class dummy_device:
        mac = "00:00:00:00:00:00"
        host = HostData.dummy_host1
