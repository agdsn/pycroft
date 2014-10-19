# -*- coding: utf-8 -*-
from datetime import datetime
from flask.ext.wtf import Form
from wtforms.validators import Required, Regexp, NumberRange, ValidationError, \
    DataRequired
from pycroft.model.user import User
from pycroft.model.host import Host, NetDevice
from pycroft.model.property import PropertyGroup
from pycroft.model.finance import Semester
from web.blueprints.dormitories.forms import dormitory_query
from web.form.fields.core import TextField, TextAreaField, BooleanField,\
    QuerySelectField, DateField, SelectField
from web.form.fields.custom import LazyLoadSelectField


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


class UserSearchForm(Form):
    userid = TextField(u"Nutzerid")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")



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
        validators=[NumberRange(message=u"Etage?")],
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
                                     message=u"Login ist ungültig!"),
                                 validate_unique_login])
    mac = TextField(u"MAC", [Regexp(regex=NetDevice.mac_regex,
        message=u"MAC ist ungültig!")])
    host = TextField(u"Host")
    email = TextField(u"E-Mail", [Regexp(regex=User.email_regex,
                                         message=u"E-Mail ist ungueltig!")])
    moved_from_division = BooleanField(u"Umzug aus anderer Sektion")

    already_paid_semester_fee = BooleanField\
        (u"Hat dort bereits für das aktuelle Semester Beitrag bezahlt")


class hostCreateForm(Form):
    name = TextField(u"Name")


class UserLogEntry(Form):
    message = TextAreaField(u"", [Required()])

class UserAddGroupMembership(Form):
    group_id = QuerySelectField(u"Gruppe",get_label='name',query_factory=group_query)
    begin_date = DateField(
        u"Beginn", [Required()], default=datetime.utcnow, today_btn=True,
        today_highlight=True)
    unlimited = BooleanField(u"Unbegrenzte Dauer", default=False)
    end_date = DateField(u"Ende", today_btn=True, today_highlight=True)

class UserEditGroupMembership(Form):
    begin_date = DateField(
        u"Beginn", [Required()], default=datetime.utcnow, today_btn=True,
        today_highlight=True)
    unlimited = BooleanField(u"Unbegrenzte Mitgliedschaft", default=False)
    end_date = DateField(u"Ende", today_btn=True, today_highlight=True)

class UserBlockForm(Form):
    unlimited = BooleanField(u"Unbegrenzte Sperrung", default=False)
    date = DateField(
        u"Gesperrt bis", default=datetime.utcnow, today_btn=True,
        today_highlight=True)
    reason = TextAreaField(u"Grund")

class UserMoveOutForm(Form):
    date = DateField(
        u"Auszug am", [Required()], default=datetime.utcnow, today_btn=True,
        today_highlight=True)
    comment = TextAreaField(u"Kommentar")

class NetDeviceChangeMacForm(Form):
    mac = TextField(u"MAC", [Regexp(regex=NetDevice.mac_regex,
        message=u"MAC ist ungültig!")])

class UserSelectGroupForm(Form):
    group_type = SelectField(u"Typ",
        [DataRequired(message=u"Typ?")],
        coerce=str,
        choices=[('prop', u"Eigenschaft"), ('traff', u"Traffic")])
    group = LazyLoadSelectField(u"Gruppe",
        [DataRequired(message=u"Gruppe angeben!")],
        coerce=str,
        choices=[],
        conditions=["group_type"],
        data_endpoint="user.json_groups")
