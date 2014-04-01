# -*- coding: utf-8 -*-

__author__ = 'florian'

from web.form.fields import DatePickerField
from flask.ext.wtf import Form
from wtforms import TextField, IntegerField, HiddenField, FileField
from pycroft.model.finance import FinanceAccount


def financeaccounts_query():
    return FinanceAccount.q.order_by(FinanceAccount.name)


class SemesterCreateForm(Form):
    name = TextField(u"Semestername")
    registration_fee = IntegerField(u"Anmeldegebühr")
    semester_fee = IntegerField(u"Semesterbeitrag")
    begin_date = DatePickerField(u"Anfang")
    end_date = DatePickerField(u"Ende")


class JournalCreateForm(Form):
    name = TextField(u"Name")
    bank = TextField(u"Bank")
    hbci_url = TextField(u"HBCI-URL")
    account_number = IntegerField(u"Kontonummer")
    bank_identification_code = IntegerField(u"Banknummer")


class JournalLinkForm(Form):
    search = TextField()
    account_id = HiddenField()
    #linked_accounts = QuerySelectField(u"Zugehoeriges Konto",
                          # get_label='name',
                          # query_factory=financeaccounts_query,
                          # allow_blank=True)

class JournalImportForm(Form):
    csv_file = FileField()
