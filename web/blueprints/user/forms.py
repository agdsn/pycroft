# -*- coding: utf-8 -*-


from flaskext.wtf import Form, TextField, QuerySelectField, PasswordField, \
    DateField, BooleanField
from wtforms.validators import Required, EqualTo
from pycroft.model.user import User


def user_query():
    return User.q.order_by(User.id)


class UserSearchForm(Form):
    userid = TextField(u"Nutzerid")
    name = TextField(u"Name")
    login = TextField(u"Unix-Login")


class UserCreateForm(Form):
    name = TextField(u"Name")
    login = TextField(u"Login")
    room_id = TextField(u"Raum ID")