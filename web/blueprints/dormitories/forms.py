# -*- coding: utf-8 -*-


from flask.ext.wtf import Form
from wtforms.validators import Length, Required
from pycroft.model.dormitory import Dormitory
from web.form.fields.core import TextField, BooleanField, TextAreaField, \
    QuerySelectField

from pycroft.helpers.dormitory import sort_dormitories


def dormitory_query():
    return sort_dormitories(Dormitory.q.all())


class RoomForm(Form):
    number = TextField(u"Nummer")
    level = TextField(u"Etage")
    inhabitable = BooleanField(u"Bewohnbar")
    dormitory_id = QuerySelectField(u"Wohnheim",
                                    get_label='short_name',
                                    query_factory=dormitory_query)


class DormitoryForm(Form):
    short_name = TextField(u"Kürzel")
    number = TextField(u"Nummer")
    street = TextField(u"Straße", validators=[Length(min=5)])


class RoomLogEntry(Form):
    message = TextAreaField(u"", [DataRequired()])
