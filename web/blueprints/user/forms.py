# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime
from flask.ext.wtf import Form
from wtforms.validators import Regexp, NumberRange, ValidationError, \
    DataRequired, Optional, Email
from pycroft.model.user import User
from pycroft.model.host import Host, NetDevice
from pycroft.model.property import PropertyGroup
from pycroft.model.finance import Semester
from web.blueprints.dormitories.forms import dormitory_query
from web.form.fields.core import TextField, TextAreaField, BooleanField,\
    QuerySelectField, DateField, SelectField, FormField
from web.form.fields.custom import LazyLoadSelectField
from web.form.fields.validators import OptionalIf

def user_query():
    return User.q.order_by(User.id)


def host_query():
    return Host.q.order_by(Host.id)


def group_query():
    return PropertyGroup.q.order_by(PropertyGroup.name)


def semester_query():
    return Semester.q.order_by(Semester.name)


def validate_unique_login(form, field):
        if User.q.filter_by(login=field.data).first():
            raise ValidationError(u"Nutzerlogin schon vergeben!")


class UserSearchForm(Form):
    userid = TextField(u"Nutzerid")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")


class UserEditNameForm(Form):
    name = TextField(u"Name", [DataRequired(message=u"Name wird benötigt!")])


class UserEditEMailForm(Form):
    email = TextField(u"E-Mail", [Email(u"E-Mail-Adresse ist ungültig!")])


class UserMoveForm(Form):
    dormitory = QuerySelectField(u"Wohnheim",
        [DataRequired(message=u"Wohnheim?")],
        get_label='short_name',
        query_factory=dormitory_query)
    level = LazyLoadSelectField(u"Etage",
        validators=[NumberRange(message=u"Etage?")],
        coerce=int,
        choices=[],
        conditions=["dormitory"],
        data_endpoint="user.json_levels")
    room_number = LazyLoadSelectField(u"Raumnummer",
        validators=[DataRequired(message=u"Raum?")],
        coerce=str,
        choices=[],
        conditions=["dormitory", "level"],
        data_endpoint="user.json_rooms")


class UserCreateForm(UserEditNameForm, UserMoveForm):
    login = TextField(u"Login", [
        DataRequired(message=u"Login?"),
        Regexp(regex=User.login_regex, message=u"Login ist ungültig!"),
        validate_unique_login])
    mac = TextField(u"MAC", [
        Regexp(regex=NetDevice.mac_regex, message=u"MAC ist ungültig!")])
    host = TextField(u"Host")
    email = TextField(u"E-Mail", [Email(message=u"E-Mail ist ungueltig!")])
    moved_from_division = BooleanField(u"Umzug aus anderer Sektion")

    already_paid_semester_fee = BooleanField\
        (u"Hat dort bereits für das aktuelle Semester Beitrag bezahlt")


class HostCreateForm(Form):
    name = TextField(u"Name", [DataRequired(u"Der Host benötigt einen Namen!")])


class UserLogEntry(Form):
    message = TextAreaField(u"", [DataRequired()])

class OptionallyUnlimitedEndDateForm(Form):
    unlimited = BooleanField(u"Unbegrenzte Dauer", default=False)
    date = DateField(u"Ende", [OptionalIf("unlimited")])

class UserAddGroupMembership(Form):
    group_id = QuerySelectField(u"Gruppe",get_label='name',
                                query_factory=group_query)
    start_date = DateField(u"Beginn", [DataRequired()])
    end = FormField(OptionallyUnlimitedEndDateForm)

class UserEditGroupMembership(Form):
    start_date = DateField(u"Beginn", [DataRequired()])
    end = FormField(OptionallyUnlimitedEndDateForm)

class UserBlockForm(Form):
    end = FormField(OptionallyUnlimitedEndDateForm)
    reason = TextAreaField(u"Grund", [DataRequired()])

class UserMoveOutForm(Form):
    date = DateField(u"Auszug am", [DataRequired()])
    comment = TextAreaField(u"Kommentar")

class NetDeviceChangeMacForm(Form):
    mac = TextField(u"MAC", [
        Regexp(regex=NetDevice.mac_regex, message=u"MAC ist ungültig!")])

class UserSelectGroupForm(Form):
    group_type = SelectField(u"Typ",
        [DataRequired(message=u"Typ?")],
        coerce=str,
        choices=[('prop', u"Eigenschaft"), ('traff', u"Traffic")])
    group = LazyLoadSelectField(u"Gruppe",
        [DataRequired(message=u"Gruppe angeben!")],
        coerce=str,
        choices=[],
        conditions=["group_type"],
        data_endpoint="user.json_groups")
