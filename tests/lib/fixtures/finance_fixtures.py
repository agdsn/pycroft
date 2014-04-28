# coding=utf-8
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import datetime
from fixture import DataSet

__author__ = 'shreyder'


class FinanceAccountData(DataSet):
    class BankAccount:
        name = u"Bankkonto 3120219540"
        type = "ASSET"


class JournalData(DataSet):
    class Journal1:
        name = u"Hauptkonto"
        bank = u"Ostsächsische Sparkasse Dresden"
        account_number = "3120219540"
        routing_number = "85050300"
        iban = "DE61850503003120219540"
        bic = "OSDDDE81XXX"
        hbci_url = "https://hbci.example.com/"
        financeaccount = FinanceAccountData.BankAccount
