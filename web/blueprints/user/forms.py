# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import typing
from difflib import SequenceMatcher

from flask import url_for
from flask_wtf import FlaskForm as Form
from wtforms import Field
from wtforms.widgets import HTMLString

from pycroft.model.address import Address
from pycroft.model.facilities import Room
from web.blueprints.helpers.host import UniqueMac
from web.form.widgets import UserIDField
from wtforms.validators import (
    Regexp, ValidationError, DataRequired, Email, Optional)

from pycroft.model.host import Host
from pycroft.model.user import PropertyGroup, User
from web.blueprints.facilities.forms import building_query, SelectRoomForm, CreateAddressForm
from web.blueprints.properties.forms import property_group_query, property_group_user_create_query
from wtforms_widgets.fields.core import TextField, TextAreaField, BooleanField, \
    QuerySelectField, FormField, \
    QuerySelectMultipleField, DateField, IntegerField
from wtforms_widgets.fields.custom import MacField
from wtforms_widgets.fields.filters import empty_to_none, to_lowercase
from wtforms_widgets.fields.validators import OptionalIf, MacAddress

from ..helpers.form import confirmable_div, ConfirmCheckboxField


def user_query():
    return User.q.order_by(User.id)


def host_query():
    return Host.q.order_by(Host.id)


def group_query():
    return PropertyGroup.q.order_by(PropertyGroup.name)


def validate_unique_login(form, field):
    if User.q.filter_by(login=field.data).first():
        raise ValidationError(u"Nutzerlogin schon vergeben!")


class UniqueName:
    """Checks whether the name of a user in a given building is unique.

    If the form misses one of the fields ``room_number``, ``level``, ``building``,
    this validator is effectively disabled.

    :param force_field: The name of the “do it anyway” checkbox field
    """
    def __init__(self, force_field: typing.Optional[str] = 'force'):
        self.force_field = force_field
        self.building_field = 'building'
        self.level_field = 'level'
        self.room_number_field = 'room_number'
        self.ratio = 0.6

    def force_set(self, form: Form) -> bool:
        return self.force_field and getattr(form, self.force_field).data

    def try_get_room(self, form: Form) -> typing.Optional[Room]:
        try:
            number = getattr(form, self.room_number_field).data
            level = getattr(form, self.level_field).data
            building = getattr(form, self.building_field).data
        except AttributeError:
            return

        return Room.q.filter_by(number=number, level=level, building=building).one_or_none()

    def similar_users(self, our_name, room: Room):
        return [u for u in room.users
                if SequenceMatcher(None, our_name, u.name).ratio() > self.ratio]

    def __call__(self, form: Form, field: Field):
        if any((
            self.force_set(form),
            (room := self.try_get_room(form)) is None,
            not (conflicting_inhabitants := self.similar_users(field.data, room))
        )):
            return

        user_links = ", ".join(
            f"""<a target="_blank" href="{url_for('user.user_show', user_id=user.id)}"/>
                  {user.name}
                </a>""" for user in conflicting_inhabitants
        )
        raise ValidationError(HTMLString(
            f'{confirmable_div(self.force_field)}'
            f'* Ähnliche Benutzer existieren bereits in diesem Zimmer:'
            f'<br/>Nutzer: {user_links}</div>'
        ))


class UniqueEmail:
    """Checks whether a given email is unique, i.e. already assigned to some user.

    :param force_field: The name of the “do it anyway” checkbox field
    """
    def __init__(self, force_field: typing.Optional[str] = 'force'):
        self.force_field = force_field

    def force_set(self, form: Form) -> bool:
        return self.force_field and getattr(form, self.force_field).data

    @staticmethod
    def get_conflicting_users(email: str) -> list[User]:
        return User.q.filter_by(email=email).all()

    def __call__(self, form: Form, field: Field):
        if any((
            self.force_set(form),
            not (conflicting_users := self.get_conflicting_users(field.data))
        )):
            return

        user_links = ", ".join(
            f"""<a target="_blank" href="{url_for('user.user_show', user_id=user.id)}"/>
                {user.name}</a>""" for user in conflicting_users
        )
        raise ValidationError(HTMLString(
            f"{confirmable_div(self.force_field)}* E-Mail bereits in Verwendung!"
            f"<br/>Nutzer:{user_links}</div>"
        ))


class UserSearchForm(Form):
    id = TextField(u"Nutzer-ID")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")
    mac = MacField(u"MAC-Adresse")
    ip_address = TextField(u"IP-Adresse")
    property_group_id = QuerySelectField(u"Eigenschaftsgruppe",
                                get_label='name',
                                query_factory=property_group_query,
                                allow_blank=True,
                                blank_text=u"<Eigenschaftsgruppe>")
    building_id = QuerySelectField(u"Wohnheim",
                                get_label='short_name',
                                query_factory=building_query,
                                allow_blank=True,
                                blank_text=u"<Wohnheim>")
    email = TextField("E-Mail")
    person_id = TextField("Debitorennummer")


class UserResetPasswordForm(Form):
    pass


class UserEditForm(Form):
    name = TextField(u"Name", [DataRequired(message=u"Name wird benötigt!")])
    email = TextField(u"E-Mail",
                      [Optional(), Email(u"E-Mail-Adresse ist ungültig!")])
    email_forwarded = BooleanField("E-Mail Weiterleitung", default=True)
    birthdate = DateField(u"Geburtsdatum", [Optional()])
    person_id = IntegerField("Debitorennummer", [Optional()],
                             filters=[empty_to_none])

class UserEditAddressForm(CreateAddressForm):
    def set_defaults_from_adress(self, address: Address):
        self.address_street.data = address.street
        self.address_number.data = address.number
        self.address_zip_code.data = address.zip_code
        self.address_city.data = address.city
        self.address_state.data = address.state
        self.address_country.data = address.country


class UserMoveForm(SelectRoomForm):
    now = BooleanField(u"Sofort", default=False)
    when = DateField(u"Umzug am", [OptionalIf("now")])


class UserBaseDataForm(Form):
    name = TextField(u"Name", [DataRequired(message=u"Name wird benötigt!"),
                               UniqueName()])

    login = TextField(u"Login", [
        DataRequired(message=u"Login wird benötigt!"),
        Regexp(regex=User.login_regex_ci, message=u"Login ist ungültig!"),
        validate_unique_login
    ], filters=[to_lowercase])
    email = TextField(u"E-Mail", [Email(message=u"E-Mail ist ungueltig!"),
                                  Optional()], filters=[empty_to_none])


class UserCreateForm(UserBaseDataForm, SelectRoomForm):
    birthdate = DateField(u"Geburtsdatum",
                          [OptionalIf('mac', invert=True)])
    mac = MacField(u"MAC",
                   [MacAddress(message=u"MAC ist ungültig!"), UniqueMac(), Optional()])
    property_groups = QuerySelectMultipleField(u"Gruppen",
                                      get_label='name',
                                      query_factory=property_group_user_create_query)
    annex = ConfirmCheckboxField(u"Host annektieren")
    force = ConfirmCheckboxField("* Hinweise ignorieren")

    _order = ("name", "building", "level", "room_number")


class NonDormantUserCreateForm(UserBaseDataForm, CreateAddressForm):
    birthdate = DateField(u"Geburtsdatum", [OptionalIf('mac', invert=True)])
    mac = MacField(u"MAC",
                   [MacAddress(message=u"MAC ist ungültig!"), Optional()])
    property_groups = QuerySelectMultipleField(u"Gruppen",
                                      get_label='name',
                                      query_factory=property_group_user_create_query)
    annex = ConfirmCheckboxField(u"Host annektieren")
    force = ConfirmCheckboxField("* Hinweise ignorieren")

    _order = (
        'name', 'login',
        *(f for f in CreateAddressForm.__dict__ if f.startswith('address_')),
        'email', 'birthdate', 'mac', 'property_groups', 'annex', 'force'
    )


class PreMemberEditForm(UserBaseDataForm, SelectRoomForm):
    # overrides `email` from UserBaseDataForm
    email = TextField("E-Mail", [DataRequired("Mitgliedschaftsanfragen benötigen E-Mail"),
                                 Email(message="E-Mail ist ungueltig!")], filters=[empty_to_none])
    birthdate = DateField(u"Geburtsdatum", [DataRequired("Das Geburtsdatum wird benötigt!")])
    move_in_date = DateField("Einzugsdatum", [Optional()])
    person_id = IntegerField("Debitorennummer", [Optional()], filters=[empty_to_none])

    force = ConfirmCheckboxField("* Hinweise ignorieren")

    _order = ("name", "building", "level", "room_number")


class PreMemberDenyForm(Form):
    reason = TextAreaField("Begründung", [Optional()], filters=[empty_to_none])
    inform_user = BooleanField("Nutzer per E-Mail informieren", [Optional()], default=True)


class PreMemberMergeForm(Form):
    user_id = UserIDField("User-ID", [DataRequired("Nutzer-ID erforderlich!")])


class PreMemberMergeConfirmForm(Form):
    merge_name = BooleanField("Name", [Optional()], default=True)
    merge_email = BooleanField("E-Mail", [Optional()], default=True)
    merge_person_id = BooleanField("Debitorennummer", [Optional()], default=True)
    merge_room = BooleanField("Einzug/Umzug", [Optional()], default=True)
    merge_password = BooleanField("Passwort aus der Registrierung", [Optional()], default=False)
    merge_birthdate = BooleanField("Geburtsdatum", [Optional()], default=False)


class UserMoveInForm(UserMoveForm):
    now = BooleanField(u"Sofort", default=False)
    when = DateField(u"Einzug am", [OptionalIf("now")])
    birthdate = DateField(u"Geburtsdatum", [OptionalIf('mac', invert=True)])
    mac = MacField(u"MAC", [Optional()])
    begin_membership = BooleanField(u"Mitgliedschaft beginnen", [Optional()])


class UserLogEntry(Form):
    message = TextAreaField(u"", [DataRequired()])


class OptionallyDirectBeginDateForm(Form):
    now = BooleanField(u"Sofort", default=False)
    date = DateField(u"Beginn", [OptionalIf("now")])


class OptionallyUnlimitedEndDateForm(Form):
    unlimited = BooleanField(u"Unbegrenzte Dauer", default=False)
    date = DateField(u"Ende", [OptionalIf("unlimited")])


class UserAddGroupMembership(Form):
    group = QuerySelectField(u"Gruppe", get_label='name',
                             query_factory=group_query)
    begins_at = FormField(OptionallyDirectBeginDateForm)
    ends_at = FormField(OptionallyUnlimitedEndDateForm)


class UserEditGroupMembership(Form):
    begins_at = DateField(u"Beginn", [DataRequired()])
    ends_at = FormField(OptionallyUnlimitedEndDateForm)


class UserSuspendForm(Form):
    ends_at = FormField(OptionallyUnlimitedEndDateForm)
    reason = TextAreaField(u"Grund", [DataRequired()])
    violation = BooleanField("Verstoß")


class UserMoveOutForm(Form):
    now = BooleanField(u"Sofort", default=False)
    when = DateField(u"Auszug am", [OptionalIf("now")])
    comment = TextAreaField(u"Kommentar")
    end_membership = BooleanField(u"Mitgliedschaft/Extern beenden", [Optional()])
