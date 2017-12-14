from datetime import datetime, timedelta

from fixture import DataSet

from tests.fixtures.dummy.finance import AccountData
from tests.fixtures.dummy.facilities import SiteData


class TrafficGroupData(DataSet):
    class default:
        name = "default"
        credit_limit = 7000
        credit_amount = 2000
        credit_interval = timedelta(days=1)

    class non_default:
        name = "non_default"
        credit_limit = 7000
        credit_amount = 2000
        credit_interval = timedelta(days=1)


class BaseHouse:
    site = SiteData.dummy
    street = "dummy"


class BuildingData(DataSet):
    class dummy_house1(BaseHouse):
        number = "01"
        short_name = "abc"
        default_traffic_group = TrafficGroupData.default

    # class dummy_house2(BaseHouse):
    #     number = "02"
    #     short_name = "def"
    #     default_traffic_group = TrafficGroupData.default

    class house_with_no_traffic_group(BaseHouse):
        number = "03"
        short_name = "geh"


class RoomData(DataSet):
    class dummy_room1:
        number = "1"
        level = 1
        inhabitable = True
        building = BuildingData.dummy_house1

    class dummy_room2:
        number = "1"
        level = 1
        inhabitable = True
        building = BuildingData.house_with_no_traffic_group


class UserData(DataSet):
    class dummy:
        login = "test"
        name = "John Doe"
        registered_at = datetime.utcnow()
        room = RoomData.dummy_room1
        account = AccountData.dummy_user1

    class dummy_no_default_group:
        login = "test2"
        name = "Wbua Qbr"
        registered_at = datetime.utcnow()
        room = RoomData.dummy_room2
        account = AccountData.dummy_user2


datasets = [
    TrafficGroupData,
    UserData,  # inherits all Rooms, buildings & sites
]
