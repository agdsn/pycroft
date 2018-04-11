# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import re
from difflib import SequenceMatcher

from flask import url_for
from flask_wtf import FlaskForm as Form
from wtforms.validators import (
    Regexp, NumberRange, ValidationError, DataRequired, Email, Optional)
from wtforms.widgets import HTMLString

from pycroft.helpers.net import mac_regex
from pycroft.model.facilities import Room
from pycroft.model.finance import Semester
from pycroft.model.host import Host, Interface
from pycroft.model.user import PropertyGroup, User, TrafficGroup
from web.blueprints.facilities.forms import building_query
from web.blueprints.properties.forms import trafficgroup_query, \
    propertygroup_query
from web.form.fields.core import TextField, TextAreaField, BooleanField, \
    QuerySelectField, DateField, SelectField, FormField
from web.form.fields.custom import LazyLoadSelectField
from web.form.fields.validators import OptionalIf


def user_query():
    return User.q.order_by(User.id)


def host_query():
    return Host.q.order_by(Host.id)


def group_query():
    return PropertyGroup.q.order_by(PropertyGroup.name)


def semester_query():
    return Semester.q.order_by(Semester.name)


def validate_unique_login(form, field):
    if User.q.filter_by(login=field.data).first():
        raise ValidationError(u"Nutzerlogin schon vergeben!")


def validate_unique_name(form, field):
    if not form.force.data:
        room = Room.q.filter_by(number=form.room_number.data,
                                level=form.level.data,
                                building=form.building.data).one()

        if room is not None:
            users = User.q.filter_by(room_id=room.id).all()

            for user in users:
                ratio = SequenceMatcher(None, field.data, user.name).ratio()

                if ratio > 0.6:
                    raise ValidationError(
                        HTMLString("* " + u"Ein ähnlicher Benutzer existiert bereits in diesem Zimmer!" +
                                   "<br/>Nutzer: " +
                                   "<a target=\"_blank\" href=\"" +
                                   url_for("user.user_show", user_id=user.id) +
                                   "\">" + user.name + "</a>"))


def validate_unique_email(form, field):
    user = User.q.filter_by(email=field.data).first()
    if user is not None and not form.force.data:
        raise ValidationError(
            HTMLString("* " + "E-Mail bereits in Verwendung!<br/>Nutzer: " +
                       "<a target=\"_blank\" href=\"" +
                       url_for("user.user_show", user_id=user.id) +
                       "\">" + user.name + "</a>"))


def validate_unique_mac(form, field):
    if re.match(mac_regex, field.data):
        interface_existing = Interface.q.filter_by(mac=field.data).first()

        if interface_existing is not None and not form.annex.data:
            owner = interface_existing.host.owner

            raise ValidationError(
                HTMLString("MAC bereits in Verwendung!<br/>Nutzer: " +
                           "<a target=\"_blank\" href=\"" +
                           url_for("user.user_show", user_id=owner.id) +
                           "#hosts\">" + owner.name + "</a>"))


class UserSearchForm(Form):
    id = TextField(u"Nutzer-ID")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")
    mac = TextField(u"MAC-Adresse")
    ip_address = TextField(u"IP-Adresse")
    trafficgroup_id = QuerySelectField(u"Trafficgruppe",
                                get_label='name',
                                query_factory=trafficgroup_query,
                                allow_blank=True,
                                blank_text=u"<Trafficgruppe>")
    propertygroup_id = QuerySelectField(u"Eigenschaftsgruppe",
                                get_label='name',
                                query_factory=propertygroup_query,
                                allow_blank=True,
                                blank_text=u"<Eigenschaftsgruppe>")
    building_id = QuerySelectField(u"Wohnheim",
                                get_label='short_name',
                                query_factory=building_query,
                                allow_blank=True,
                                blank_text=u"<Wohnheim>")


class UserResetPasswordForm(Form):
    pass


class UserEditNameForm(Form):
    name = TextField(u"Name", [DataRequired(message=u"Name wird benötigt!")])


class UserEditEMailForm(Form):
    email = TextField(u"E-Mail", [Email(u"E-Mail-Adresse ist ungültig!")])


class UserMoveForm(Form):
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


class UserCreateForm(UserMoveForm):
    name = TextField(u"Name", [DataRequired(message=u"Name wird benötigt!"), validate_unique_name])
    login = TextField(u"Login", [
        DataRequired(message=u"Login wird benötigt!"),
        Regexp(regex=User.login_regex, message=u"Login ist ungültig!"),
        validate_unique_login])
    mac = TextField(u"MAC", [
        Regexp(regex=mac_regex, message=u"MAC ist ungültig!"),
        validate_unique_mac])
    email = TextField(u"E-Mail", [Email(message=u"E-Mail ist ungueltig!"),
                                  Optional(), validate_unique_email])
    annex = BooleanField(u"Host annketieren", [Optional()])
    force = BooleanField(u"* Hinweise ignorieren", [Optional()])


class UserMoveBackInForm(UserMoveForm):
    mac = TextField(u"MAC", [
        Regexp(regex=mac_regex, message=u"MAC ist ungültig!")])


class HostCreateForm(Form):
    name = TextField(u"Name", [DataRequired(u"Der Host benötigt einen Namen!")])


class UserLogEntry(Form):
    message = TextAreaField(u"", [DataRequired()])


class OptionallyUnlimitedEndDateForm(Form):
    unlimited = BooleanField(u"Unbegrenzte Dauer", default=False)
    date = DateField(u"Ende", [OptionalIf("unlimited")])


class UserAddGroupMembership(Form):
    group = QuerySelectField(u"Gruppe", get_label='name',
                             query_factory=group_query)
    begins_at = DateField(u"Beginn", [DataRequired()])
    ends_at = FormField(OptionallyUnlimitedEndDateForm)


class UserEditGroupMembership(Form):
    begins_at = DateField(u"Beginn", [DataRequired()])
    ends_at = FormField(OptionallyUnlimitedEndDateForm)


class UserSuspendForm(Form):
    ends_at = FormField(OptionallyUnlimitedEndDateForm)
    reason = TextAreaField(u"Grund", [DataRequired()])


class UserMoveOutForm(Form):
    # when = DateField(u"Auszug am", [DataRequired()])
    comment = TextAreaField(u"Kommentar")


class InterfaceChangeMacForm(Form):
    mac = TextField(u"MAC", [
        Regexp(regex=mac_regex, message=u"MAC ist ungültig!")])


class UserSelectGroupForm(Form):
    group_type = SelectField(u"Typ",
                             [DataRequired(message=u"Typ?")],
                             coerce=str,
                             choices=[('prop', u"Eigenschaft"),
                                      ('traff', u"Traffic")])
    group = LazyLoadSelectField(u"Gruppe",
                                [DataRequired(message=u"Gruppe angeben!")],
                                coerce=str,
                                choices=[],
                                conditions=["group_type"],
                                data_endpoint="user.json_groups")
