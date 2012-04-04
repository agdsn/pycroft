# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.infrastructure
    ~~~~~~~~~~~~~~

    This module defines view functions for /infrastructure

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flaskext.wtf import Form, TextField, validators
from pycroft.model import dormitory, session

bp = Blueprint('housing', __name__, )


@bp.route('/')
@bp.route('/rooms')
def rooms():
    return render_template('housing/housing_base.html', page_title = u"Räume")

class DormitoryForm(Form):
    short_name = TextField(u"Kürzel")
    number = TextField(u"Nummer")
    street = TextField(u"Straße", validators=[validators.Length(min=5)])

@bp.route('/dormitories')
def dormitories():
    dormi = dormitory.Dormitory.q.all()
    return render_template('housing/dormitory_list.html',
                           page_title = u"Wohnheime", dormitories=dormi)


@bp.route('/dormitories/new', methods=['GET', 'POST'])
def dormitory_new():
    form = DormitoryForm()
    if form.validate_on_submit():
        myDormitory = dormitory.Dormitory(short_name=form.short_name.data,
            street=form.street.data, number=form.number.data)
        session.session.add(myDormitory)
        session.session.commit()
        flash('Haus angelegt', 'success')
        return redirect(url_for('.dormitories'))
    return render_template('housing/dormitory_new.html',
                           page_title = u"Neues Wohnheim", form=form)
