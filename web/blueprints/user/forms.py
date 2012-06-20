# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.


from flaskext.wtf import Form, TextField, QuerySelectField, SelectField,\
    PasswordField, DateTimeField, BooleanField
from wtforms.validators import Required, EqualTo, Regexp
from pycroft.model.user import User
from pycroft.model.hosts import Host, NetDevice
from pycroft.model.properties import PropertyGroup
from pycroft.model.dormitory import Room
import pycroft.helpers.user_helper as helpers
from web.blueprints.dormitories.forms import dormitory_query
from web.form.fields import DatePickerField


def user_query():
    return User.q.order_by(User.id)


def host_query():
    return Host.q.order_by(Host.id)

def group_query():
    return PropertyGroup.q.order_by(PropertyGroup.name)


class UserSearchForm(Form):
    userid = TextField(u"Nutzerid")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")


class AjaxSelectField(SelectField):
    def pre_validate(self, form):
        pass


class UserCreateForm(Form):
    name = TextField(u"Name", [Required(message=u"Name?"),
                               Regexp(regex=User.name_regex,
                                   message=u"Name ist ungültig!")])
    login = TextField(u"Login", [Required(message=u"Login?"),
                                 Regexp(regex=User.login_regex,
                                     message=u"Login ist ungültig!")])
    mac = TextField(u"MAC", [Regexp(regex=NetDevice.mac_regex,
        message=u"MAC ist ungültig!")])
    host = TextField(u"Host")
    dormitory_id = QuerySelectField(u"Wohnheim",
        [Required(message=u"Wohnheim?")],
        get_label='short_name',
        query_factory=dormitory_query)
    level = AjaxSelectField(u"Etage",
        [Required(message=u"Etage?")],
        coerce=int, choices=[])
    room_number = AjaxSelectField(u"Raumnummer",
        [Required(message=u"Raum?")],
        coerce=str, choices=[])


class hostCreateForm(Form):
    name = TextField(u"Name")


class userLogEntry(Form):
    message = TextField(u"", [Required()])

class UserAddGroupMembership(Form):
    group_id = QuerySelectField(u"Gruppe",get_label='name',query_factory=group_query)
    begin_date = DatePickerField(u"Beginn",with_today_button=True)
    end_date = DatePickerField(u"Ende",with_today_button=True)
