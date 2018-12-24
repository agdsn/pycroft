# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.


from flask_wtf import FlaskForm as Form
from wtforms.validators import Length, DataRequired, NumberRange, Optional
from pycroft.model.facilities import Building
from web.form.base_form import BaseForm
from web.form.fields.core import TextField, BooleanField, TextAreaField, \
    QuerySelectField, IntegerField

from pycroft.helpers.facilities import sort_buildings
from web.form.fields.custom import LazyLoadSelectField, static
from web.form.fields.filters import to_uppercase
from web.form.fields.validators import OptionalIf


def building_query():
    return sort_buildings(Building.q.all())


class SelectRoomForm(BaseForm):
    building = QuerySelectField(u"Wohnheim",
                                [DataRequired(message=u"Wohnheim?")],
                                get_label='short_name',
                                query_factory=building_query)
    level = LazyLoadSelectField(u"Etage",
                                validators=[NumberRange(message=u"Etage?")],
                                coerce=int,
                                choices=[],
                                conditions=["building"],
                                data_endpoint="facilities.json_levels")
    room_number = LazyLoadSelectField(u"Raumnummer",
                                      validators=[
                                          DataRequired(message=u"Raum?")],
                                      coerce=str,
                                      choices=[],
                                      conditions=["building", "level"],
                                      data_endpoint="facilities.json_rooms")


class SelectRoomFormOptional(BaseForm):
    building = QuerySelectField(u"Wohnheim",
                                [Optional()],
                                get_label='short_name',
                                query_factory=building_query,
                                allow_blank=True)
    level = LazyLoadSelectField(u"Etage",
                                validators=[
                                    OptionalIf('building', invert=True),
                                    NumberRange(message=u"Etage?")],
                                coerce=int,
                                choices=[],
                                conditions=["building"],
                                data_endpoint="facilities.json_levels")
    room_number = LazyLoadSelectField(u"Raumnummer",
                                      validators=[
                                          OptionalIf('level', invert=True)],
                                      coerce=str,
                                      choices=[],
                                      conditions=["building", "level"],
                                      data_endpoint="facilities.json_rooms")


class CreateRoomForm(Form):
    building = QuerySelectField("Wohnheim",
                                get_label='short_name',
                                query_factory=building_query)
    level = IntegerField("Etage")
    number = TextField("Nummer")
    inhabitable = BooleanField("Bewohnbar", validators=[Optional()])


class EditRoomForm(Form):
    building = static(TextField("Wohnheim"))
    level = static(IntegerField("Etage"))
    number = TextField("Nummer")
    inhabitable = BooleanField("Bewohnbar", validators=[Optional()])


class BuildingForm(Form):
    short_name = TextField(u"Kürzel")
    number = TextField(u"Nummer")
    street = TextField(u"Straße", validators=[Length(min=5)])


class RoomLogEntry(Form):
    message = TextAreaField(u"", [DataRequired()])


class PatchPortForm(SelectRoomForm):
    name = TextField(label="Name", validators=[DataRequired()], filters=[to_uppercase])
    switch_room = static(TextField(label="Switchraum"))

    _order = ("name","switch_room")
