# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.finance
    ~~~~~~~~~~~~~~

    This module defines view functions for /finance

    :copyright: (c) 2012 by AG DSN.
"""
from itertools import imap, groupby, izip_longest, ifilter

from flask import Blueprint, render_template, redirect, url_for, jsonify,\
    request, flash, abort
from sqlalchemy import func, desc, or_
from web.blueprints.navigation import BlueprintNavigation
from forms import SemesterCreateForm, JournalEntryEditForm, JournalImportForm, \
    JournalCreateForm, FinanceAccountCreateForm
from pycroft.lib import finance, config
from datetime import datetime, timedelta
from pycroft.model.finance import Semester, Journal, JournalEntry, Split
from pycroft.model.session import session
from pycroft.model.user import User
from pycroft.model.finance import FinanceAccount, Transaction
import os
import math
from web.blueprints.access import BlueprintAccess

bp = Blueprint('finance', __name__, )
access = BlueprintAccess(bp, ['finance_show'])
nav = BlueprintNavigation(bp, "Finanzen", blueprint_access=access)

@bp.route('/')
@bp.route('/journals')
@bp.route('/journals/list')
@access.require('finance_show')
@nav.navigate(u"Journals")
def journals_list():
    journals = Journal.q.all()

    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 25, type=int)
    order = request.args.get("order", "transaction_date", type=str)


    count = JournalEntry.q.filter(
        JournalEntry.transaction_id == None
    ).count()

    page_count = int(math.ceil(count/float(limit)))

    offset = (page-1)*limit

    journal_entries_list = JournalEntry.q.filter(
        JournalEntry.transaction_id == None
    ).order_by(order).offset(offset).limit(limit)


    return render_template('finance/journals_list.html',
                           journals=journals,
                           journal_entries=journal_entries_list,
                           page=page,
                           page_count=page_count,
                           limit = limit)


@bp.route('/journals/import', methods=['GET', 'POST'])
@access.require('finance_change')
@nav.navigate(u"Buchungen importieren")
def journals_import():
    form = JournalImportForm()
    if form.validate_on_submit():
        try:
            finance.import_journal_csv(form.csv_file.data)
            flash(u"Der CSV-Import war erfolgreich!", "success")
        except Exception as error:
            message = u"Der CSV-Import ist fehlgeschlagen: {0}"
            flash(message.format(error.message), "error")

    return render_template('finance/journals_import.html', form=form)


@bp.route('/journals/create', methods=['GET', 'POST'])
@access.require('finance_change')
def journals_create():
    form = JournalCreateForm()

    if form.validate_on_submit():
        new_journal = Journal(
            name=form.name.data,
            bank=form.bank.data,
            account_number=form.account_number.data,
            routing_number=form.routing_number.data,
            iban=form.iban.data,
            bic=form.bic.data,
            hbci_url=form.hbci_url.data)
        session.add(new_journal)
        session.commit()
        return redirect(url_for('.journals'))

    return render_template('finance/journals_create.html',
                           form=form, page_title=u"Journal erstellen")


@bp.route('/journals/<int:journal_id>/entries/<int:entry_id>', methods=["GET", "POST"])
@access.require('finance_change')
def journals_entries_edit(journal_id, entry_id):
    entry = JournalEntry.q.get(entry_id)
    form = JournalEntryEditForm(obj=entry, journal_name=entry.journal.name)

    if form.validate():
        debit_account = entry.journal.finance_account
        credit_account = FinanceAccount.q.filter(
            FinanceAccount.id == form.finance_account_id.data
        ).one()
        entry.transaction = finance.simple_transaction(
            description=entry.description, debit_account=debit_account,
            credit_account=credit_account, amount=entry.amount,
            author=current_user, valid_date=entry.valid_date)
        entry.description = form.description.data
        session.add(entry)
        session.commit()

        return redirect(url_for('.journals'))

    return render_template(
        'finance/journals_entries_edit.html',
        entry=entry, form=form
    )


@bp.route('/accounts')
@bp.route('/accounts/list')
@nav.navigate(u"Konten")
@access.require('finance_show')
def accounts_list():
    accounts_by_type = dict(imap(
        lambda t: (t[0], list(t[1])),
        groupby(
            FinanceAccount.q .outerjoin(User).filter(User.id == None)
            .order_by(FinanceAccount.type).all(),
            lambda a: a.type
        )
    ))
    return render_template(
        'finance/accounts_list.html', accounts=accounts_by_type
    )


@bp.route('/accounts/<int:account_id>')
@access.require('finance_show')
def accounts_show(account_id):
    account = FinanceAccount.q.filter(FinanceAccount.id == account_id).one()
    splits = (
        Split.q
        .join(Transaction)
        .filter(Split.account_id == account_id)
        .order_by(Transaction.valid_date)
    )
    typed_splits = izip_longest(
        ifilter(lambda s: s.amount > 0, splits),
        ifilter(lambda s: s.amount <= 0, splits)
    )
    balance = sum(imap(lambda s: s.amount, splits))
    return render_template(
        'finance/accounts_show.html',
        account=account, balance=balance,
        splits=splits, typed_splits=typed_splits
    )


@bp.route('/transactions/<int:transaction_id>')
@access.require('finance_show')
def transactions_show(transaction_id):
    transaction = Transaction.q.get(transaction_id)
    if transaction is None:
        abort(404)
    return render_template(
        'finance/transactions_show.html',
        transaction=transaction
    )


@bp.route('/accounts/create', methods=['GET', 'POST'])
@access.require('finance_change')
def accounts_create():
    form = FinanceAccountCreateForm()

    if form.validate_on_submit():
        new_account = FinanceAccount(name=form.name.data, type=form.type.data)
        session.add(new_account)
        session.commit()
        return redirect(url_for('.accounts'))

    return render_template('finance/accounts_create.html', form=form,
                           page_title=u"Konto erstellen")


@bp.route("/semesters")
@access.require('finance_show')
@nav.navigate(u"Semesterliste")
def semesters_list():
    semesters = Semester.q.order_by(Semester.begin_date.desc()).all()
    return render_template('finance/semesters_list.html', semesters=semesters)


@bp.route('/semesters/create', methods=("GET", "POST"))
@access.require('finance_change')
def semesters_create():
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
        Semester(
            name=form.name.data,
            registration_fee=form.registration_fee.data,
            regular_membership_fee=form.regular_membership_fee.data,
            reduced_membership_fee=form.reduced_membership_fee.data,
            overdue_fine=form.overdue_fine.data,
            premature_begin_date=form.premature_begin_date.data,
            begin_date=form.begin_date.data,
            end_date=form.end_date.data,
            belated_end_date=form.belated_end_date.data)
        return redirect(url_for(".semesters_list"))
    return render_template('finance/semesters_create.html', form=form)


@bp.route('/json/accounts/system')
@access.require('finance_show')
def json_accounts_system():
    return jsonify(accounts=map(
        lambda account: {
            "account_id": account.id,
            "account_name": account.name
        },
        session.query(FinanceAccount).outerjoin(User).filter(
            User.finance_account == None
        ).all()
    ))


@bp.route('/json/accounts/user-search')
@access.require('finance_show')
def json_accounts_user_search():
    query = request.args['query']
    return jsonify(accounts=map(
        lambda result: {
            "account_id": result[0],
            "user_id": result[1],
            "user_name": result[2]
        },
        session.query(FinanceAccount.id, User.id, User.name).filter(
            FinanceAccount.id == User.finance_account_id,
            or_(
                func.lower(User.name).like(func.lower("%{0}%".format(query))),
                User.id.like("{0}%".format(query))
            )
        ).all()
    ))
