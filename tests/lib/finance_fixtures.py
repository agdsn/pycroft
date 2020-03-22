# coding=utf-8
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime, time, timedelta

from fixture import DataSet

from tests.fixtures.config import PropertyGroupData
from tests.fixtures.dummy.facilities import RoomData


today = datetime.utcnow().date()

class AccountData(DataSet):
    class bank_account:
        name = u"Bankkonto 3120219540"
        type = "BANK_ASSET"

    class membership_fee_account:
        name = u"Membership Fees"
        type = "REVENUE"

    class user_account:
        name = u"Dummy User"
        type = "USER_ASSET"

    class user_account_early:
        name = u"Dummy User Early"
        type = "USER_ASSET"

    class user_account_grace:
        name = u"Dummy User Grace"
        type = "USER_ASSET"

    class user_account_no_grace:
        name = u"Dummy User No Grace"
        type = "USER_ASSET"


class UserData(DataSet):
    class dummy_1:
        login = u"dummy1"
        name = u"Dummy Dummy"
        registered_at = datetime(2019, 1, 1)
        room = RoomData.dummy_room1
        address = room.address
        account = AccountData.user_account

    class dummy_2:
        login = u"dummy2"
        name = u"Dummy Dummy"
        registered_at = datetime(2019, 1, 1)
        room = RoomData.dummy_room1
        address = room.address
        account = AccountData.user_account_early

    class dummy_14:
        login = u"dummy14"
        name = u"Dummy Dummy"
        registered_at = datetime(2019, 1, 1)
        room = RoomData.dummy_room1
        address = room.address
        account = AccountData.user_account_grace

    class dummy_15:
        login = u"dummy15"
        name = u"Dummy Dummy"
        registered_at = datetime(2019, 1, 1)
        room = RoomData.dummy_room1
        address = room.address
        account = AccountData.user_account_no_grace

class MembershipData(DataSet):
    class member_1:
        begins_at = UserData.dummy_1.registered_at
        ends_at = UserData.dummy_1.registered_at
        user = UserData.dummy_1
        group = PropertyGroupData.member

    class member_2:
        begins_at = UserData.dummy_2.registered_at
        ends_at = UserData.dummy_2.registered_at
        user = UserData.dummy_2
        group = PropertyGroupData.member

    class member_14:
        begins_at = UserData.dummy_14.registered_at
        ends_at = None
        user = UserData.dummy_14
        group = PropertyGroupData.member

    class member_15:
        begins_at = UserData.dummy_15.registered_at
        ends_at = None
        user = UserData.dummy_15
        group = PropertyGroupData.member


class BankAccountData(DataSet):
    class dummy:
        name = u"Hauptkonto"
        bank = u"Ostsächsische Sparkasse Dresden"
        account_number = "3120219540"
        routing_number = "85050300"
        iban = "DE61850503003120219540"
        bic = "OSDDDE81XXX"
        fints_endpoint="https://example.org/fints"
        account = AccountData.bank_account
