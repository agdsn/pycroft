# coding=utf-8
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime, time, timedelta
from fixture import DataSet

__author__ = 'shreyder'


today = datetime.utcnow().date()


class SemesterData(DataSet):
    class with_registration_fee:
        name = "previous semester"
        registration_fee = 2500
        regular_semester_fee = 1500
        reduced_semester_fee = 450
        late_fee = 250
        grace_period = timedelta(62)
        reduced_semester_fee_threshold = timedelta(62)
        payment_deadline = timedelta(31)
        allowed_overdraft = 500
        begins_on = today - timedelta(days=271)
        ends_on = today - timedelta(days=91)

    class without_registration_fee:
        name = "current semester"
        registration_fee = 0
        regular_semester_fee = 2000
        reduced_semester_fee = 100
        late_fee = 250
        grace_period = timedelta(62)
        reduced_semester_fee_threshold = timedelta(62)
        payment_deadline = timedelta(31)
        allowed_overdraft = 500
        begins_on = today - timedelta(days=90)
        ends_on = today + timedelta(days=90)


class DormitoryData(DataSet):
    class Dummy:
        number = "01"
        short_name = "abc"
        street = "dummy"


class RoomData(DataSet):
    class Dummy:
        number = 1
        level = 1
        inhabitable = True
        dormitory = DormitoryData.Dummy


class FinanceAccountData(DataSet):
    class bank_account:
        name = u"Bankkonto 3120219540"
        type = "ASSET"

    class Asset:
        name = u"Asset"
        type = "ASSET"

    class Liability:
        name = u"Liability"
        type = "LIABILITY"

    class Expense:
        name = u"Expense"
        type = "EXPENSE"

    class Revenue:
        name = u"Revenue"
        type = "REVENUE"

    class fee_account:
        name = u"Fees"
        type = "REVENUE"

    class late_fee_account:
        name = u"Late Fees"
        type = "REVENUE"

    class user_account:
        name = u"Dummy User"
        type = "ASSET"


class PropertyGroupData(DataSet):
    class member:
        name = "Members"

    class away:
        name = "Away Members"


class PropertyData(DataSet):
    class registration_fee:
        granted = True
        name = "registration_fee"
        property_group = PropertyGroupData.member

    class semester_fee:
        granted = True
        name = "semester_fee"
        property_group = PropertyGroupData.member

    class late_fee:
        granted = True
        name = "late_fee"
        property_group = PropertyGroupData.member

    class away:
        granted = True
        name = "away"
        property_group = PropertyGroupData.away


class UserData(DataSet):
    class dummy:
        login = u"dummy"
        name = u"Dummy Dummy"
        registered_at = datetime.combine(SemesterData.with_registration_fee.begins_on + timedelta(days=31), time.min)
        room = RoomData.Dummy
        finance_account = FinanceAccountData.user_account


class MembershipData(DataSet):
    class dummy:
        begins_at = UserData.dummy.registered_at
        ends_at = None
        user = UserData.dummy
        group = PropertyGroupData.member


class TransactionData(DataSet):
    class claim1:
        description = "Claim 1"
        valid_date = SemesterData.with_registration_fee.begins_on + timedelta(days=31)

    class late_fee_for_claim1:
        description = "Late fee for Claim 1"
        valid_date = SemesterData.with_registration_fee.begins_on + timedelta(days=63)

    class claim2:
        description = "Claim 2"
        valid_date = SemesterData.with_registration_fee.begins_on + timedelta(days=81)

    class payment:
        description = "Payment of Claim 1"
        valid_date = SemesterData.with_registration_fee.begins_on + timedelta(days=64)


class SplitData(DataSet):
    class claim1_credit:
        transaction = TransactionData.claim1
        account = FinanceAccountData.user_account
        amount = 5000

    class claim1_debit:
        transaction = TransactionData.claim1
        account = FinanceAccountData.fee_account
        amount = -5000

    class late_fee1_credit:
        transaction = TransactionData.late_fee_for_claim1
        account = FinanceAccountData.user_account
        amount = 2500

    class late_fee2_credit:
        transaction = TransactionData.late_fee_for_claim1
        account = FinanceAccountData.late_fee_account
        amount = -2500

    class claim2_credit:
        transaction = TransactionData.claim2
        account = FinanceAccountData.user_account
        amount = 5000

    class claim2_debit:
        transaction = TransactionData.claim2
        account = FinanceAccountData.fee_account
        amount = -5000

    class payment_credit:
        transaction = TransactionData.payment
        account = FinanceAccountData.bank_account
        amount = 5000

    class payment_debit:
        transaction = TransactionData.payment
        account = FinanceAccountData.user_account
        amount = -5000


class JournalData(DataSet):
    class Journal1:
        name = u"Hauptkonto"
        bank = u"Ostsächsische Sparkasse Dresden"
        account_number = "3120219540"
        routing_number = "85050300"
        iban = "DE61850503003120219540"
        bic = "OSDDDE81XXX"
        hbci_url = "https://hbci.example.com/"
        finance_account = FinanceAccountData.bank_account
