# -*- coding: utf-8 -*-


from flask.ext.wtf import Form, TextField, QuerySelectField, SelectField,\
    PasswordField, DateTimeField, BooleanField, TextAreaField
from wtforms.validators import Required, EqualTo, Regexp
from pycroft.model.user import User
from pycroft.model.hosts import Host, NetDevice
from pycroft.model.properties import PropertyGroup
from web.blueprints.dormitories.forms import dormitory_query
from web.form.fields import DatePickerField
from datetime import datetime


def user_query():
    return User.q.order_by(User.id)


def host_query():
    return Host.q.order_by(Host.id)

def group_query():
    return PropertyGroup.q.order_by(PropertyGroup.name)


class UserSearchForm(Form):
    userid = TextField(u"Nutzerid")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")


from web.form.fields import LazyLoadSelectField

class UserEditNameForm(Form):
    name = TextField(u"Name", [Required(message=u"Name?"),
                               Regexp(regex=User.name_regex,
                                   message=u"Name ist ungültig!")])

class UserMoveForm(Form):
    dormitory = QuerySelectField(u"Wohnheim",
        [Required(message=u"Wohnheim?")],
        get_label='short_name',
        query_factory=dormitory_query)
    level = LazyLoadSelectField(u"Etage",
        validators=[Required(message=u"Etage?")],
        coerce=int,
        choices=[],
        conditions=["dormitory"],
        data_endpoint="user.json_levels")
    room_number = LazyLoadSelectField(u"Raumnummer",
        validators=[Required(message=u"Raum?")],
        coerce=str,
        choices=[],
        conditions=["dormitory", "level"],
        data_endpoint="user.json_rooms")


class UserCreateForm(UserEditNameForm, UserMoveForm):
    login = TextField(u"Login", [Required(message=u"Login?"),
                                 Regexp(regex=User.login_regex,
                                     message=u"Login ist ungültig!")])
    mac = TextField(u"MAC", [Regexp(regex=NetDevice.mac_regex,
        message=u"MAC ist ungültig!")])
    host = TextField(u"Host")


class hostCreateForm(Form):
    name = TextField(u"Name")


class userLogEntry(Form):
    message = TextAreaField(u"", [Required()])

class UserAddGroupMembership(Form):
    group_id = QuerySelectField(u"Gruppe",get_label='name',query_factory=group_query)
    begin_date = DatePickerField(u"Beginn", [Required()], with_today_button=True, default=datetime.now)
    end_date = DatePickerField(u"Ende",with_today_button=True)
