# coding=utf-8
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
        finance_account = FinanceAccountData.BankAccount
