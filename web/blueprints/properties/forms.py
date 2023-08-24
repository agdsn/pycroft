# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from flask_wtf import FlaskForm as Form
from sqlalchemy.orm import Query
from wtforms.validators import DataRequired, Regexp

from pycroft import config
from pycroft.model.user import PropertyGroup
from wtforms_widgets.fields.core import TextField, IntegerField


def property_group_query() -> Query:
    return PropertyGroup.q.order_by(PropertyGroup.id)


def property_group_user_create_query() -> Query:
    return PropertyGroup.q.filter(PropertyGroup.id.in_([
        config.member_group_id,
        config.external_group_id,
    ])).order_by(PropertyGroup.id)


class PropertyGroupForm(Form):
    name = TextField("Gruppenname", [
        DataRequired("Name?"),
        Regexp("^[a-zA-Z0-9äöüÄÖÜ ]{3,}$",
               message="Namen ohne Sonderzeichen und mindestens 3 Buchstaben"
                       " eingeben! (RegEx: ^[a-zA-Z0-9äöüÄÖÜ ]{3,}$)")
    ])
    permission_level = IntegerField("Berechtigungslevel")
