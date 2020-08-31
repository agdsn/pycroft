# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from flask import url_for
from flask_wtf import FlaskForm as Form
from wtforms.validators import Length, DataRequired, NumberRange, Optional
from pycroft.model.facilities import Building
from wtforms_widgets.base_form import BaseForm
from wtforms_widgets.fields.core import TextField, BooleanField, TextAreaField, \
    QuerySelectField, IntegerField


from pycroft.helpers.facilities import sort_buildings
from wtforms_widgets.fields.custom import LazyLoadSelectField, static
from wtforms_widgets.fields.filters import to_uppercase, empty_to_none
from wtforms_widgets.fields.validators import OptionalIf


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
    vo_suchname = TextField("VO Nummer", validators=[Optional()], filters=[empty_to_none])


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
