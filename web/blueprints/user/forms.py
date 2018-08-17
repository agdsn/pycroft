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

from pycroft.helpers.net import mac_regex
from pycroft.model.host import Host
from pycroft.model.user import PropertyGroup, User
from web.blueprints.facilities.forms import building_query
from web.blueprints.properties.forms import traffic_group_query, \
    property_group_query
from web.form.fields.core import TextField, TextAreaField, BooleanField, \
    QuerySelectField, DateField, SelectField, FormField
from web.form.fields.custom import LazyLoadSelectField
from web.form.fields.validators import OptionalIf


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
    mac = TextField(u"MAC-Adresse")
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


class UserEditNameForm(Form):
    name = TextField(u"Name", [DataRequired(message=u"Name wird benötigt!")])


class UserEditEMailForm(Form):
    email = TextField(u"E-Mail", [Optional(), Email(u"E-Mail-Adresse ist ungültig!")])


class UserEditBirthdateForm(Form):
    birthdate = DateField(u"Birthdate", [Optional()], format="%d.%m.%Y")


class UserMoveForm(Form):
    building = QuerySelectField(u"Wohnheim",
                                [Optional()],
                                get_label='short_name',
                                query_factory=building_query)
    level = LazyLoadSelectField(u"Etage",
                                validators=[Optional(), NumberRange(message=u"Etage?")],
                                coerce=int,
                                choices=[],
                                conditions=["building"],
                                data_endpoint="facilities.json_levels")
    room_number = LazyLoadSelectField(u"Raumnummer",
                                      validators=[Optional()],
                                      coerce=str,
                                      choices=[],
                                      conditions=["building", "level"],
                                      data_endpoint="facilities.json_rooms")


class UserCreateForm(UserMoveForm):
    name = TextField(u"Name", [DataRequired(message=u"Name wird benötigt!")])
    login = TextField(u"Login", [
        DataRequired(message=u"Login wird benötigt!"),
        Regexp(regex=User.login_regex, message=u"Login ist ungültig!"),
        validate_unique_login])
    email = TextField(u"E-Mail", [Email(message=u"E-Mail ist ungueltig!"),
                                  Optional()])
    mac = TextField(u"MAC", [OptionalIf('room_number', invert=True),
                             Regexp(regex=mac_regex, message=u"MAC ist ungültig!")])
    birthdate = DateField(u"Geburtsdatum",
                          [DataRequired(message=u"Geburtsdatum wird benötigt!")])
    annex = BooleanField(u"Host annketieren", [Optional()])
    force = BooleanField(u"* Hinweise ignorieren", [Optional()])


class UserMoveInForm(UserMoveForm):
    mac = TextField(u"MAC", [
        Regexp(regex=mac_regex, message=u"MAC ist ungültig!")])
    birthdate = DateField(u"Geburtsdatum",
                          [DataRequired(
                              message=u"Geburtsdatum wird benötigt!")])


class HostCreateForm(Form):
    name = TextField(u"Name", [DataRequired(u"Der Host benötigt einen Namen!")])


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


class UserMoveOutForm(Form):
    # when = DateField(u"Auszug am", [DataRequired()])
    comment = TextAreaField(u"Kommentar")


class InterfaceChangeMacForm(Form):
    mac = TextField(u"MAC", [
        Regexp(regex=mac_regex, message=u"MAC ist ungültig!")])


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
