# -*- coding: utf-8 -*-
"""
    web.blueprints.finance
    ~~~~~~~~~~~~~~

    This module defines view functions for /finance

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, redirect, url_for, jsonify,\
    request, flash
from web.blueprints.navigation import BlueprintNavigation
from forms import SemesterCreateForm, JournalLinkForm, JournalImportForm, \
    JournalCreateForm, FinanceaccountCreateForm
from pycroft.lib import finance, config
from datetime import datetime, timedelta
from pycroft.model.finance import Semester, Journal, JournalEntry
from pycroft.model.session import session
from pycroft.model.user import User
from pycroft.model.finance import FinanceAccount, Transaction
import os
from web.blueprints.access import BlueprintAccess

bp = Blueprint('finance', __name__, )
access = BlueprintAccess(bp, ['finance_show'])
nav = BlueprintNavigation(bp, "Finanzen", blueprint_access=access)

@bp.route('/')
@bp.route('/journals')
@access.require('finance_show')
@nav.navigate(u"Journals")
def journals():
    journals_list = Journal.q.all()
    journal_entries_list = JournalEntry.q.all()

    return render_template('finance/journal_list.html',
                           journals=journals_list,
                           journal_entries=journal_entries_list)


@bp.route('/journals/import', methods=['GET', 'POST'])
@access.require('finance_change')
@nav.navigate(u"Buchungen importieren")
def journal_import():
    #TODO felix_kluge: secure fileupload
    form = JournalImportForm()

    if form.validate_on_submit():
        try:
            finance.import_csv(form.csv_file.data)
            flash(u"Der CSV-Import war erfolgreich!", "success")
        except Exception as error:
            flash(u"Der CSV-Import ist fehlgeschlagen! " + error.message, "error")

    return render_template('finance/journal_import.html',
                           form=form)


@bp.route('/journals/create', methods=['GET', 'POST'])
@access.require('finance_change')
def journal_create():
    form = JournalCreateForm()

    if form.validate_on_submit():
        new_journal = Journal(account=form.name.data,
                              bank=form.bank.data,
                              hbci_url=form.hbci_url.data,
                              last_update=datetime.now(),
                              account_number=form.account_number.data,
                              bank_identification_code=form.bank_identification_code.data)
        session.add(new_journal)
        session.commit()
        return redirect(url_for('.journals'))

    return render_template('finance/journal_create.html',
                           form=form, page_title=u"Journal erstellen")


@bp.route('/journalentry/edit/<int:entryid>', methods=["GET", "POST"])
@access.require('finance_change')
def journalentry_edit(entryid):
    journalentry = JournalEntry.q.get(entryid)
    form = JournalLinkForm()

    if form.validate():
        #finance.simple_transaction()
        pass

    return render_template('finance/journalentry_edit.html',
                           entry=journalentry, form=form)


@bp.route('/accounts')
@nav.navigate(u"Konten")
@access.require('finance_show')
def accounts():
    accounts_list = FinanceAccount.q.all()

    return render_template('finance/accounts_list.html', accounts=accounts_list)


@bp.route('/accounts/create', methods=['GET', 'POST'])
@access.require('finance_change')
def accounts_create():
    form = FinanceaccountCreateForm()

    if form.validate_on_submit():
        # With QuerySelectField the form.data contains a valid Semester object.
        # If no Semester is selected, data will be None.
        new_account = FinanceAccount(name=form.name.data,
                                     type=form.type.data,
                                     semester=form.semester.data)
        session.add(new_account)
        session.commit()
        return redirect(url_for('.accounts'))

    return render_template('finance/accounts_create.html', form=form,
                           page_title=u"Konto erstellen")


@bp.route('/transactions')
@access.require('finance_show')
@nav.navigate(u"Transaktionen")
def transactions():
    transactions_list = Transaction.q.all()

    return render_template('finance/transactions_list.html', transactions=transactions_list)


@bp.route("/semester")
@access.require('finance_show')
@nav.navigate(u"Semesterliste")
def semester_list():
    semesters = Semester.q.order_by(Semester.begin_date.desc()).all()
    return render_template('finance/semester_list.html', semesters=semesters)


@bp.route('/semester/create', methods=("GET", "POST"))
@access.require('finance_change')
def semester_create():
    previous_semester = Semester.q.order_by(Semester.begin_date.desc()).first()
    if previous_semester:
        begin_date_default = previous_semester.end_date + timedelta(1)
        end_date_default = previous_semester.begin_date.replace(
            year=previous_semester.begin_date.year + 1
        ) - timedelta(1)
        premature_begin_date_default = begin_date_default - timedelta(30)
        belated_end_date_default = end_date_default + timedelta(30)
        if begin_date_default.year == end_date_default.year:
            name_default = u'Sommersemester ' + str(begin_date_default.year)
        else:
            name_default = (u'Wintersemester ' + str(begin_date_default.year) +
                            u'/' + str(end_date_default.year))
        form = SemesterCreateForm(
            name=name_default,
            registration_fee=previous_semester.registration_fee,
            regular_membership_fee=previous_semester.regular_membership_fee,
            reduced_membership_fee=previous_semester.reduced_membership_fee,
            overdue_fine=previous_semester.overdue_fine,
            premature_begin_date=premature_begin_date_default,
            begin_date=begin_date_default,
            end_date=end_date_default,
            belated_end_date=belated_end_date_default)
    else:
        form = SemesterCreateForm()
    if form.validate_on_submit():
        finance.create_semester(
            name=form.name.data,
            registration_fee=form.registration_fee.data,
            regular_membership_fee=form.regular_membership_fee.data,
            reduced_membership_fee=form.reduced_membership_fee.data,
            overdue_fine=form.overdue_fine.data,
            premature_begin_date=form.premature_begin_date.data,
            begin_date=form.begin_date.data,
            end_date=form.end_date.data,
            belated_end_date=form.belated_end_date.data)
        return redirect(url_for(".semester_list"))
    return render_template('finance/semester_create.html', form=form)


@bp.route('/json/search_accounts/<string:search_str>')
@access.require('finance_show')
def json_search_accounts(search_str):
    result = session.query(FinanceAccount).filter(FinanceAccount.name.like("%%%s%%" % search_str)).all()

    r = []
    for user in result:
        r.append({"id": user.id, "name": user.name})

    return jsonify({"result": r})
