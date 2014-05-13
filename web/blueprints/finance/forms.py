# -*- coding: utf-8 -*-

__author__ = 'florian'

from web.form.fields import static
from flask.ext.wtf import Form
from wtforms.validators import DataRequired, NumberRange, Optional
from web.form.fields.core import TextField, IntegerField, HiddenField,\
    FileField, SelectField, FormField, FieldList, StringField, DateField
from web.form.fields.custom import TypeaheadField


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
    premature_begin_date = DateField(
        u"Vorzeitiger Anfang", validators=[DataRequired()], today_btn=True,
        today_highlight=True)
    begin_date = DateField(
        u"Anfang", validators=[DataRequired()], today_btn=True,
        today_highlight=True)
    end_date = DateField(u"Ende", validators=[DataRequired()], today_btn=True,
        today_highlight=True)
    belated_end_date = DateField(
        u"Verspätetes Ende", validators=[DataRequired()], today_btn=True,
        today_highlight=True)


class JournalCreateForm(Form):
    name = TextField(u"Name")
    bank = TextField(u"Bank")
    account_number = TextField(u"Kontonummer")
    routing_number = TextField(u"Bankleitzahl (BLZ)")
    iban = TextField(u"IBAN")
    bic = TextField(u"BIC")
    hbci_url = TextField(u"HBCI-URL")


class JournalEntryEditForm(Form):
    finance_account = TypeaheadField(u"Gegenkonto")
    finance_account_id = HiddenField(validators=[DataRequired()])
    journal_name = static(StringField(u"Bankkonto"))
    amount = static(IntegerField(u"Wert"))
    description = StringField(u"Beschreibung")
    original_description = static(StringField(u"Ursprüngliche Beschreibung"))
    other_account_number = static(StringField(u"Kontonummer"))
    other_routing_number = static(StringField(u"Bankleitzahl (BLZ)"))
    other_name = static(StringField(u"Name"))
    valid_date = static(DateField(u"Valutadatum"))
    transaction_date = static(DateField(u"Buchungsdatum"))


class JournalImportForm(Form):
    csv_file = FileField()


class FinanceAccountCreateForm(Form):
    name = TextField(u"Name", validators=[DataRequired()])
    type = SelectField(
        u"Typ", validators=[DataRequired()],
        choices=[
            ("ASSET", "Aktivkonto"), ("LIABILITY", "Passivkonto"),
            ("EXPENSE", "Aufwandskonto"), ("REVENUE", "Ertragskonto"),
        ]
    )
