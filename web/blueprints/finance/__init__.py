# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.finance
    ~~~~~~~~~~~~~~

    This module defines view functions for /finance

    :copyright: (c) 2012 by AG DSN.
"""
from datetime import timedelta
from itertools import groupby
from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request,
    url_for)
from flask.ext.login import current_user
from sqlalchemy import func, or_, Text, cast
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from pycroft._compat import imap
from pycroft.helpers.i18n import localized
from pycroft.lib import finance
from pycroft.lib.finance import get_typed_splits
from pycroft.model.finance import Semester, Journal, JournalEntry, Split
from pycroft.model.session import session
from pycroft.model.user import User
from pycroft.model.finance import FinanceAccount, Transaction
from web.blueprints.access import BlueprintAccess
from web.blueprints.finance.forms import (
    SemesterCreateForm, JournalEntryEditForm, JournalImportForm,
    JournalCreateForm, FinanceAccountCreateForm, TransactionCreateForm)
from web.blueprints.navigation import BlueprintNavigation
from web.template_filters import date_filter, money_filter, datetime_filter
from web.template_tests import privilege_check


bp = Blueprint('finance', __name__)
access = BlueprintAccess(bp, required_properties=['finance_show'])
nav = BlueprintNavigation(bp, "Finanzen", blueprint_access=access)


@bp.route('/')
@bp.route('/journals')
@bp.route('/journals/list')
@nav.navigate(u"Journals")
def journals_list():
    return render_template('finance/journals_list.html')


@bp.route('/journals/list/json')
def journals_list_json():
    return jsonify(items=[
        {
            'name': journal.name,
            'bank': journal.bank,
            'ktonr': journal.account_number,
            'blz': journal.routing_number,
            'iban': journal.iban,
            'bic': journal.bic,
            'kto': {
                'href': url_for('.accounts_show',
                                account_id=journal.finance_account_id),
                'title': 'Konto anzeigen',
                'btn_class': 'btn-primary'
            },
            'hbci': journal.hbci_url,
            'change_date': ''.format(journal.last_update)
        } for journal in Journal.q.all()])


@bp.route('/journals/entries/json')
def journals_entries_json():
    return jsonify(items=[
        {
            'journal': entry.journal.name,
            'valid_on': date_filter(entry.valid_on),
            'amount': money_filter(entry.amount),
            'description': entry.description,
            'original_description': entry.original_description,
            'ktonr': entry.other_account_number,
            # 'blz': entry.other_bank,   # todo revisit. wuzdat? dunno…
            'name': entry.other_name,
            'actions': ([{
                             'href': url_for('.journals_entries_edit',
                                             journal_id=entry.journal_id,
                                             entry_id=entry.id),
                             'title': '',
                             'btn_class': 'btn-primary',
                             'icon': 'glyphicon-pencil'
                         }] if privilege_check(current_user,
                                               'finance_change') else []),
        } for entry in JournalEntry.q.filter(
            JournalEntry.transaction_id == None
        ).order_by(JournalEntry.valid_on).all()])


@bp.route('/journals/import', methods=['GET', 'POST'])
@access.require('finance_change')
@nav.navigate(u"Buchungen importieren")
def journals_import():
    form = JournalImportForm()
    if form.validate_on_submit():
        try:
            finance.import_journal_csv(
                form.csv_file.data, form.expected_balance.data)
            session.commit()
            flash(u"Der CSV-Import war erfolgreich!", "success")
        except finance.CSVImportError as e:
            session.rollback()
            message = u"Der CSV-Import ist fehlgeschlagen: {0}"
            flash(message.format(e.message), "error")

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


@bp.route('/journals/<int:journal_id>/entries/<int:entry_id>',
          methods=["GET", "POST"])
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
            author=current_user, valid_on=entry.valid_on)
        entry.description = form.description.data
        session.add(entry)
        session.commit()

        return redirect(url_for('.journals_list'))

    return render_template(
        'finance/journals_entries_edit.html',
        entry=entry, form=form
    )


@bp.route('/accounts/')
@bp.route('/accounts/list')
@nav.navigate(u"Konten")
def accounts_list():
    accounts_by_type = dict(imap(
        lambda t: (t[0], list(t[1])),
        groupby(
            FinanceAccount.q.outerjoin(User).filter(User.id == None)
            .order_by(FinanceAccount.type).all(),
            lambda a: a.type
        )
    ))
    return render_template(
        'finance/accounts_list.html', accounts=accounts_by_type
    )


@bp.route('/accounts/<int:account_id>')
def accounts_show(account_id):
    account = FinanceAccount.q.filter(FinanceAccount.id == account_id).one()
    try:
        user = User.q.filter_by(finance_account_id=account.id).one()
    except NoResultFound:
        user = None
    except MultipleResultsFound:
        user = User.q.filter_by(finance_account_id=account.id).first()
        flash(u"Es existieren mehrere Nutzer, die mit diesem Konto"
              u" verbunden sind!", "warning")

    return render_template(
        'finance/accounts_show.html',
        account=account, user=user, balance=account.balance,
        json_url=url_for('.accounts_show_json', account_id=account_id),
        footer=[{'title': 'Saldo', 'colspan': 3},
                {'title': money_filter(account.balance)}]
    )


@bp.route('/accounts/<int:account_id>/json')
def accounts_show_json(account_id):
    inverted = False
    limit = request.args.get('limit', None, type=int)
    offset = request.args.get('offset', 0, type=int)
    sort_by = request.args.get('sort')
    sort_order = request.args.get('order')
    total = Split.q.join(Transaction).filter(Split.account_id == account_id).count()

    return jsonify(
        items={
            "total": total,
            "rows": [
                {
                    'id': i+offset,
                    'posted_at': datetime_filter(split.transaction.posted_at),
                    #'posted_by': (split.transaction.author.id, split.transaction.author.name),
                    'valid_on': date_filter(split.transaction.valid_on),
                    'description': {
                        'href': url_for(
                            "finance.transactions_show",
                            transaction_id=split.transaction_id
                        ),
                        'title': localized(split.transaction.description)
                    },
                    'amount': money_filter(split.amount),
                    'row_positive': (split.amount > 0) is not inverted
                } for i, split in enumerate(
                    Split.q.join(Transaction)
                        .filter(Split.account_id == account_id)
                        .order_by(Transaction.valid_on).
                        offset(offset).
                        limit(limit))
                ]
        })


@bp.route('/transactions/<int:transaction_id>')
def transactions_show(transaction_id):
    transaction = Transaction.q.get(transaction_id)
    if transaction is None:
        abort(404)
    return render_template(
        'finance/transactions_show.html',
        transaction=transaction
    )


@bp.route('/transactions/<int:transaction_id>/json')
def transactions_show_json(transaction_id):
    inverted = False
    return jsonify(items=[
        {
            'account': {
                'href': url_for(".accounts_show", account_id=split.account_id),
                'title': localized(split.account.name)
            },
            'amount': money_filter(split.amount),
            'row_positive': (split.amount > 0) is not inverted
        } for split in Transaction.q.get(transaction_id).splits])


@bp.route('/transactions/create', methods=['GET', 'POST'])
@nav.navigate(u'Buchung erstellen')
@access.require('finance_change')
def transactions_create():
    form = TransactionCreateForm()
    if form.validate_on_submit():
        splits = []
        for split_form in form.splits:
            splits.append((
                FinanceAccount.q.get(split_form.account_id.data),
                split_form.amount.data
            ))
        finance.complex_transaction(
            description=form.description.data,
            author=current_user,
            splits=splits,
            valid_on=form.valid_on.data,
        )
        return redirect(url_for('.accounts_list'))
    return render_template(
        'finance/transactions_create.html',
        form=form
    )


@bp.route('/accounts/create', methods=['GET', 'POST'])
@access.require('finance_change')
def accounts_create():
    form = FinanceAccountCreateForm()

    if form.validate_on_submit():
        new_account = FinanceAccount(name=form.name.data, type=form.type.data)
        session.add(new_account)
        session.commit()
        return redirect(url_for('.accounts_list'))

    return render_template('finance/accounts_create.html', form=form,
                           page_title=u"Konto erstellen")


@bp.route("/semesters")
@nav.navigate(u"Semesterliste")
def semesters_list():
    return render_template('finance/semesters_list.html')


@bp.route("/semesters/json")
def semesters_list_json():
    return jsonify(items=[
        {
            'name': localized(semester.name),
            'registration_fee': money_filter(semester.registration_fee),
            'regular_semester_fee': money_filter(
                semester.regular_semester_fee),
            'reduced_semester_fee': money_filter(
                semester.reduced_semester_fee),
            'late_fee': money_filter(semester.late_fee),
            'begins_on': date_filter(semester.begins_on),
            'ends_on': date_filter(semester.ends_on),
        } for semester in Semester.q.order_by(Semester.begins_on.desc()).all()])


@bp.route('/semesters/create', methods=("GET", "POST"))
@access.require('finance_change')
def semesters_create():
    previous_semester = Semester.q.order_by(Semester.begins_on.desc()).first()
    if previous_semester:
        begins_on_default = previous_semester.ends_on + timedelta(1)
        ends_on_default = previous_semester.begins_on.replace(
            year=previous_semester.begins_on.year + 1
        ) - timedelta(1)
        if begins_on_default.year == ends_on_default.year:
            name_default = u'Sommersemester ' + str(begins_on_default.year)
        else:
            name_default = (u'Wintersemester ' + str(begins_on_default.year) +
                            u'/' + str(ends_on_default.year))
        reduced_semester_fee_threshold = previous_semester.reduced_semester_fee_threshold.days
        form = SemesterCreateForm(
            name=name_default,
            registration_fee=previous_semester.registration_fee,
            regular_semester_fee=previous_semester.regular_semester_fee,
            reduced_semester_fee=previous_semester.reduced_semester_fee,
            late_fee=previous_semester.late_fee,
            grace_period=previous_semester.grace_period.days,
            reduced_semester_fee_threshold=reduced_semester_fee_threshold,
            payment_deadline=previous_semester.payment_deadline.days,
            allowed_overdraft=previous_semester.allowed_overdraft,
            begins_on=begins_on_default,
            ends_on=ends_on_default,
        )
    else:
        form = SemesterCreateForm()
    if form.validate_on_submit():
        Semester(
            name=form.name.data,
            registration_fee=form.registration_fee.data,
            regular_semester_fee=form.regular_semester_fee.data,
            reduced_semester_fee=form.reduced_semester_fee.data,
            late_fee=form.late_fee.data,
            grace_period=timedelta(days=form.grace_period.data),
            reduced_semester_fee_threshold=timedelta(days=form.reduced_semester_fee_threshold.data),
            payment_deadline=timedelta(days=form.payment_deadline.data),
            allowed_overdraft=form.allowed_overdraft.data,
            begins_on=form.begins_on.data,
            ends_on=form.ends_on.data,
        )
        return redirect(url_for(".semesters_list"))
    return render_template('finance/semesters_create.html', form=form)


@bp.route('/json/accounts/system')
def json_accounts_system():
    return jsonify(accounts=[
        {
            "account_id": account.id,
            "account_name": localized(account.name),
        } for account in session.query(FinanceAccount).outerjoin(User).filter(
            User.finance_account == None
        ).all()])


@bp.route('/json/accounts/user-search')
def json_accounts_user_search():
    query = request.args['query']
    results = session.query(
        FinanceAccount.id, User.id, User.login, User.name
    ).select_from(User).join(FinanceAccount).filter(
        or_(func.lower(User.name).like(func.lower("%{0}%".format(query))),
            func.lower(User.login).like(func.lower("%{0}%".format(query))),
            cast(User.id, Text).like(u"{0}%".format(query)))
    ).all()
    accounts = [
        {"account_id": account_id,
         "user_id": user_id,
         "user_login": user_login,
         "user_name": user_name}
        for account_id, user_id, user_login, user_name in results
    ]
    return jsonify(accounts=accounts)
