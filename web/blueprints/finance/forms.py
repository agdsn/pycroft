# -*- coding: utf-8 -*-
# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'florian'

from web.form.fields import DatePickerField
from flask.ext.wtf import Form, TextField, IntegerField, QuerySelectField
from pycroft.model.finance import FinanceAccount


def financeaccounts_query():
    return FinanceAccount.q.order_by(FinanceAccount.name)


class SemesterCreateForm(Form):
    name = TextField(u"Semestername")
    registration_fee = IntegerField(u"Anmeldegebühr")
    semester_fee = IntegerField(u"Semesterbeitrag")
    begin_date = DatePickerField(u"Anfang")
    end_date = DatePickerField(u"Ende")


class JournalLinkForm(Form):
    linked_accounts = QuerySelectField(u"Zugehoeriges Konto",
                          get_label='name',
                          query_factory=financeaccounts_query,
                          allow_blank=True)
