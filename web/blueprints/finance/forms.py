# -*- coding: utf-8 -*-
__author__ = 'florian'

from web.form.fields import DatePickerField
from flask.ext.wtf import Form, TextField, IntegerField

class SemesterCreateForm(Form):
    name = TextField(u"Semestername")
    registration_fee = IntegerField(u"Anmeldegebühr")
    semester_fee = IntegerField(u"Semesterbeitrag")
    begin_date = DatePickerField(u"Anfang")
    end_date = DatePickerField(u"Ende")