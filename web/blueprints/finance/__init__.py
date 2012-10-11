# -*- coding: utf-8 -*-
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
    form = SemesterCreateForm()
    if form.validate_on_submit():
        finance.semester_create(name=form.name.data,
        registration_fee=form.registration_fee.data,
        semester_fee=form.semester_fee.data,
        begin_date=form.begin_date.data,
        end_date=form.end_date.data)
        return redirect(url_for(".semester_list"))
    return render_template('finance/semester_create.html', form=form)
