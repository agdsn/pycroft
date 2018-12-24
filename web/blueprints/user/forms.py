# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import re
from difflib import SequenceMatcher

from flask import url_for
from flask_wtf import FlaskForm as Form
from wtforms.validators import (
    Regexp, NumberRange, ValidationError, DataRequired, Email, Optional)

from pycroft.model.host import Host
from pycroft.model.user import PropertyGroup, User
from web.blueprints.facilities.forms import building_query, SelectRoomForm, SelectRoomFormOptional
from web.blueprints.properties.forms import traffic_group_query, \
    property_group_query, property_group_user_create_query
from web.form.fields.core import TextField, TextAreaField, BooleanField, \
    QuerySelectField, DateField, SelectField, FormField, \
    QuerySelectMultipleField, SelectMultipleField
from web.form.fields.custom import LazyLoadSelectField, MacField, UserIDField
from web.form.fields.filters import empty_to_none, to_lowercase
from web.form.fields.validators import OptionalIf, MacAddress


def user_query():
    return User.q.order_by(User.id)


def host_query():
    return Host.q.order_by(Host.id)


def group_query():
    return PropertyGroup.q.order_by(PropertyGroup.name)


def validate_unique_login(form, field):
    if User.q.filter_by(login=field.data).first():
        raise ValidationError(u"Nutzerlogin schon vergeben!")


class UserSearchForm(Form):
    id = TextField(u"Nutzer-ID")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")
    mac = MacField(u"MAC-Adresse")
    ip_address = TextField(u"IP-Adresse")
    traffic_group_id = QuerySelectField(u"Trafficgruppe",
                                get_label='name',
                                query_factory=traffic_group_query,
                                allow_blank=True,
                                blank_text=u"<Trafficgruppe>")
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


class UserResetPasswordForm(Form):
    pass


class UserEditForm(Form):
    name = TextField(u"Name", [DataRequired(message=u"Name wird benötigt!")])
    email = TextField(u"E-Mail",
                      [Optional(), Email(u"E-Mail-Adresse ist ungültig!")])
    birthdate = DateField(u"Geburtsdatum", [Optional()])


class UserMoveForm(SelectRoomForm):
    pass


class UserCreateForm(SelectRoomFormOptional):
    name = TextField(u"Name", [DataRequired(message=u"Name wird benötigt!")])

    login = TextField(u"Login", [
        DataRequired(message=u"Login wird benötigt!"),
        Regexp(regex=User.login_regex_ci, message=u"Login ist ungültig!"),
        validate_unique_login],
                      filters=[to_lowercase])
    email = TextField(u"E-Mail", [Email(message=u"E-Mail ist ungueltig!"),
                                  Optional()], filters=[empty_to_none])
    birthdate = DateField(u"Geburtsdatum",
                          [OptionalIf('mac', invert=True)])
    mac = MacField(u"MAC",
                   [MacAddress(message=u"MAC ist ungültig!"), Optional()])
    property_groups = QuerySelectMultipleField(u"Gruppen",
                                      get_label='name',
                                      query_factory=property_group_user_create_query)
    annex = BooleanField(u"Host annektieren", [Optional()])
    force = BooleanField(u"* Hinweise ignorieren", [Optional()])

    _order = ("name", "building", "level", "room_number")


class UserMoveInForm(UserMoveForm):
    birthdate = DateField(u"Geburtsdatum", [OptionalIf('mac', invert=True)])
    mac = MacField(u"MAC", [Optional()])
    begin_membership = BooleanField(u"Mitgliedschaft beginnen", [Optional()])


class UserLogEntry(Form):
    message = TextAreaField(u"", [DataRequired()])


class OptionallyUnlimitedEndDateForm(Form):
    unlimited = BooleanField(u"Unbegrenzte Dauer", default=False)
    date = DateField(u"Ende", [OptionalIf("unlimited")])


class UserAddGroupMembership(Form):
    group = QuerySelectField(u"Gruppe", get_label='name',
                             query_factory=group_query)
    begins_at = DateField(u"Beginn", [DataRequired()])
    ends_at = FormField(OptionallyUnlimitedEndDateForm)


class UserEditGroupMembership(Form):
    begins_at = DateField(u"Beginn", [DataRequired()])
    ends_at = FormField(OptionallyUnlimitedEndDateForm)


class UserSuspendForm(Form):
    ends_at = FormField(OptionallyUnlimitedEndDateForm)
    reason = TextAreaField(u"Grund", [DataRequired()])
    violation = BooleanField("Verstoß")


class UserMoveOutForm(Form):
    # when = DateField(u"Auszug am", [DataRequired()])
    comment = TextAreaField(u"Kommentar")
    end_membership = BooleanField(u"Mitgliedschaft/Extern beenden", [Optional()])


class HostForm(SelectRoomForm):
    owner_id = UserIDField(u"Besitzer-ID")
    name = TextField(u"Name", [DataRequired(u"Der Host benötigt einen Namen!")],
                     description=u"z.B. TP-LINK WR841, FritzBox 4040 oder MacBook")

    _order = ("name", "owner_id")


class InterfaceForm(Form):
    host = QuerySelectField(u"Host", get_label='name')
    mac = MacField(u"MAC", [MacAddress(message=u"MAC ist ungültig!")])
    ips = SelectMultipleField(u"IPs", validators=[Optional()])


class UserSelectGroupForm(Form):
    group_type = SelectField(u"Typ",
                             [DataRequired(message=u"Typ?")],
                             coerce=str,
                             choices=[('prop', u"Eigenschaft"),
                                      ('traff', u"Traffic")])
    group = LazyLoadSelectField(u"Gruppe",
                                [DataRequired(message=u"Gruppe angeben!")],
                                coerce=str,
                                choices=[],
                                conditions=["group_type"],
                                data_endpoint="user.json_groups")
