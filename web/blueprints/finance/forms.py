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
    FieldList, StringField, DateField, MoneyField, PasswordField, DecimalField,
    BooleanField, SelectMultipleField, QuerySelectMultipleField, TextAreaField)
from web.form.fields.custom import TypeaheadField, static, disabled
from pycroft.helpers.i18n import gettext
from pycroft.model.finance import BankAccount


class MembershipFeeCreateForm(Form):
    name = TextField(u"Beitragsname", validators=[DataRequired()])
    regular_fee = MoneyField(
        u"Regulärer Beitrag",
        validators=[InputRequired(), NumberRange(min=0)]
    )

    # TODO Transform IntegerFields to IntervalFields

    booking_begin = IntegerField(
        u"Buchungsbeginn (Tage)",
        description=u"Ab diesem Tag im Zeitraum wird ein Mitglied "
                    u"als zahlungspflichtig angesehen.",
        validators=[InputRequired(), NumberRange(min=1)]
    )

    booking_end = IntegerField(
        u"Buchungsende (Tage)",
        description=u"Bis zu diesem Tag im Zeitraum wird ein neues Mitglied "
                    u"als zahlungspflichtig angesehen.",
        validators=[InputRequired(), NumberRange(min=1)]
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

    begins_on = DateField(
        u"Anfang", validators=[DataRequired()], today_btn=True,
        today_highlight=True
    )
    ends_on = DateField(
        u"Ende", validators=[DataRequired()], today_btn=True,
        today_highlight=True
    )


class FeeApplyForm(Form):
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


class BankAccountActivityReadForm(Form):
    bank_account_name = static(StringField(u"Bankkonto"))
    amount = disabled(MoneyField(u"Wert"))
    reference = static(StringField(u"Verwendungszweck"))
    other_account_number = static(StringField(u"Kontonummer"))
    other_routing_number = static(StringField(u"Bankleitzahl (BLZ)"))
    other_name = static(StringField(u"Name"))
    valid_on = static(DateField(u"Valutadatum"))
    posted_on = static(DateField(u"Buchungsdatum"))


class BankAccountActivityEditForm(BankAccountActivityReadForm):
    account = TypeaheadField(u"Gegenkonto", render_kw={
        'data_toggle': 'account-typeahead',
        'data-target': 'account_id'
    })
    account_id = HiddenField(validators=[DataRequired()])
    description = StringField(u"Beschreibung")


class BankAccountActivitiesImportForm(Form):
    account = SelectField(u"Bankkonto", coerce=int)
    user = StringField(u"Loginname", validators=[DataRequired()])
    pin = PasswordField(u"PIN", validators=[DataRequired()])
    start_date = DateField(u"Startdatum")
    end_date = DateField(u"Enddatum")
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


class ActivityMatchForm(Form):
    pass


def get_user_name_with_id(user):
    return "{} ({})".format(user.name, user.id)


class HandlePaymentsInDefaultForm(Form):
    new_pid_memberships = QuerySelectMultipleField(u"Neue Mitgliedschaften in der 'Zahlungsrückstand' Gruppe",
                                                   get_label=get_user_name_with_id,
                                                   render_kw={'size': 20})
    terminated_member_memberships = QuerySelectMultipleField(u"Beendete Mitgliedschaften/Auszüge",
                                                             get_label=get_user_name_with_id,
                                                             render_kw={'size': 20})

class FixMT940Form(Form):
    mt940 = TextAreaField(u'MT940')
    do_import = BooleanField(u"Import durchführen", default=False)
