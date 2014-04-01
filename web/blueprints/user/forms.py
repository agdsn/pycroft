# -*- coding: utf-8 -*-


from flask.ext.wtf import Form
from wtforms import TextField, TextAreaField, BooleanField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import Required, EqualTo, Regexp
from pycroft.model.user import User
from pycroft.model.host import Host, NetDevice
from pycroft.model.property import PropertyGroup
from pycroft.model.finance import Semester
from web.blueprints.dormitories.forms import dormitory_query
from web.form.fields import DatePickerField
from datetime import datetime


def user_query():
    return User.q.order_by(User.id)


def host_query():
    return Host.q.order_by(Host.id)

def group_query():
    return PropertyGroup.q.order_by(PropertyGroup.name)

def semester_query():
    return Semester.q.order_by(Semester.name)


class UserSearchForm(Form):
    userid = TextField(u"Nutzerid")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")


from web.form.fields import LazyLoadSelectField

class UserEditNameForm(Form):
    name = TextField(u"Name", [Required(message=u"Name wird benötigt!")])


class UserEditEMailForm(Form):
    email = TextField(u"E-Mail", [Regexp(regex=User.email_regex,
                                  message=u"E-Mail-Adresse ist ungültig!")])

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
    email = TextField(u"E-Mail", [Regexp(regex=User.email_regex,
                                         message=u"E-Mail ist ungueltig!")])
    semester = QuerySelectField(u"aktuelles Semester", get_label="name",
        query_factory=semester_query)


class hostCreateForm(Form):
    name = TextField(u"Name")


class UserLogEntry(Form):
    message = TextAreaField(u"", [Required()])

class UserAddGroupMembership(Form):
    group_id = QuerySelectField(u"Gruppe",get_label='name',query_factory=group_query)
    begin_date = DatePickerField(u"Beginn", [Required()], with_today_button=True, default=datetime.now)
    unlimited = BooleanField(u"Unbegrenzte Dauer", default=False)
    end_date = DatePickerField(u"Ende",with_today_button=True)

class UserEditGroupMembership(Form):
    begin_date = DatePickerField(u"Beginn", [Required()], with_today_button=True, default=datetime.now)
    unlimited = BooleanField(u"Unbegrenzte Mitgliedschaft", default=False)
    end_date = DatePickerField(u"Ende",with_today_button=True)

class UserBlockForm(Form):
    unlimited = BooleanField(u"Unbegrenzte Sperrung", default=False)
    date = DatePickerField(u"Gesperrt bis", with_today_button=True, default=datetime.now)
    reason = TextAreaField(u"Grund")

class UserMoveOutForm(Form):
    date = DatePickerField(u"Auszug am", [Required()], with_today_button=True,
        default=datetime.now)
    comment = TextAreaField(u"Kommentar")

class NetDeviceChangeMacForm(Form):
    mac = TextField(u"MAC", [Regexp(regex=NetDevice.mac_regex,
        message=u"MAC ist ungültig!")])
