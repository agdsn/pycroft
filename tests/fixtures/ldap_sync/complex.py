from datetime import datetime, timedelta

from fixture import DataSet

from tests.fixtures.dummy.unixaccount import UnixAccountData
from tests.fixtures.dummy.facilities import RoomData
from tests.fixtures.dummy.finance import AccountData

class UserData(DataSet):
    """Some fixtures interesting for the ldap syncer.

    In order for the users to obtain the correct `mail` attributes and
    so on, the :py:cls:`MembershipData` has to be loaded as well.
    """
    class dummy:
        """A Boring dummy User

        He lives in dummy_room1 and misses a ``unix_account`` and the
        ``mail`` property.
        """
        login = "dummy"
        name = "Black Hat"
        registered_at = datetime.utcnow()
        room = RoomData.dummy_room1
        account = AccountData.dummy_user1

    class moved_out_user1(dummy):
        """unix_account, but no 'mail'"""
        login = "moved-out"
        room = RoomData.dummy_room2
        account = AccountData.dummy_user2
        unix_account = UnixAccountData.dummy_account_1

    class active_user1(dummy):
        """unix_account and 'mail'"""
        login = "active1"
        room = RoomData.dummy_room3
        account = AccountData.dummy_user3
        unix_account = UnixAccountData.dummy_account_2
        email = 'ich-liebe-die@agdsn.de'

    class active_user2(dummy):
        """unix_account and 'mail'"""
        login = "active2"
        room = RoomData.dummy_room4
        account = AccountData.dummy_user4
        unix_account = UnixAccountData.dummy_account_3

    class inconsistent_user1(dummy):
        """'mail' but no unix_account"""
        login = 'inconsistent'
        room = RoomData.dummy_room5
        account = AccountData.dummy_user5


class PropertyGroupData(DataSet):
    class dummy:
        name = "dummy_property_group"

    class another_dummy:
        name = "another_dummy_property_group"


class PropertyData(DataSet):
    class mail:
        property_group = PropertyGroupData.dummy
        name = "mail"
        granted = True

    class ldap_login_enabled:
        """Necessary to not add `pwdAccountLockedTime` during tests"""
        property_group = PropertyGroupData.dummy
        name = "ldap_login_enabled"
        granted = True


class MembershipData(DataSet):
    class active1_membership:
        begins_at = datetime.utcnow() - timedelta(1)
        ends_at = datetime.utcnow() + timedelta(1)
        group = PropertyGroupData.dummy
        user = UserData.active_user1

    class active2_membership(active1_membership):
        user = UserData.active_user2

    class inconsistent_membership(active1_membership):
        user = UserData.inconsistent_user1

    class dummy_membership:
        begins_at = datetime.utcnow() - timedelta(1)
        ends_at = datetime.utcnow() + timedelta(1)
        group = PropertyGroupData.another_dummy
        user = UserData.dummy

# This is a complex fixture providing many users, of which some have a
# ``unix_account``, and some have the attribute ``mail``.  Every possible
# combination is covered.
datasets = frozenset([PropertyData, MembershipData])
