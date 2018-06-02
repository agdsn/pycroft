# coding=utf-8
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime, time, timedelta

from fixture import DataSet

from tests.fixtures.config import PropertyGroupData
from tests.fixtures.dummy.facilities import RoomData


today = datetime.utcnow().date()


class MembershipFeeData(DataSet):
    class with_registration_fee:
        name = u"previous month"
        registration_fee = 5.00
        regular_fee = 5.00
        reduced_fee = 1.00
        late_fee = 2.50
        grace_period = timedelta(14)
        reduced_fee_threshold = timedelta(10)
        payment_deadline = timedelta(14)
        payment_deadline_final = timedelta(62)
        not_allowed_overdraft_late_fee = 2.00
        begins_on = today - timedelta(days=61)
        ends_on = today - timedelta(days=31)

    class without_registration_fee:
        name = u"current month"
        registration_fee = 0.00
        regular_fee = 5.00
        reduced_fee = 1.00
        late_fee = 2.50
        grace_period = timedelta(14)
        reduced_fee_threshold = timedelta(10)
        payment_deadline = timedelta(14)
        payment_deadline_final = timedelta(62)
        not_allowed_overdraft_late_fee = 2.00
        begins_on = today - timedelta(days=30)
        ends_on = today

    class first_fee:
        name = u"first month"
        registration_fee = 0.00
        regular_fee = 5.00
        reduced_fee = 0.00
        late_fee = 0.00
        grace_period = timedelta(14)
        reduced_fee_threshold = timedelta(32)
        payment_deadline = timedelta(14)
        payment_deadline_final = timedelta(62)
        not_allowed_overdraft_late_fee = 0.00
        begins_on = today - timedelta(days=92)
        ends_on = today - timedelta(days=62)


class AccountData(DataSet):
    class bank_account:
        name = u"Bankkonto 3120219540"
        type = "BANK_ASSET"

    class registration_fee_account:
        name = u"Registration Fees"
        type = "REVENUE"

    class membership_fee_account:
        name = u"Membership Fees"
        type = "REVENUE"

    class late_fee_account:
        name = u"Late Fees"
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
    class dummy:
        login = u"dummy"
        name = u"Dummy Dummy"
        registered_at = datetime.combine(MembershipFeeData.with_registration_fee.begins_on + timedelta(days=12), time.min)
        room = RoomData.dummy_room1
        account = AccountData.user_account

    class dummy_grace:
        login = u"dummy_grace"
        name = u"Dummy Dummy"
        registered_at = datetime.combine(MembershipFeeData.without_registration_fee.begins_on + timedelta(days=20), time.min)
        room = RoomData.dummy_room1
        account = AccountData.user_account_grace

    class dummy_no_grace:
        login = u"dummy_no_grace"
        name = u"Dummy Dummy"
        registered_at = datetime.combine(MembershipFeeData.without_registration_fee.begins_on - timedelta(days=10), time.min)
        room = RoomData.dummy_room1
        account = AccountData.user_account_no_grace

    class dummy_early:
        login = u"dummy_early"
        name = u"Dummy Dummy"
        registered_at = datetime.combine(MembershipFeeData.first_fee.begins_on + timedelta(days=12), time.min)
        room = RoomData.dummy_room1
        account = AccountData.user_account_early


class MembershipData(DataSet):
    class member:
        begins_at = UserData.dummy.registered_at
        ends_at = None
        user = UserData.dummy
        group = PropertyGroupData.member

    class member_early:
        begins_at = UserData.dummy_early.registered_at
        ends_at = None
        user = UserData.dummy_early
        group = PropertyGroupData.member

    class member_grace:
        begins_at = UserData.dummy_grace.registered_at
        ends_at = None
        user = UserData.dummy_grace
        group = PropertyGroupData.member

    class member_no_grace:
        begins_at = UserData.dummy_no_grace.registered_at
        ends_at = UserData.dummy_no_grace.registered_at + timedelta(30)
        user = UserData.dummy_no_grace
        group = PropertyGroupData.member


class TransactionData(DataSet):
    class claim1:
        description = "Claim 1"
        valid_on = MembershipFeeData.with_registration_fee.begins_on + timedelta(days=31)

    class late_fee_for_claim1:
        description = "Late fee for Claim 1"
        valid_on = MembershipFeeData.with_registration_fee.begins_on + timedelta(days=63)

    class claim2:
        description = "Claim 2"
        valid_on = MembershipFeeData.with_registration_fee.begins_on + timedelta(days=81)

    class payment:
        description = "Payment of Claim 1"
        valid_on = MembershipFeeData.with_registration_fee.begins_on + timedelta(days=64)


class SplitData(DataSet):
    class claim1_credit:
        transaction = TransactionData.claim1
        account = AccountData.user_account
        amount = 50.00

    class claim1_debit:
        transaction = TransactionData.claim1
        account = AccountData.membership_fee_account
        amount = -50.00

    class late_fee1_credit:
        transaction = TransactionData.late_fee_for_claim1
        account = AccountData.user_account
        amount = 25.00

    class late_fee2_credit:
        transaction = TransactionData.late_fee_for_claim1
        account = AccountData.late_fee_account
        amount = -25.00

    class claim2_credit:
        transaction = TransactionData.claim2
        account = AccountData.user_account
        amount = 50.00

    class claim2_debit:
        transaction = TransactionData.claim2
        account = AccountData.membership_fee_account
        amount = -50.00

    class payment_credit:
        transaction = TransactionData.payment
        account = AccountData.bank_account
        amount = 50.00

    class payment_debit:
        transaction = TransactionData.payment
        account = AccountData.user_account
        amount = -50.00


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
