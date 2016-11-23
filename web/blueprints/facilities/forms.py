# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.


from flask_wtf import FlaskForm as Form
from wtforms.validators import Length, DataRequired
from pycroft.model.facilities import Building
from web.form.fields.core import TextField, BooleanField, TextAreaField, \
    QuerySelectField

from pycroft.helpers.facilities import sort_buildings


def building_query():
    return sort_buildings(Building.q.all())


class RoomForm(Form):
    number = TextField(u"Nummer")
    level = TextField(u"Etage")
    inhabitable = BooleanField(u"Bewohnbar")
    building_id = QuerySelectField(u"Wohnheim",
                                    get_label='short_name',
                                    query_factory=building_query)


class BuildingForm(Form):
    short_name = TextField(u"Kürzel")
    number = TextField(u"Nummer")
    street = TextField(u"Straße", validators=[Length(min=5)])


class RoomLogEntry(Form):
    message = TextAreaField(u"", [DataRequired()])
