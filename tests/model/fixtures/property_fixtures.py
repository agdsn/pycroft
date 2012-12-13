from datetime import datetime
from tests import DataSet

class DormitoryData(DataSet):
    class dummy_house:
        number = "01"
        short_name = "abc"
        street = "dummy"


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


class PropertyGroupData(DataSet):
    class group1:
        name = "group1"

    class group2:
        name = "group2"


class TrafficGroupData(DataSet):
    class group1:
        name = "trafficgroup1"
        traffic_limit = 1000

    class group2:
        name = "trafficgroup2"
        traffic_limit = 2000


class PropertyData(DataSet):
    class prop_test1:
        name = "test1"
        property_group = PropertyGroupData.group1

    class prop_test1_1(prop_test1):
        property_group = PropertyGroupData.group2

    class prop_test2:
        name = "test2"
        property_group = PropertyGroupData.group2