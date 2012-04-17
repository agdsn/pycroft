# -*- coding: utf-8 -*-


from flaskext.wtf import Form, TextField, QuerySelectField, PasswordField, DateField
from wtforms.validators import Required, EqualTo
from pycroft.model.dormitory import Dormitory


def dormitory_query():
    return Dormitory.q.order_by(Dormitory.short_name)

class UserCreateForm(Form):
    name = TextField(u"Name")
    login = TextField(u"Login")
    room_id = TextField(u"Raum ID")
    registration_date = DateField(u"Datum")
    password = PasswordField(u"Passwort", [Required(), EqualTo('confirm', message='Passwörter müssen übereinstimmen')])
    confirm = PasswordField(u"nochmal Passwort")