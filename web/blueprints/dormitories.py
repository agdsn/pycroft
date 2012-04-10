# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.dormitories
    ~~~~~~~~~~~~~~

    This module defines view functions for /dormitories
    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flaskext.wtf import Form, TextField, validators
from pycroft.model import dormitory, session
from web.blueprints import BlueprintNavigation

bp = Blueprint('dormitories', __name__, )
nav = BlueprintNavigation(bp, "Wohnheime")


@bp.route('/')
@nav.navigate(u"Wohnheime")
def dormitories():
    dormitories_list = dormitory.Dormitory.q.all()
    return render_template('dormitories/dormitories_list.html',
        page_title=u"Wohnheime", dormitories=dormitories_list)


class DormitoryForm(Form):
    short_name = TextField(u"Kürzel")
    number = TextField(u"Nummer")
    street = TextField(u"Straße", validators=[validators.Length(min=5)])


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate(u"Neues Wohnheim")
def dormitory_create():
    form = DormitoryForm()
    if form.validate_on_submit():
        myDormitory = dormitory.Dormitory(short_name=form.short_name.data,
            street=form.street.data, number=form.number.data)
        session.session.add(myDormitory)
        session.session.commit()
        flash('Wohnheim angelegt', 'success')
        return redirect(url_for('.dormitories'))
    return render_template('dormitories/dormitory_create.html',
                           page_title=u"Neues Wohnheim", form=form)
