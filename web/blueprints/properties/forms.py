# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from flask_wtf import FlaskForm as Form
from wtforms.validators import DataRequired, Regexp

from pycroft import config
from pycroft.model.user import PropertyGroup
from web.form.fields.core import TextField, IntegerField


def property_group_query():
    return PropertyGroup.q.order_by(PropertyGroup.id)


def property_group_user_create_query():
    return PropertyGroup.q.filter(PropertyGroup.id.in_([
        config.member_group_id,
        config.external_group_id,
        config.cache_group_id
    ])).order_by(PropertyGroup.id)


class PropertyGroupForm(Form):
    name = TextField(u"Gruppenname", [
        DataRequired(u"Name?"),
        Regexp(u"^[a-zA-Z0-9äöüÄÖÜ ]{3,}$",
               message=u"Namen ohne Sonderzeichen und mindestens 3 Buchstaben"
                       u" eingeben! (RegEx: ^[a-zA-Z0-9äöüÄÖÜ ]{3,}$)")
    ])
    permission_level = IntegerField("Berechtigungslevel")
