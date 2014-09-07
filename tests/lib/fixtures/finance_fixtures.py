# coding=utf-8
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import date, datetime, timedelta
from fixture import DataSet

__author__ = 'shreyder'


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
    class BankAccount:
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


class PropertyGroupData(DataSet):
    class dummy:
        name = "dummy"


class PropertyData(DataSet):
    class pay_registration_fee:
        granted = True
        name = "pay_registration_fee"
        property_group = PropertyGroupData.dummy

    class pay_semester_fee:
        granted = True
        name = "pay_semester_fee"
        property_group = PropertyGroupData.dummy

    class pay_late_fee:
        granted = True
        name = "pay_late_fee"
        property_group = PropertyGroupData.dummy


class UserData(DataSet):
    class Dummy:
        login = u"dummy"
        name = u"Dummy Dummy"
        registered_at = datetime(2014, 1, 1)
        room = RoomData.Dummy
        finance_account = FinanceAccountData.Asset


class MembershipData(DataSet):
    class dummy:
        start_date = datetime.utcnow() - timedelta(1)
        end_date = datetime.utcnow() + timedelta(1)
        user = UserData.Dummy
        group = PropertyGroupData.dummy


class JournalData(DataSet):
    class Journal1:
        name = u"Hauptkonto"
        bank = u"Ostsächsische Sparkasse Dresden"
        account_number = "3120219540"
        routing_number = "85050300"
        iban = "DE61850503003120219540"
        bic = "OSDDDE81XXX"
        hbci_url = "https://hbci.example.com/"
        finance_account = FinanceAccountData.BankAccount


class SemesterData(DataSet):
    class CurrentSemester:
        name = "current semester"
        registration_fee = 0
        regular_semester_fee = 2000
        reduced_semester_fee = 100
        late_fee = 250
        begin_date = date.today()
        end_date = begin_date + timedelta(1)

    class PreviousSemester:
        name = "previous semester"
        registration_fee = 2500
        regular_semester_fee = 1500
        reduced_semester_fee = 450
        late_fee = 250
        end_date = date.today() - timedelta(1)
        begin_date = end_date - timedelta(1)

