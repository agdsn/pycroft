# -*- coding: utf-8 -*-


from flaskext.wtf import Form, TextField, QuerySelectField, SelectField,\
    PasswordField, DateField, BooleanField
from wtforms.validators import Required, EqualTo, Regexp
from pycroft.model.user import User
from pycroft.model.hosts import Host, NetDevice
from pycroft.model.dormitory import Room
import pycroft.helpers.user_helper as helpers
from web.blueprints.dormitories.forms import dormitory_query


def user_query():
    return User.q.order_by(User.id)


def host_query():
    return Host.q.order_by(Host.id)


class UserSearchForm(Form):
    userid = TextField(u"Nutzerid")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")


class AjaxSelectField(SelectField):
    def pre_validate(self, form):
        pass


class UserCreateForm(Form):
    name = TextField(u"Name", [Required(message=u"Name?"),
                               Regexp(regex=User.name_regex,
                                   message=u"Name ist ungültig!")])
    login = TextField(u"Login", [Required(message=u"Login?"),
                                 Regexp(regex=User.login_regex,
                                     message=u"Login ist ungültig!")])
    mac = TextField(u"MAC", [Regexp(regex=NetDevice.mac_regex,
        message=u"MAC ist ungültig!")])
    host = TextField(u"Host")
    dormitory_id = QuerySelectField(u"Wohnheim",
        [Required(message=u"Wohnheim?")],
        get_label='short_name',
        query_factory=dormitory_query)
    level = AjaxSelectField(u"Etage",
        [Required(message=u"Etage?")],
        coerce=int, choices=[])
    room_number = AjaxSelectField(u"Raumnummer",
        [Required(message=u"Raum?")],
        coerce=str, choices=[])


class hostCreateForm(Form):
    name = TextField(u"Name")


class userLogEntry(Form):
    message = TextField(u"", [Required()])
