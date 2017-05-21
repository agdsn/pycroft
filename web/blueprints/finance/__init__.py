# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.finance
    ~~~~~~~~~~~~~~

    This module defines view functions for /finance

    :copyright: (c) 2012 by AG DSN.
"""
from datetime import timedelta, datetime
from functools import partial
from itertools import groupby, zip_longest, chain
from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request,
    url_for)
from flask_login import current_user
from sqlalchemy import func, or_, Text, cast
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from pycroft.helpers.i18n import localized
from pycroft.lib import finance
from pycroft.lib.finance import get_typed_splits
from pycroft.model.finance import (
    Semester, BankAccount, BankAccountActivity, Split)
from pycroft.model.session import session
from pycroft.model.user import User
from pycroft.model.finance import Account, Transaction
from web.blueprints.access import BlueprintAccess
from web.blueprints.finance.forms import (
    AccountCreateForm, BankAccountCreateForm, BankAccountActivityEditForm,
    BankAccountActivitiesImportForm, SemesterCreateForm, TransactionCreateForm)
from web.blueprints.finance.tables import FinanceTable, FinanceTableSplitted
from web.blueprints.navigation import BlueprintNavigation
from web.template_filters import date_filter, money_filter, datetime_filter
from web.template_tests import privilege_check
from web.templates import page_resources
from web.blueprints.helpers.api import json_agg_core
from web.blueprints.helpers.finance import build_transactions_query

from sqlalchemy.sql.expression import literal_column, func, select, Join


bp = Blueprint('finance', __name__)
access = BlueprintAccess(bp, required_properties=['finance_show'])
nav = BlueprintNavigation(bp, "Finanzen", blueprint_access=access)


@bp.route('/')
@bp.route('/bank-accounts')
@bp.route('/bank-accounts/list')
@nav.navigate(u"Bankkonten")
def bank_accounts_list():
    return render_template('finance/bank_accounts_list.html')


@bp.route('/bank-accounts/list/json')
def bank_accounts_list_json():
    return jsonify(items=[
        {
            'name': bank_account.name,
            'bank': bank_account.bank,
            'ktonr': bank_account.account_number,
            'blz': bank_account.routing_number,
            'iban': bank_account.iban,
            'bic': bank_account.bic,
            'kto': {
                'href': url_for('.accounts_show',
                                account_id=bank_account.account_id),
                'title': 'Konto anzeigen',
                'btn_class': 'btn-primary'
            },
            'change_date': ''.format(bank_account.last_updated_at)
        } for bank_account in BankAccount.q.all()])


@bp.route('/bank-accounts/activities/json')
def bank_accounts_activities_json():
    return jsonify(items=[
        {
            'bank_account': activity.bank_account.name,
            'valid_on': date_filter(activity.valid_on),
            'amount': money_filter(activity.amount),
            'reference': activity.reference,
            'original_reference': activity.original_reference,
            'ktonr': activity.other_account_number,
            # 'blz': activity.other_bank,   # todo revisit. wuzdat? dunno…
            'name': activity.other_name,
            'actions': ([{
                'href': url_for(
                    '.bank_account_activities_edit',
                    activity_id=activity.id),
                'title': '',
                'btn_class': 'btn-primary',
                'icon': 'glyphicon-pencil'
            }]
                        if privilege_check(current_user, 'finance_change')
                        else []),
        } for activity in BankAccountActivity.q.filter(
            BankAccountActivity.transaction_id == None
        ).order_by(BankAccountActivity.valid_on).all()])


@bp.route('/bank-accounts/import', methods=['GET', 'POST'])
@access.require('finance_change')
@nav.navigate(u"Bankkontobewegungen importieren")
def bank_accounts_import():
    form = BankAccountActivitiesImportForm()
    if form.validate_on_submit():
        try:
            finance.import_bank_account_activities_csv(
                form.csv_file.data, form.expected_balance.data)
            session.commit()
            flash(u"Der CSV-Import war erfolgreich!", "success")
        except finance.CSVImportError as e:
            session.rollback()
            message = u"Der CSV-Import ist fehlgeschlagen: {0}"
            flash(message.format(e.message), "error")

    return render_template('finance/bank_accounts_import.html', form=form)


@bp.route('/bank-accounts/create', methods=['GET', 'POST'])
@access.require('finance_change')
def bank_accounts_create():
    form = BankAccountCreateForm()

    if form.validate_on_submit():
        new_bank_account = BankAccount(
            name=form.name.data,
            bank=form.bank.data,
            account_number=form.account_number.data,
            routing_number=form.routing_number.data,
            iban=form.iban.data,
            bic=form.bic.data,
            account=Account(name=form.name.data, type='BANK_ASSET'),
        )
        session.add(new_bank_account)
        session.commit()
        return redirect(url_for('.bank_accounts'))

    return render_template('finance/bank_accounts_create.html',
                           form=form, page_title=u"Bankkonto erstellen")


@bp.route('/bank-account-activities/<activity_id>',
          methods=["GET", "POST"])
@access.require('finance_change')
def bank_account_activities_edit(activity_id):
    activity = BankAccountActivity.q.get(activity_id)
    print(activity_id)
    form = BankAccountActivityEditForm(
        obj=activity, bank_account_name=activity.bank_account.name)

    if form.validate():
        debit_account = activity.bank_account.account
        credit_account = Account.q.filter(
            Account.id == form.account_id.data
        ).one()
        transaction = finance.simple_transaction(
            description=form.description.data, debit_account=debit_account,
            credit_account=credit_account, amount=activity.amount,
            author=current_user, valid_on=activity.valid_on)
        activity.split = next(split for split in transaction.splits
                              if split.account_id == debit_account.id)
        session.add(activity)
        session.commit()

        return redirect(url_for('.bank_accounts_list'))

    return render_template('finance/bank_account_activities_edit.html',
                           form=form)


@bp.route('/accounts/')
@bp.route('/accounts/list')
@nav.navigate(u"Konten")
def accounts_list():
    accounts_by_type = {
        t[0]: list(t[1])
        for t in groupby(
            Account.q.outerjoin(User).filter(User.id == None)
            .order_by(Account.type).all(),
            lambda a: a.type
        )
    }
    return render_template(
        'finance/accounts_list.html', accounts=accounts_by_type
    )


@bp.route('/accounts/<int:account_id>/balance/json')
def balance_json(account_id):
    balance_json = (select([Transaction.valid_on,
                            func.sum(Split.amount).over(
                                order_by=Transaction.valid_on).label("balance")
                            ])
                    .select_from(
                        Join(Split, Transaction,
                             Split.transaction_id==Transaction.id))
                    .where(Split.account_id == account_id))

    res = session.execute(json_agg_core(balance_json)).first()[0]
    return jsonify(items=res)


@bp.route('/accounts/<int:account_id>')
def accounts_show(account_id):
    account = Account.q.get(account_id)
    try:
        user = User.q.filter_by(account_id=account.id).one()
    except NoResultFound:
        user = None
    except MultipleResultsFound:
        user = User.q.filter_by(account_id=account.id).first()
        flash(u"Es existieren mehrere Nutzer, die mit diesem Konto"
              u" verbunden sind!", "warning")

    _table_kwargs = {
        'data_url': url_for("finance.accounts_show_json", account_id=account_id),
        'saldo': account.balance,
    }

    page_resources.link_script(
        url_for("static", filename="libs/d3/d3.min.js"))
    return render_template(
        'finance/accounts_show.html',
        account=account, user=user, balance=account.balance,
        balance_json_url=url_for('.balance_json', account_id=account_id),
        finance_table_regular=FinanceTable(**_table_kwargs),
        finance_table_splitted=FinanceTableSplitted(**_table_kwargs),
    )


def _format_row(split, style, prefix=None):
    row = {
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
        'amount': {
            'value': money_filter(split.amount),
            'is_positive': (split.amount > 0) ^ (style == "inverted"),
        },
        'row_positive': (split.amount > 0) ^ (style == "inverted"),
    }
    if prefix is None:
        return row
    return {'{}_{}'.format(prefix, key): val for key, val in row.items()}


def _prefixed_merge(a, prefix_a, b, prefix_b):
    result = {}
    result.update(**{'{}_{}'.format(prefix_a, k): v
                     for k, v in a.items()})
    result.update(**{'{}_{}'.format(prefix_b, k): v
                     for k, v in b.items()})
    return result


@bp.route('/accounts/<int:account_id>/json')
def accounts_show_json(account_id):
    style = request.args.get('style')
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int)
    sort_by = request.args.get('sort', default="valid_on")
    sort_order = request.args.get('order', default="desc")
    search = request.args.get('search')
    splitted = request.args.get('splitted', default=False, type=bool)
    if sort_by.startswith("soll_") or sort_order.startswith("haben_"):
        sort_by = '_'.join(sort_by.split('_')[1:])

    account = Account.q.get(account_id) or abort(404)

    total = Split.q.join(Transaction).filter(Split.account == account).count()

    build_this_query = partial(build_transactions_query,
                               account=account, search=search, sort_by=sort_by,
                               sort_order=sort_order, offset=offset, limit=limit)

    def rows_from_query(query):
        # iterating over `query` executes it
        return [_format_row(split, style) for split in query]

    if splitted:
        rows_pos = rows_from_query(build_this_query(positive=True))
        rows_neg = rows_from_query(build_this_query(positive=False))

        _keys = ['posted_at', 'valid_on', 'description', 'amount']
        _filler = {key: None for key in chain(('soll_'+key for key in _keys),
                                              ('haben_'+key for key in _keys))}

        rows = [
            _prefixed_merge(split_pos, 'soll', split_neg, 'haben')
            for split_pos, split_neg in zip_longest(rows_pos, rows_neg, fillvalue=_filler)
        ]
    else:
        query = build_this_query()
        rows = rows_from_query(query)

    items = {'total': total, 'rows': rows}

    return jsonify(
        name=account.name,
        items=items
    )


@bp.route('/transactions/<int:transaction_id>')
def transactions_show(transaction_id):
    transaction = Transaction.q.get(transaction_id)
    if transaction is None:
        abort(404)
    return render_template(
        'finance/transactions_show.html',
        transaction=transaction,
        get_transaction_type=finance.get_transaction_type
    )


@bp.route('/transactions/<int:transaction_id>/json')
def transactions_show_json(transaction_id):
    transaction = Transaction.q.get(transaction_id)
    return jsonify(
        description=transaction.description,
        items=[
        {
            'account': {
                'href': url_for(".accounts_show", account_id=split.account_id),
                'title': localized(split.account.name)
            },
            'amount': money_filter(split.amount),
            'row_positive': split.amount > 0
        } for split in transaction.splits])


@access.require('finance_show')
@bp.route('/transactions')
def transactions_all():
    page_resources.link_script(
        url_for("static", filename="libs/d3/d3.min.js"))
    page_resources.link_script(
        url_for("static", filename="libs/crossfilter/crossfilter.min.js"))
    page_resources.link_script(
        url_for("static", filename="libs/dcjs/dc.min.js"))
    return render_template('finance/transactions_overview.html',
                           args=request.args)


@access.require('finance_show')
@bp.route('/transactions/json')
def transactions_all_json():
    lower = request.args.get('after', "")
    upper = request.args.get('before', "")
    filter = request.args.get('filter', "nonuser")
    if filter == "nonuser":
        non_user_transactions = (select([Split.transaction_id])
                                 .select_from(
                                    Join(Split, User,
                                         (User.account_id == Split.account_id),
                                         isouter=True))
                                 .group_by(Split.transaction_id)
                                 .having(func.bool_and(User.id == None))
                                 .alias("nut"))

        tid = literal_column("nut.transaction_id")
        transactions = non_user_transactions.join(Transaction,
                                                  Transaction.id == tid)
    else:
        transactions = Transaction.__table__

    q = (select([Transaction.id,
                 Transaction.valid_on,
                 Split.account_id,
                 Account.type,
                 Split.amount])
         .select_from(transactions
                      .join(Split, Split.transaction_id == Transaction.id)
                      .join(Account, Account.id == Split.account_id)))

    try:
        datetime.strptime(lower, "%Y-%m-%d").date()
    except ValueError:
        not lower or abort(422)
    else:
        q = q.where(Transaction.valid_on >= lower)

    try:
        datetime.strptime(upper, "%Y-%m-%d").date()
    except ValueError:
        not upper or abort(422)
    else:
        q = q.where(Transaction.valid_on <= upper)

    res = session.execute(json_agg_core(q)).fetchone()[0] or []
    return jsonify(items=res)


@bp.route('/transactions/create', methods=['GET', 'POST'])
@nav.navigate(u'Buchung erstellen')
@access.require('finance_change')
def transactions_create():
    form = TransactionCreateForm()
    if form.validate_on_submit():
        splits = []
        for split_form in form.splits:
            splits.append((
                Account.q.get(split_form.account_id.data),
                split_form.amount.data
            ))
        transaction = finance.complex_transaction(
            description=form.description.data,
            author=current_user,
            splits=splits,
            valid_on=form.valid_on.data,
        )
        session.commit()
        return redirect(url_for('.transactions_show',
                                transaction_id=transaction.id))
    return render_template(
        'finance/transactions_create.html',
        form=form
    )


@bp.route('/accounts/create', methods=['GET', 'POST'])
@access.require('finance_change')
def accounts_create():
    form = AccountCreateForm()

    if form.validate_on_submit():
        new_account = Account(name=form.name.data, type=form.type.data)
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
            'finance_link': {'href': url_for(".transactions_all",
                                        filter="all",
                                        after=semester.begins_on,
                                        before=semester.ends_on),
                            'title': 'Finanzübersicht',
                            'icon': 'glyphicon-euro'},
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
        } for account in session.query(Account).outerjoin(User).filter(
            User.account == None
        ).all()])


@bp.route('/json/accounts/user-search')
def json_accounts_user_search():
    query = request.args['query']
    results = session.query(
        Account.id, User.id, User.login, User.name
    ).select_from(User).join(Account).filter(
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
