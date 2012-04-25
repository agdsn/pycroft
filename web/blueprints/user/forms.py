# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.


from flaskext.wtf import Form, TextField, QuerySelectField, PasswordField, \
    DateField, BooleanField
from wtforms.validators import Required, EqualTo, Regexp
from pycroft.model.user import User
from helpers import getRegex


def user_query():
    return User.q.order_by(User.id)


class UserSearchForm(Form):
    userid = TextField(u"Nutzerid")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")


class UserCreateForm(Form):
    name = TextField(u"Name", [Required(message=u"Name?"),
                     Regexp(regex=getRegex("name"),
                     message=u"Name ist ungültig!")])
    login = TextField(u"Login", [Required(message=u"Login?"),
                      Regexp(regex=getRegex("login"),
                             message=u"Login ist ungültig!")])
    mac = TextField(u"MAC", [Regexp(regex=getRegex("mac"),
                                    message=u"MAC ist ungültig!")])
    room_id = TextField(u"Raum ID", [Required(message=u"Raum?"),
                                     Regexp(regex=getRegex("room"),
                                            message=u"Raum ist ungültig!")])
