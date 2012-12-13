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

