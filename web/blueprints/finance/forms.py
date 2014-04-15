# -*- coding: utf-8 -*-

__author__ = 'florian'

from web.form.fields import DatePickerField
from flask.ext.wtf import Form
from wtforms import TextField, IntegerField, HiddenField, FileField, SelectField
from wtforms.validators import DataRequired, NumberRange
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from pycroft.model.finance import FinanceAccount, Semester


def financeaccounts_query():
    return FinanceAccount.q.order_by(FinanceAccount.name)


def semester_query():
    return Semester.q.all()


class SemesterCreateForm(Form):
    name = TextField(u"Semestername", validators=[DataRequired()])
    registration_fee = IntegerField(
        u"Anmeldegebühr", validators=[DataRequired(), NumberRange(min=1)])
    regular_membership_fee = IntegerField(
        u"Regulärer Beitrag", validators=[DataRequired(), NumberRange(min=1)])
    reduced_membership_fee = IntegerField(
        u"Ermäßigter Beitrag", validators=[DataRequired(), NumberRange(min=1)])
    overdue_fine = IntegerField(
        u"Versäumnisgebühr", validators=[DataRequired(), NumberRange(min=1)])
    premature_begin_date = DatePickerField(
        u"Vorzeitiger Anfang", validators=[DataRequired()])
    begin_date = DatePickerField(u"Anfang", validators=[DataRequired()])
    end_date = DatePickerField(u"Ende", validators=[DataRequired()])
    belated_end_date = DatePickerField(
        u"Verspätetes Ende", validators=[DataRequired()])


class JournalCreateForm(Form):
    name = TextField(u"Name")
    bank = TextField(u"Bank")
    hbci_url = TextField(u"HBCI-URL")
    account_number = TextField(u"Kontonummer")
    bank_identification_code = TextField(u"Banknummer")


class JournalLinkForm(Form):
    search = TextField()
    account_id = HiddenField()
    #linked_accounts = QuerySelectField(u"Zugehoeriges Konto",
                          # get_label='name',
                          # query_factory=financeaccounts_query,
                          # allow_blank=True)


class JournalImportForm(Form):
    csv_file = FileField()


class FinanceaccountCreateForm(Form):
    name = TextField(u"Name")
    type = SelectField(u"Typ", choices=[("LIABILITY","Passivkonto"), ("EXPENSE", "Aufwandskonto"),
                                        ("ASSET", "Aktivkonto"), ("INCOME", "Ertragskonto"), ("EQUITY", "Equity")])
    semester = QuerySelectField(u"Semester", get_label='name', query_factory=semester_query, allow_blank=True)
    tag = HiddenField() #TODO
