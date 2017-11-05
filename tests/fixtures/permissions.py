# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime
from fixture import DataSet
from pycroft.helpers.user import hash_password
from tests.fixtures.dummy.facilities import RoomData
from tests.fixtures.dummy.finance import AccountData
from tests.fixtures.config import ConfigData


class BaseUser():
    """Data every user model needs"""
    name = "John Die"
    password = "password"
    passwd_hash = hash_password(password)
    registered_at = datetime.utcnow()
    room = RoomData.dummy_room1  # yes, they all live in the same room
    account = AccountData.dummy_asset


class UserData(DataSet):
    class user1_admin(BaseUser):
        # Normal admin
        login = "testadmin2"  # "admin" is blocked

    class user2_finance(BaseUser):
        # Admin with permission to view Finance
        login = "finanzer"

    class user3_user(BaseUser):
        # User without any usergroup
        login = "user"


class BaseMembership():
    """Base class with data every membership model needs"""
    begins_at = datetime.utcnow()
    ends_at = None


class BaseProperty():
    """Base class with data every property model needs"""
    granted = True


class PropertyGroupData(DataSet):
    # note that This is additional to the `PropertyGroupData` used by
    # the config.
    class property_group1_admin:
        name = "Admin"

    class property_group2_finance:
        name = "Finanzer"


class PropertyData(DataSet):
    class _AdminProperty(BaseProperty):
        # Property granted to admin
        property_group = PropertyGroupData.property_group1_admin

    class _FinanceProperty(BaseProperty):
        # Property granted to admin
        property_group = PropertyGroupData.property_group2_finance

    class property1_facilities_show(_AdminProperty):
        name = "facilities_show"

    class property2_facilities_change(_AdminProperty):
        name = "facilities_change"

    class property3_finance_show(_FinanceProperty):
        name = "finance_show"

    class property4_finance_change(_FinanceProperty):
        name = "finance_change"

    class property5_user_show(_AdminProperty):
        name = "user_show"

    class property6_user_change(_AdminProperty):
        name = "user_change"

    class property_groups_change(_AdminProperty):
        name = "groups_change"

    class property_groups_change_membership(_AdminProperty):
        name = "groups_change_membership"

    class property_groups_show(_AdminProperty):
        name = "groups_show"


class MembershipData(DataSet):
    class membership1_user1_admin(BaseMembership):
        group = PropertyGroupData.property_group1_admin
        user = UserData.user1_admin

    class membership2_user2_admin(BaseMembership):
        group = PropertyGroupData.property_group1_admin
        user = UserData.user2_finance

    class membership3_user2_finance(BaseMembership):
        group = PropertyGroupData.property_group2_finance
        user = UserData.user2_finance

    class user3_is_member(BaseMembership):
        group = ConfigData.config.member_group
        user = UserData.user3_user


# Provides example Users with adequate permissions plus a config for
# running frontend tests plus a user who is a member
datasets = {MembershipData, PropertyData, ConfigData}
