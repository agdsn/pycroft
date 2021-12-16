# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import datetime

from flask_wtf import FlaskForm as Form
from wtforms import Form as WTForm, ValidationError
from wtforms.validators import DataRequired, NumberRange, Optional, \
    InputRequired
from wtforms_widgets.fields.core import (
    TextField, IntegerField, HiddenField, FileField, SelectField, FormField,
    FieldList, StringField, DateField, MoneyField, PasswordField, BooleanField,
    QuerySelectMultipleField, TextAreaField, QuerySelectField)
from wtforms_widgets.fields.custom import TypeaheadField, static, disabled

from pycroft.helpers.i18n import gettext
from pycroft.model.finance import BankAccount


class MembershipFeeCreateForm(Form):
    name = TextField("Beitragsname", validators=[DataRequired()])
    regular_fee = MoneyField(
        "Regulärer Beitrag",
        validators=[InputRequired(), NumberRange(min=0)]
    )

    # TODO Transform IntegerFields to IntervalFields

    booking_begin = IntegerField(
        "Buchungsbeginn (Tage)",
        description="Ab diesem Tag im Zeitraum wird ein Mitglied "
                    "als zahlungspflichtig angesehen.",
        validators=[InputRequired(), NumberRange(min=1)]
    )

    booking_end = IntegerField(
        "Buchungsende (Tage)",
        description="Bis zu diesem Tag im Zeitraum wird ein neues Mitglied "
                    "als zahlungspflichtig angesehen.",
        validators=[InputRequired(), NumberRange(min=1)]
    )

    payment_deadline = IntegerField(
        "Zahlungsfrist (Tage)",
        description="Bleibt ein Mitglied mehr Tage als hier angegeben eine "
                    "Zahlung schuldig, so wird es Mitglied in der "
                    "Zahlungsrückstands-Gruppe.",
        validators=[InputRequired(), NumberRange(min=0)]
    )

    payment_deadline_final = IntegerField(
        "Endgültige Zahlungsfrist (Tage)",
        description="Bleibt ein Mitglied mehr Tage als hier angegeben eine "
                    "Zahlung schuldig, so wird seine Mitgliedschaft beendet.",
        validators=[InputRequired(), NumberRange(min=0)]
    )

    begins_on = DateField(
        "Anfang", validators=[DataRequired()], today_btn=True,
        today_highlight=True
    )
    ends_on = DateField(
        "Ende", validators=[DataRequired()], today_btn=True,
        today_highlight=True
    )


class FeeApplyForm(Form):
    pass


class MembershipFeeEditForm(MembershipFeeCreateForm):
    pass


class BankAccountCreateForm(Form):
    name = TextField("Name")
    bank = TextField("Bank")
    account_number = TextField("Kontonummer")
    routing_number = TextField("Bankleitzahl (BLZ)")
    iban = TextField("IBAN")
    bic = TextField("BIC")
    fints = TextField("FinTS-Endpunkt", default="https://mybank.com/…")

    def validate_iban(self, field):
        if BankAccount.q.filter_by(iban=field.data ).first() is not None:
            raise ValidationError("Konto existiert bereits.")


class BankAccountActivityReadForm(Form):
    bank_account_name = static(StringField("Bankkonto"))
    amount = disabled(MoneyField("Wert"))
    reference = static(StringField("Verwendungszweck"))
    other_account_number = static(StringField("Kontonummer"))
    other_routing_number = static(StringField("Bankleitzahl (BLZ)"))
    other_name = static(StringField("Name"))
    valid_on = static(DateField("Valutadatum"))
    posted_on = static(DateField("Buchungsdatum"))


class BankAccountActivityEditForm(BankAccountActivityReadForm):
    account = TypeaheadField("Gegenkonto", render_kw={
        'data_toggle': 'account-typeahead',
        'data-target': 'account_id'
    })
    account_id = HiddenField(validators=[DataRequired()])
    description = StringField("Beschreibung")


class BankAccountActivitiesImportForm(Form):
    account = SelectField("Bankkonto", coerce=int)
    user = StringField("Loginname", validators=[DataRequired()])
    pin = PasswordField("PIN", validators=[DataRequired()])
    start_date = DateField("Startdatum")
    end_date = DateField("Enddatum")
    do_import = BooleanField("Import durchführen", default=False)


class BankAccountActivitiesImportManualForm(Form):
    account = QuerySelectField('Bankkonto', get_label="name")
    file = FileField('MT940 Datei')


class AccountCreateForm(Form):
    name = TextField("Name", validators=[DataRequired()])
    type = SelectField(
        "Typ", validators=[DataRequired()],
        choices=[
            ("ASSET", "Aktivkonto"), ("LIABILITY", "Passivkonto"),
            ("EXPENSE", "Aufwandskonto"), ("REVENUE", "Ertragskonto"),
        ]
    )


# Subclass WTForms Form to disable Flask-WTF’s CSRF mechanism
class SplitCreateForm(WTForm):
    account = TypeaheadField("Konto", validators=[DataRequired()])
    account_id = HiddenField(validators=[DataRequired(message=gettext("Missing account."))])
    amount = MoneyField("Wert", validators=[DataRequired(message=gettext("Invalid value."))])

    def validate_amount(self, field):
        cents = field.data.shift(2)
        if cents == 0 or cents != int(cents):
            raise ValidationError(gettext("Invalid value."))


class TransactionCreateForm(Form):
    description = TextField("Beschreibung", validators=[DataRequired()])
    valid_on = DateField(
        "Gültig ab", validators=[Optional()], today_btn=True,
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
            raise ValidationError("Buchung ist nicht ausgeglichen.")


class ActivityMatchForm(Form):
    pass


def get_user_name_with_id(user):
    return f"{user.name} ({user.id})"


def get_user_name_with_id_and_balance(user):
    return f"{user.name} ({user.id}) | {-user.account.balance}€"


class HandlePaymentsInDefaultForm(Form):
    new_pid_memberships = QuerySelectMultipleField("Neue Mitgliedschaften in der 'Zahlungsrückstand' Gruppe",
                                                   get_label=get_user_name_with_id_and_balance,
                                                   render_kw={'size': 20})
    terminated_member_memberships = QuerySelectMultipleField("Beendete Mitgliedschaften/Auszüge",
                                                             get_label=get_user_name_with_id_and_balance,
                                                             render_kw={'size': 20})

class FixMT940Form(Form):
    mt940 = TextAreaField('MT940')
    do_import = BooleanField("Import durchführen", default=False)
