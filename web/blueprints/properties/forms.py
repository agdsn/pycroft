# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.


from flask.ext.wtf import Form
from wtforms.validators import DataRequired, Regexp, NumberRange
from web.form.fields.core import TextField


class TrafficGroupForm(Form):
    name = TextField(u"Gruppenname", [
        DataRequired(u"Name?"),
        Regexp(u"^[a-zA-Z0-9äöüÄÖÜ ]{3,}$",
               message=u"Namen ohne Sonderzeichen und mindestens 3 Buchstaben"
                       u" eingeben! (RegEx: ^[a-zA-Z0-9äöüÄÖÜ ]{3,}$)")
    ])
    traffic_limit = TextField(u"Traffic Limit (GB)", [
        DataRequired(u"Wie viel GB?"),
        NumberRange(0, None, u"Muss eine natürliche Zahl sein!")
    ])


class PropertyGroupForm(Form):
    name = TextField(u"Gruppenname", [
        DataRequired(u"Name?"),
        Regexp(u"^[a-zA-Z0-9äöüÄÖÜ ]{3,}$",
               message=u"Namen ohne Sonderzeichen und mindestens 3 Buchstaben"
                       u" eingeben! (RegEx: ^[a-zA-Z0-9äöüÄÖÜ ]{3,}$)")
    ])
