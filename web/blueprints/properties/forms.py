# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from flask_wtf import FlaskForm as Form
from wtforms.validators import DataRequired, Regexp, NumberRange, ValidationError

from pycroft.model.user import TrafficGroup, PropertyGroup
from web.form.fields.core import TextField, IntegerField
from web.form.fields.custom import IntervalField


def trafficgroup_query():
    return TrafficGroup.q.order_by(TrafficGroup.id)


def propertygroup_query():
    return PropertyGroup.q.order_by(PropertyGroup.id)


class TrafficGroupForm(Form):
    name = TextField(u"Gruppenname", [
        DataRequired(u"Name?"),
        Regexp(u"^[a-zA-Z0-9äöüÄÖÜ ]{3,}$",
               message=u"Namen ohne Sonderzeichen und mindestens 3 Buchstaben"
                       u" eingeben! (RegEx: ^[a-zA-Z0-9äöüÄÖÜ ]{3,}$)")
    ])
    credit_interval = IntervalField(u"Gutschritintervall")
    credit_amount = IntegerField(u"Gutschriftmenge (GiB)", [
        NumberRange(0, None, u"Muss positiv sein!")
    ])
    credit_limit = IntegerField(u"Anspargrenze (GiB)", [
        DataRequired(u"Wie viel GB?"),
        NumberRange(0, None, u"Muss eine natürliche Zahl sein!")
    ])
    initial_credit = IntegerField(u"Initialer Credit (GiB)", [
        NumberRange(0, None, u"Muss positiv sein!")
    ])


class PropertyGroupForm(Form):
    name = TextField(u"Gruppenname", [
        DataRequired(u"Name?"),
        Regexp(u"^[a-zA-Z0-9äöüÄÖÜ ]{3,}$",
               message=u"Namen ohne Sonderzeichen und mindestens 3 Buchstaben"
                       u" eingeben! (RegEx: ^[a-zA-Z0-9äöüÄÖÜ ]{3,}$)")
    ])
