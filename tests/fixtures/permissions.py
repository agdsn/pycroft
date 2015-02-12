# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime
from fixture import DataSet
from pycroft.helpers.user import hash_password
from tests.fixtures.dummy.facilities import RoomData
from tests.fixtures.dummy.finance import FinanceAccountData


class BaseUser():
    """Data every user model needs"""
    name = "John Die"
    password = "password"
    passwd_hash = hash_password(password)
    registered_at = datetime.utcnow()
    room = RoomData.dummy_room1  # yes, they all live in the same room
    finance_account = FinanceAccountData.dummy_asset


class UserData(DataSet):
    class user1_admin(BaseUser):
        # Normal admin
        login = "admin"

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
    class property_group1_admin:
        name = "Admin"

    class property_group2_finance:
        name = "Finanzer"


class PropertyData(DataSet):
    class property1_facilities_show(BaseProperty):
        name = "facilities_show"
        property_group = PropertyGroupData.property_group1_admin

    class property2_facilities_change(BaseProperty):
        name = "facilities_change"
        property_group = PropertyGroupData.property_group1_admin

    class property3_finance_show(BaseProperty):
        name = "finance_show"
        property_group = PropertyGroupData.property_group2_finance

    class property4_finance_change(BaseProperty):
        name = "finance_change"
        property_group = PropertyGroupData.property_group2_finance


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
