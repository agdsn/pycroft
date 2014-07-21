# coding=utf-8
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import date, datetime, timedelta
from fixture import DataSet


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


class UserData(DataSet):
    class Dummy:
        login = u"dummy"
        name = u"Dummy Dummy"
        registration_date = datetime(2014, 1, 1)
        room = RoomData.Dummy


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


class JournalEntryData(DataSet):
    class entry01:
        id = 1
        description = u"1234-0 Mustaermann, Max"
        original_description = description
        journal = JournalData.Journal1
        amount = 1500
        other_name = u"Mustermann Max"
        other_account_number = u"DE5508154245251415235"
        other_routing_number = u"OSDDXABHF"
        import_time = datetime.utcnow()
        transaction_date = date.today()
        valid_date = date.today()


class SemesterData(DataSet):
    class CurrentSemester:
        name = "current semester"
        registration_fee = 2500
        regular_semester_contribution = 1500
        reduced_semester_contribution = 450
        overdue_fine = 250
        today = date.today()
        premature_begin_date = today - timedelta(1)
        begin_date = today
        end_date = today + timedelta(1)
        belated_end_date = today + timedelta(2)

