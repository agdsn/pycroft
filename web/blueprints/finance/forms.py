# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import datetime
from flask_wtf import FlaskForm as Form
from wtforms import Form as WTForm, ValidationError
from wtforms.validators import DataRequired, NumberRange, Optional, \
    InputRequired

from web.form.fields.core import (
    TextField, IntegerField, HiddenField, FileField, SelectField, FormField,
    FieldList, StringField, DateField, MoneyField, PasswordField, DecimalField, BooleanField)
from web.form.fields.custom import TypeaheadField, static, disabled
from pycroft.helpers.i18n import gettext
from pycroft.model.finance import BankAccount


class MembershipFeeCreateForm(Form):
    name = TextField(u"Beitragsname", validators=[DataRequired()])
    registration_fee = MoneyField(
        u"Anmeldegebühr", validators=[InputRequired(), NumberRange(min=0)])
    regular_fee = MoneyField(
        u"Regulärer Beitrag",
        validators=[InputRequired(), NumberRange(min=0)]
    )
    reduced_fee = MoneyField(
        u"Ermäßigter Beitrag",
        validators=[InputRequired(), NumberRange(min=0)]
    )
    late_fee = MoneyField(
        u"Versäumnisgebühr", validators=[InputRequired(), NumberRange(min=0)]
    )
    # TODO Add form fields to specify these values
    grace_period = IntegerField(
        u"Kulanzfrist (Tage)",
        description=u"Ist ein Nutzer weniger oder gleich viele Tage innerhalb "
                    u"des Zeitraums Mitglied, so entfällt jegliche "
                    u"Gebühr.",
        validators=[InputRequired(), NumberRange(min=0)]
    )
    reduced_fee_threshold = IntegerField(
        u"Ermäßigung ab (Tage)",
        description=u"Ist ein Nutzer innerhalb eines Zeitraums so viele Tage "
                    u"wie hier angeben oder länger abwesend, fällt nur der "
                    u"ermäßigte Beitrag an.",
        validators=[InputRequired(), NumberRange(min=0)]
    )

    payment_deadline = IntegerField(
        u"Zahlungsfrist (Tage)",
        description=u"Bleibt ein Mitglied mehr Tage als hier angegeben eine "
                    u"Zahlung schuldig, so fällt die Versäumnisgebühr an. "
                    u"Der Nutzer wird zudem Mitglied in der "
                    u"Zahlungsrückstands-Gruppe.",
        validators=[InputRequired(), NumberRange(min=0)]
    )

    payment_deadline_final = IntegerField(
        u"Endgültige Zahlungsfrist (Tage)",
        description=u"Bleibt ein Mitglied mehr Tage als hier angegeben eine "
                    u"Zahlung schuldig, so wird die Mitgliedschaft beendet.",
        validators=[InputRequired(), NumberRange(min=0)]
    )

    not_allowed_overdraft_late_fee = MoneyField(
        u"Versäumnisgebühr ab Saldo",
        description=u"Saldo ab dem eine Versäumnisgebühr anfallen kann. "
                    u"Versäumnisgebühren müssen angemessen sein.",
        validators=[InputRequired(), NumberRange(min=0)]
    )

    begins_on = DateField(
        u"Anfang", validators=[DataRequired()], today_btn=True,
        today_highlight=True
    )
    ends_on = DateField(
        u"Ende", validators=[DataRequired()], today_btn=True,
        today_highlight=True
    )


class FeeApplyForm(Form):
    apply_registration_fee = disabled(BooleanField(u"Anmeldegebühr"))
    apply_membership_fee = BooleanField(u"Mitgliedsbeitrag")
    apply_late_fee = disabled(BooleanField(u"Versäumnisgebühr"))

class HandlePaymentsInDefaultForm(Form):
    pass


class MembershipFeeEditForm(MembershipFeeCreateForm):
    pass


class BankAccountCreateForm(Form):
    name = TextField(u"Name")
    bank = TextField(u"Bank")
    account_number = TextField(u"Kontonummer")
    routing_number = TextField(u"Bankleitzahl (BLZ)")
    iban = TextField(u"IBAN")
    bic = TextField(u"BIC")
    fints = TextField(u"FinTS-Endpunkt", default="https://mybank.com/…")

    def validate_iban(self, field):
        if BankAccount.q.filter_by(iban=field.data ).first() is not None:
            raise ValidationError("Konto existiert bereits.")

class BankAccountActivityEditForm(Form):
    account = TypeaheadField(u"Gegenkonto")
    account_id = HiddenField(validators=[DataRequired()])
    bank_account_name = static(StringField(u"Bankkonto"))
    amount = disabled(MoneyField(u"Wert"))
    description = StringField(u"Beschreibung")
    original_reference = static(StringField(u"Ursprüngliche Verwendung"))
    other_account_number = static(StringField(u"Kontonummer"))
    other_routing_number = static(StringField(u"Bankleitzahl (BLZ)"))
    other_name = static(StringField(u"Name"))
    valid_on = static(DateField(u"Valutadatum"))
    posted_on = static(DateField(u"Buchungsdatum"))


class BankAccountActivitiesImportForm(Form):
    account = SelectField(u"Bankkonto", coerce=int)
    user = StringField(u"Loginname", validators=[DataRequired()])
    pin = PasswordField(u"PIN", validators=[DataRequired()])
    do_import = BooleanField(u"Import durchführen", default=False)


class AccountCreateForm(Form):
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
    account_id = HiddenField(validators=[DataRequired(message=gettext("Missing account."))])
    amount = MoneyField(u"Wert", validators=[DataRequired(message=gettext("Invalid value."))])

    def validate_amount(self, field):
        cents = field.data.shift(2)
        if cents == 0 or cents != int(cents):
            raise ValidationError(gettext("Invalid value."))


class TransactionCreateForm(Form):
    description = TextField(u"Beschreibung", validators=[DataRequired()])
    valid_on = DateField(
        u"Gültig ab", validators=[Optional()], today_btn=True,
        today_highlight=True, default=datetime.date.today())
    splits = FieldList(
        FormField(SplitCreateForm),
        validators=[DataRequired()],
        min_entries=2
    )

    def validate_splits(self, field):
        balance = sum(split_form['amount'].data for split_form in field
                      if split_form['amount'].data is not None)
        if balance != 0:
            raise ValidationError(u"Buchung ist nicht ausgeglichen.")
