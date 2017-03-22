from datetime import datetime

from fixture import DataSet

from tests.fixtures.dummy.facilities import RoomData
from tests.fixtures.dummy.finance import AccountData


class UnixAccountData(DataSet):
    class explicit_ids:
        home_directory = '/home/explicit'
        uid = 1042
        gid = 27  # if you know what I mean
    class dummy_account_1:
        home_directory = '/home/dummy1'

    class dummy_account_2:
        home_directory = '/home/dummy2'

    class dummy_account_3:
        home_directory = '/home/dummy3'

    class dummy_account_4:
        home_directory = '/home/dummy4'

    class dummy_account_5:
        home_directory = '/home/dummy5'


class UserData(DataSet):
    """A simple dataset providing a user with and a user without a unix account"""
    class dummy:
        login = "test"
        name = "John Doe"
        registered_at = datetime.utcnow()
        room = RoomData.dummy_room1
        account = AccountData.dummy_user1

    class withldap(dummy):
        login = "ldap"
        # name = "Ldap User"
        registered_at = datetime.utcnow()
        room = RoomData.dummy_room2
        account = AccountData.dummy_user2
        unix_account = UnixAccountData.dummy_account_1
