# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.finance
    ~~~~~~~~~~~~~~

    This module defines view functions for /finance

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, redirect, url_for
from web.blueprints.navigation import BlueprintNavigation
from forms import SemesterCreateForm
from pycroft.lib import finance
from datetime import datetime, timedelta
from pycroft.model.finance import Semester

bp = Blueprint('finance', __name__, )
nav = BlueprintNavigation(bp, "Finanzen")


@bp.route('/')
@bp.route('/journals')
@nav.navigate(u"Journale")
def journals():
    return render_template('finance/base.html')


@bp.route('/accounts')
@nav.navigate(u"Konten")
def accounts():
    return render_template('finance/base.html')


@bp.route('/transactions')
@nav.navigate(u"Transaktionen")
def transactions():
    return render_template('finance/base.html')

@bp.route("/semester")
@nav.navigate(u"Semesterliste")
def semester_list():
    return "foo"

@bp.route('/semester/create', methods=("GET", "POST"))
@nav.navigate(u"Erstelle Semester")
def semester_create():
    try:
        previous_semester = Semester.q.order_by(
            Semester.begin_date.desc()
            ).first()
        begin_date_default = previous_semester.end_date
        end_date_default = previous_semester.begin_date.replace(
            year = previous_semester.begin_date.year + 1
            )
        if begin_date_default.year == end_date_default.year:
            name_default = u'Sommersemester ' + str(begin_date_default.year)
        else:
            name_default = (u'Wintersemester ' + str(begin_date_default.year) +
                            u'/' + str(end_date_default.year))
        registration_fee_default = previous_semester.registration_fee
        semester_fee_default = previous_semester.semester_fee
        form = SemesterCreateForm(name=name_default,
                                  registration_fee=registration_fee_default,
                                  semester_fee=semester_fee_default,
                                  begin_date=begin_date_default,
                                  end_date=end_date_default)
    except IndexError:
        form = SemesterCreateForm()
    if form.validate_on_submit():
        finance.semester_create(name=form.name.data,
        registration_fee=form.registration_fee.data,
        semester_fee=form.semester_fee.data,
        begin_date=form.begin_date.data,
        end_date=form.end_date.data)
        print 
        return redirect(url_for(".semester_list"))
    return render_template('finance/semester_create.html', form=form)
