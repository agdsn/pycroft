# -*- coding: utf-8 -*-
"""
    web.blueprints.finance
    ~~~~~~~~~~~~~~

    This module defines view functions for /finance

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, redirect, url_for, jsonify
from web.blueprints.navigation import BlueprintNavigation
from forms import SemesterCreateForm, JournalLinkForm
from pycroft.lib import finance
from datetime import datetime, timedelta
from pycroft.model.finance import Semester, Journal, JournalEntry
from pycroft.model.session import session
from pycroft.model.user import User
from pycroft.model.finance import FinanceAccount

bp = Blueprint('finance', __name__, )
nav = BlueprintNavigation(bp, "Finanzen")


@bp.route('/')
@bp.route('/journals')
@nav.navigate(u"Journale")
def journals():
    journals_list = JournalEntry.q.all()

    return render_template('finance/journal_list.html',
                           journals=journals_list)


@bp.route('/journalentry/edit/<int:entryid>')
def journalentry_edit(entryid):
    journalentry = JournalEntry.q.get(entryid)
    form = JournalLinkForm()

    if form.validate_on_submit():
        #finance.simple_transaction()
        pass

    return render_template('finance/journalentry_edit.html',
                           entry=journalentry, form=form)


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
    semesters = Semester.q.order_by(Semester.begin_date.desc()).all()
    return render_template('finance/semester_list.html', semesters=semesters)


@bp.route('/semester/create', methods=("GET", "POST"))
@nav.navigate(u"Erstelle Semester")
def semester_create():
    previous_semester = Semester.q.order_by(Semester.begin_date.desc()).first()
    if previous_semester:
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
    else:
        form = SemesterCreateForm()
    if form.validate_on_submit():
        finance.create_semester(name=form.name.data,
        registration_fee=form.registration_fee.data,
        semester_fee=form.semester_fee.data,
        begin_date=form.begin_date.data,
        end_date=form.end_date.data)
        return redirect(url_for(".semester_list"))
    return render_template('finance/semester_create.html', form=form)


@bp.route('/json/search_accounts/<string:search_str>')
def json_search_accounts(search_str):
    result = session.query(FinanceAccount).filter(FinanceAccount.name.like("%%%s%%" % search_str)).all()

    r = []
    for user in result:
        r.append({"id": user.id, "name": user.name})

    return jsonify({"result": r})