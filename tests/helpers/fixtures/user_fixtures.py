# -*- coding: utf-8 -*-
__author__ = 'florian'

from datetime import datetime, timedelta
from fixture import DataSet

class VLanData(DataSet):
    class vlan_dummy1:
        name = "vlan_dom_1"
        tag = "1"

    class vlan_dummy2:
        name = "vlan_dom_2"
        tag = "2"

class DormitoryData(DataSet):
    class dummy_house1:
        number = "01"
        short_name = "abc"
        street = "dummy"
        vlans = [VLanData.vlan_dummy1]
    class dummy_house2:
        number = "02"
        short_name = "def"
        street = "dummy"
        vlans = [VLanData.vlan_dummy2]


class RoomData(DataSet):
    class dummy_room1:
        number = 1
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house1
    class dummy_room2:
        number = 2
        level = 2
        inhabitable = True
        dormitory = DormitoryData.dummy_house2
    class dummy_room3:
        number = 2
        level = 2
        inhabitable = True
        dormitory = DormitoryData.dummy_house1


class UserData(DataSet):
    class dummy_user1:
        id = 1
        login = "test"
        name = "John Doe"
        registration_date = datetime.now()
        room = RoomData.dummy_room1

    class dummy_user2:
        id = 2
        login = "admin"
        name = "Sebsatian fucking Schrader"
        registration_date = datetime.now()
        room = RoomData.dummy_room3


class TrafficGroupData(DataSet):
    class standard_traffic:
        name = "standard_traffic"
        traffic_limit = 7000


class PropertyGroupData(DataSet):
    class one_month_negative_balance:
        name = u"one_month_negative_balance"

    class verstoss:
        name = u"Verstoß"

    class negativ_konto:
        name = u"NegativKonto"

    class tmpAusgezogen:
        name = u"tmpAusgezogen"

    class benutzer:
        name = u"Benutzer"

    class kuerzlich_eingezogen:
        name = u"Kürzlich eingezogen"

    class dummy_group:
        name = u"dummy"


class PropertyData(DataSet):
    class internet:
        name = "internet"
        granted = True
        property_group = PropertyGroupData.benutzer

    class no_internet:
        name = "internet"
        granted = False
        property_group = PropertyGroupData.verstoss

    class away:
        name = "away"
        granted = True
        property_group = PropertyGroupData.tmpAusgezogen

    class dummy:
        name = "dummy"
        granted = True
        property_group = PropertyGroupData.dummy_group


class MembershipData(DataSet):
    class dummy_membership1:
        start_date = datetime.now() - timedelta(hours=1)
        end_date = datetime.now() + timedelta(hours=1)
        group = PropertyGroupData.dummy_group
        user = UserData.dummy_user2


class UserHostData(DataSet):
    class dummy_host1:
        hostname = "host1"
        user = UserData.dummy_user1
        room = RoomData.dummy_room1


class UserNetDeviceData(DataSet):
    class dummy_device:
        mac = "00:00:00:00:00:00"
        host = UserHostData.dummy_host1


class PatchPortData(DataSet):
    class dummy_patch_port1:
        room = RoomData.dummy_room1
        name = "A20"

    class dummy_patch_port2:
        room = RoomData.dummy_room2
        name = "B25"


class SubnetData(DataSet):
    class dummy_subnet1:
        address = "141.30.216.0/24"
        gateway = "141.30.216.1"
        ip_type = "4"
        vlans = [VLanData.vlan_dummy1]

    class dummy_subnet2:
        address = "141.30.203.0/24"
        gateway = "141.30.203.1"
        ip_type = "4"
        vlans = [VLanData.vlan_dummy2]


class IpData(DataSet):
    class dummy_ip1:
        address = "141.30.216.203"
        net_device = UserNetDeviceData.dummy_device
        subnet = SubnetData.dummy_subnet1


class SemesterData(DataSet):
    class dummy_semester1:
        name = "first semester"
        semester_fee = 2500
        registration_fee = 1500
        begin_date = datetime.now()
        end_date = datetime.now()


class FinanceAccountData(DataSet):
    class dummy_finance_account1:
        name = "finance account 1"
        type = "EXPENSE"

    class dummy_finance_account2:
        name = "finance account 2"
        type = "EXPENSE"

    class semester_fee:
        name = u"Semestergebühren first semester"
        semester = SemesterData.dummy_semester1
        type = "INCOME"
        tag = "regular_fee"

    class registration_fee:
        name = u"Anmeldegebühren first semester"
        semester = SemesterData.dummy_semester1
        type = "INCOME"
        tag = "registration_fee"

    class dummy_user_account2:
        name = 'dummy user 2 finance account'
        type = 'EQUITY'

UserData.dummy_user2.finance_account = FinanceAccountData.dummy_user_account2



