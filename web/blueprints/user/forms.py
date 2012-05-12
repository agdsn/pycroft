# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.


from flaskext.wtf import Form, TextField, QuerySelectField, PasswordField,\
    DateField, BooleanField
from wtforms.validators import Required, EqualTo, Regexp
from pycroft.model.user import User
from pycroft.model.hosts import Host
from pycroft.helpers.user_helper import UserHelper as helpers
from web.blueprints.dormitories.forms import dormitory_query


def user_query():
    return User.q.order_by(User.id)


def host_query():
    return Host.q.order_by(Host.id)


class UserSearchForm(Form):
    userid = TextField(u"Nutzerid")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")


class UserCreateForm(Form):
    name = TextField(u"Name", [Required(message=u"Name?"),
                               Regexp(regex=helpers.getRegex("name"),
                                   message=u"Name ist ungültig!")])
    login = TextField(u"Login", [Required(message=u"Login?"),
                                 Regexp(regex=helpers.getRegex("login"),
                                     message=u"Login ist ungültig!")])
    mac = TextField(u"MAC", [Regexp(regex=helpers.getRegex("mac"),
        message=u"MAC ist ungültig!")])
    host = TextField(u"Host")
    dormitory_id = QuerySelectField(u"Wohnheim", get_label='short_name',
        query_factory=dormitory_query)
    room_number = TextField(u"Raum ID", [Required(message=u"Raum?"),
                                         Regexp(regex=helpersgetRegex("room"),
                                             message=u"Raum ist ungültig!")])


class hostCreateForm(Form):
    name = TextField(u"Name")
