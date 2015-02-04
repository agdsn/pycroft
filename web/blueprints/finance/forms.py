# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from flask.ext.wtf import Form
from wtforms import Form as WTForm, ValidationError
from wtforms.validators import DataRequired, NumberRange, Optional

from web.form.fields.core import (
    TextField, IntegerField, HiddenField, FileField, SelectField, FormField,
    FieldList, StringField, DateField)
from web.form.fields.custom import TypeaheadField, static


class SemesterCreateForm(Form):
    name = TextField(u"Semestername", validators=[DataRequired()])
    registration_fee = IntegerField(
        u"Anmeldegebühr", validators=[DataRequired(), NumberRange(min=0)])
    regular_semester_fee = IntegerField(
        u"Regulärer Semesterbeitrag",
        validators=[DataRequired(), NumberRange(min=0)]
    )
    reduced_semester_fee = IntegerField(
        u"Ermäßigter Semesterbeitrag",
        validators=[DataRequired(), NumberRange(min=0)]
    )
    late_fee = IntegerField(
        u"Versäumnisgebühr", validators=[DataRequired(), NumberRange(min=0)]
    )
    # TODO Add form fields to specify these values
    grace_period = IntegerField(
        u"Kulanzfrist (in Tagen)",
        description=u"Ist ein Nutzer weniger oder gleich viele Tage innerhalb "
                    u"eines Semesters Mitglied, so entfällt jegliche "
                    u"Semestergebühr.",
        validators=[DataRequired(), NumberRange(min=0)]
    )
    reduced_semester_fee_threshold = IntegerField(
        u"Ermäßigung ab (in Tagen)",
        description=u"Ist ein Nutzer innerhalb eines Semester so viele Tage "
                    u"wie hier angeben oder länger abwesend, fällt nur der "
                    u"ermäßigte Beitrag an.",
        validators=[DataRequired(), NumberRange(min=0)]
    )
    payment_deadline = IntegerField(
        u"Zahlungsfrist (in Tagen)",
        description=u"Bleibt ein Mitglied mehr Tage als hier angegeben eine "
                    u"Zahlung schuldig, so fällt die Versäumnisgebühr an.",
        validators=[DataRequired(), NumberRange(min=0)]
    )
    allowed_overdraft = IntegerField(
        u"Versäumnisgebühr ab Saldo",
        description=u"Saldo ab dem eine Versäumnisgebühr anfallen kann. "
                    u"Versäumnisgebühren müssen angemessen sein, ansonsten",
        validators=[DataRequired(), NumberRange(min=0)]
    )
    begin_date = DateField(
        u"Anfang", validators=[DataRequired()], today_btn=True,
        today_highlight=True
    )
    end_date = DateField(
        u"Ende", validators=[DataRequired()], today_btn=True,
        today_highlight=True
    )


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
    expected_balance = IntegerField(u"Erwarteter Kontostand")
    csv_file = FileField(u"Umsätze (CSV-MT940)")


class FinanceAccountCreateForm(Form):
    name = TextField(u"Name", validators=[DataRequired()])
    type = SelectField(
        u"Typ", validators=[DataRequired()],
        choices=[
            ("ASSET", "Aktivkonto"), ("LIABILITY", "Passivkonto"),
            ("EXPENSE", "Aufwandskonto"), ("REVENUE", "Ertragskonto"),
        ]
    )


# Subclass WTForms Form to disable Flask-WTF’s CSRF mechanism
class SplitCreateForm(WTForm):
    account = TypeaheadField(u"Konto", validators=[DataRequired()])
    account_id = HiddenField(validators=[DataRequired()])
    amount = IntegerField(u"Wert", validators=[DataRequired()])


class TransactionCreateForm(Form):
    description = TextField(u"Beschreibung", validators=[DataRequired()])
    valid_date = DateField(
        u"Gültig ab", validators=[Optional()], today_btn=True,
        today_highlight=True)
    splits = FieldList(
        FormField(SplitCreateForm),
        validators=[DataRequired()],
        min_entries=2
    )

    def validate_splits(self, field):
        if sum(split_form['amount'].data for split_form in field
               if split_form['amount'].data is not None
            ) != 0:
            raise ValidationError(u"Buchung ist nicht ausgeglichen.")


