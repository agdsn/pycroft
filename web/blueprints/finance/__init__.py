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
from datetime import timedelta, datetime, date
from functools import partial
from itertools import groupby, zip_longest, chain
from io import StringIO

from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request,
    url_for)
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import func, or_, and_, Text, cast
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from wtforms import BooleanField

from pycroft import config, lib
from pycroft.helpers.i18n import localized
from pycroft.helpers.util import map_or_default
from pycroft.lib import finance
from pycroft.lib.finance import get_typed_splits, \
    end_payment_in_default_memberships, \
    post_transactions_for_membership_fee, build_transactions_query, \
    match_activities, take_actions_for_payment_in_default_users
from pycroft.model.finance import (
    BankAccount, BankAccountActivity, Split, MembershipFee, MT940Error)
from pycroft.model.session import session
from pycroft.model.user import User
from pycroft.model.finance import Account, Transaction
from web.blueprints.access import BlueprintAccess
from web.blueprints.helpers.fints import FinTS3Client
from web.blueprints.helpers.table import date_format
from web.blueprints.finance.forms import (
    AccountCreateForm, BankAccountCreateForm, BankAccountActivityEditForm,
    BankAccountActivitiesImportForm, TransactionCreateForm,
    MembershipFeeCreateForm, MembershipFeeEditForm, FeeApplyForm,
    HandlePaymentsInDefaultForm, FixMT940Form, BankAccountActivityReadForm)
from web.blueprints.finance.tables import FinanceTable, FinanceTableSplitted, \
    MembershipFeeTable, UsersDueTable, BankAccountTable, \
    BankAccountActivityTable, TransactionTable, ImportErrorTable, \
    UnconfirmedTransactionsTable
from web.blueprints.navigation import BlueprintNavigation
from web.template_filters import date_filter, money_filter, datetime_filter
from web.template_tests import privilege_check
from web.templates import page_resources
from web.blueprints.helpers.api import json_agg_core

from sqlalchemy.sql.expression import literal_column, func, select, Join

from fints.dialog import FinTSDialogError
from fints.exceptions import FinTSClientPINError
from fints.utils import mt940_to_array
from datetime import date

bp = Blueprint('finance', __name__)
access = BlueprintAccess(bp, required_properties=['finance_show'])
nav = BlueprintNavigation(bp, "Finanzen", blueprint_access=access)


@bp.route('/')
@bp.route('/bank-accounts')
@bp.route('/bank-accounts/list')
@nav.navigate(u"Bankkonten")
def bank_accounts_list():
    bank_account_table = BankAccountTable(
        data_url=url_for('.bank_accounts_list_json'),
        create_account=privilege_check(current_user, 'finance_change'))

    bank_account_activity_table = BankAccountActivityTable(
        data_url=url_for('.bank_accounts_activities_json'))

    return render_template(
        'finance/bank_accounts_list.html',
        bank_account_table=bank_account_table,
        bank_account_activity_table=bank_account_activity_table,
    )


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
            'balance': money_filter(bank_account.account.balance),
            'last_imported_at': '{}'.format(
                map_or_default(bank_account.last_imported_at, datetime.date,
                               'nie'))
        } for bank_account in BankAccount.q.all()])


@bp.route('/bank-accounts/activities/json')
def bank_accounts_activities_json():
    if privilege_check(current_user, 'finance_change'):
        def actions(activity_id):
            return [{
                'href': url_for(
                    '.bank_account_activities_edit',
                    activity_id=activity_id),
                'title': '',
                'btn_class': 'btn-primary',
                'icon': 'glyphicon-pencil'
            }]
    else:
        def actions(activity_id):
            return []

    activity_q = (BankAccountActivity.q
            .options(joinedload(BankAccountActivity.bank_account))
            .filter(BankAccountActivity.transaction_id == None))

    return jsonify(items=[{
            'bank_account': activity.bank_account.name,
            'name': activity.other_name,
            'valid_on': date_format(activity.valid_on),
            'imported_at': date_format(activity.imported_at),
            'reference': activity.reference,
            'amount': money_filter(activity.amount),
            'iban': activity.other_account_number,
            'actions': actions(activity.id),
        } for activity in activity_q.all()])


@bp.route('/bank-accounts/import/errors/json')
def bank_accounts_errors_json():
    return jsonify(items=[
        {
            'name': error.bank_account.name,
            'fix': {
                'href': url_for('.fix_import_error',
                                error_id=error.id),
                'title': 'korrigieren',
                'btn_class': 'btn-primary'
            },
            'imported_at': '{}'.format(
                map_or_default(error.imported_at, datetime.date, 'nie'))
        } for error in MT940Error.q.all()])

@bp.route('/bank-accounts/import', methods=['GET', 'POST'])
@access.require('finance_change')
@nav.navigate(u"Bankkontobewegungen importieren")
def bank_accounts_import():
    form = BankAccountActivitiesImportForm()
    form.account.choices = [ (acc.id, acc.name) for acc in BankAccount.q.all()]
    (transactions, old_transactions) = ([], [])
    if request.method != 'POST':
        del(form.start_date)
        form.end_date.data = date.today() - timedelta(days=1)

    if form.validate_on_submit():
        bank_account = BankAccount.q.get(form.account.data)

        # set start_date, end_date
        if form.start_date.data is None:
            form.start_date.data = map_or_default(bank_account.last_imported_at,
                                        datetime.date, date(2018, 1, 1))
        if form.end_date.data is None:
            form.end_date.data = date.today()

        # login with fints
        process = True
        try:
            fints = FinTS3Client(
                bank_account.routing_number,
                form.user.data,
                form.pin.data,
                bank_account.fints_endpoint
            )

            acc = next((a for a in fints.get_sepa_accounts()
                        if a.iban == bank_account.iban), None)
            if acc is None:
                raise KeyError('BankAccount with IBAN {} not found.'.format(
                    bank_account.iban)
                )
            start_date = form.start_date.data
            end_date = form.end_date.data
            statement, with_error = fints.get_filtered_transactions(
                acc, start_date, end_date)
            flash(
                "Transaktionen vom {} bis {}.".format(start_date, end_date))
            if len(with_error) > 0:
                flash("{} Statements enthielten fehlerhafte Daten und müssen "
                      "vor dem Import manuell korrigiert werden.".format(
                    len(with_error)), 'error')

        except (FinTSDialogError, FinTSClientPINError):
            flash(u"Ungültige FinTS-Logindaten.", 'error')
            process = False
        except KeyError:
            flash(u'Das gewünschte Konto kann mit diesem Online-Banking-Zugang\
                    nicht erreicht werden.', 'error')
            process = False

        if process:
            (transactions, old_transactions) = finance.process_transactions(
                bank_account, statement)
        else:
            (transactions, old_transactions) = ([], [])

        if process and form.do_import.data is True:
            # save errors to database
            for error in with_error:
                session.add(MT940Error(mt940=error[0], exception=error[1],
                                       author=current_user,
                                       bank_account=bank_account))

            # save transactions to database
            session.add_all(transactions)
            session.commit()
            flash(u'Bankkontobewegungen wurden importiert.')
            return redirect(url_for(".accounts_show",
                                    account_id=bank_account.account_id))


    return render_template('finance/bank_accounts_import.html', form=form,
                           transactions=transactions,
                           old_transactions=old_transactions)

@bp.route('/bank-accounts/importerrors', methods=['GET', 'POST'])
@access.require('finance_change')
def bank_accounts_import_errors():
    error_table = ImportErrorTable(
        data_url=url_for('.bank_accounts_errors_json'))
    return render_template('finance/bank_accounts_import_errors.html',
                           page_title="Fehlerhafter Bankimport",
                           error_table=error_table)

@bp.route('/bank-accounts/importerrors/<error_id>', methods=['GET', 'POST'])
@access.require('finance_change')
def fix_import_error(error_id):
    error = MT940Error.q.get(error_id)
    form = FixMT940Form()
    (transactions, old_transactions) = ([], [])
    new_exception = None

    if request.method != 'POST':
        form.mt940.data = error.mt940

    if form.validate_on_submit():
        statement = []
        try:
            statement += mt940_to_array(form.mt940.data)
        except Exception as e:
            new_exception = str(e)

        if new_exception is None:
            flash('MT940 ist jetzt valide.', 'success')
            (transactions, old_transactions) = finance.process_transactions(
                error.bank_account, statement)

            if form.do_import.data is True:
                # save transactions to database
                session.add_all(transactions)
                session.delete(error)
                session.commit()
                flash(u'Bankkontobewegungen wurden importiert.')
                return redirect(url_for(".bank_accounts_import_errors"))
        else:
            flash('Es existieren weiterhin Fehler.', 'error')

    return render_template('finance/bank_accounts_error_fix.html',
                    error_id=error_id, exception=error.exception,
                    new_exception=new_exception, form=form,
                    transactions=transactions, old_transactions=old_transactions)


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
            fints_endpoint=form.fints.data,
            account=Account(name=form.name.data, type='BANK_ASSET'),
        )
        session.add(new_bank_account)
        session.commit()
        return redirect(url_for('.bank_accounts_list'))

    return render_template('finance/bank_accounts_create.html',
                           form=form, page_title=u"Bankkonto erstellen")


@bp.route('/bank-account-activities/<activity_id>',
          methods=["GET", "POST"])
def bank_account_activities_edit(activity_id):
    activity = BankAccountActivity.q.get(activity_id)

    if activity is None:
        flash(u"Bankbewegung mit ID {} existiert nicht!".format(activity_id), 'error')
        abort(404)

    if activity.transaction_id is not None:
        form = BankAccountActivityReadForm(
            obj=activity, bank_account_name=activity.bank_account.name)

        if activity.transaction_id:
            flash(u"Bankbewegung ist bereits zugewiesen!".format(activity_id),
                  'warning')

        form_args = {
            'form': form,
            'show_submit': False,
            'show_cancel': False,
        }

        return render_template('generic_form.html',
                               page_title="Bankbewegung",
                               form_args=form_args,
                               form=form)

    else:
        form = BankAccountActivityEditForm(
            obj=activity, bank_account_name=activity.bank_account.name, description=activity.reference)

        if form.validate_on_submit():
            debit_account = Account.q.filter(
                Account.id == form.account_id.data
            ).one()
            credit_account = activity.bank_account.account

            transaction = finance.simple_transaction(
                description=form.description.data, debit_account=debit_account,
                credit_account=credit_account, amount=activity.amount,
                author=current_user, valid_on=activity.valid_on,
                confirmed=current_user.member_of(config.treasurer_group))
            activity.split = next(split for split in transaction.splits
                                  if split.account_id == credit_account.id)
            session.add(activity)

            end_payment_in_default_memberships()

            session.commit()

            flash(u"Transaktion erfolgreich erstellt.", 'success')

            return redirect(url_for('.bank_accounts_list'))

        form_args = {
            'form': form,
            'cancel_to': url_for('.bank_accounts_list'),
            'submit_text': 'Zuweisen',
        }

        return render_template('generic_form.html',
                               page_title="Bankbewegung zuweisen",
                               form_args=form_args,
                               form=form)


@bp.route('/bank-account-activities/match/')
@access.require('finance_change')
def bank_account_activities_match():
    FieldList = [
        #("Field-Name",BooleanField('Text')),
    ]

    matching = match_activities()

    matched_activities = {}
    for activity, user in matching.items():
        matched_activities[str(activity.id)] = {
            'purpose': activity.reference,
            'name': activity.other_name,
            'user': user,
            'amount': activity.amount
        }
        FieldList.append((str(activity.id), BooleanField(str(activity.id),
                                                         default=True)))

    class F(forms.ActivityMatchForm):
        pass

    for (name, field) in FieldList:
        setattr(F, name, field)
    form = F()

    return render_template('finance/bank_accounts_match.html', form=form,
                           activities=matched_activities)

@bp.route('/bank-account-activities/match/do/', methods=['GET', 'POST'])
@access.require('finance_change')
def bank_account_activities_do_match():

    # Generate form again
    matching = match_activities()

    matched = []
    FieldList = []
    for activity, user in matching.items():
        FieldList.append(
            (str(activity.id), BooleanField('{} ({}€) -> {} ({}, {})'.format(
                activity.reference, activity.amount, user.name, user.id,
                user.login
            ))))

    class F(forms.ActivityMatchForm):
        pass

    for (name, field) in FieldList:
        setattr(F, name, field)
    form = F()

    # parse data
    if form.validate_on_submit():
        # look for all matches which were checked
        for activity, user in matching.items():
            if form._fields[str(activity.id)].data is True and activity.transaction_id is None:
                debit_account = user.account
                credit_account = activity.bank_account.account
                transaction = finance.simple_transaction(
                    description=activity.reference,
                    debit_account=debit_account,
                    credit_account=credit_account, amount=activity.amount,
                    author=current_user, valid_on=activity.valid_on)
                activity.split = next(split for split in transaction.splits
                                      if split.account_id == credit_account.id)

                session.add(activity)

                matched.append((activity, user))

        end_payment_in_default_memberships()

        session.flush()
        session.commit()

    return render_template('finance/bank_accounts_matched.html', matched=matched)

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

    if account is None:
        flash(u"Konto mit ID {} existiert nicht!".format(account_id), 'error')
        abort(404)

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
            'value': money_filter(-split.amount) if (style == "inverted") else money_filter(split.amount),
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
                               sort_order=sort_order, offset=offset,
                               limit=limit, eagerload=True)

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
        get_transaction_type=finance.get_transaction_type,
        localized=localized,
        transaction_table=TransactionTable(
            data_url=url_for(".transactions_show_json",
                             transaction_id=transaction.id)),
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
                'title': localized(split.account.name, {int: {'insert_commas': False}})
            },
            'amount': money_filter(split.amount),
            'row_positive': split.amount > 0
        } for split in transaction.splits])


@bp.route('/transactions/unconfirmed')
@nav.navigate(u"Unbestätigte Transaktionen")
def transactions_unconfirmed():
    return render_template(
        'finance/transactions_unconfirmed.html',
        page_title="Unbestätigte Transaktionen",
        unconfirmed_transactions_table=UnconfirmedTransactionsTable(
            data_url=url_for(".transactions_unconfirmed_json"))
    )


@bp.route('/transactions/unconfirmed/json')
def transactions_unconfirmed_json():
    transactions = Transaction.q.filter_by(confirmed=False).order_by(Transaction.posted_at).limit(100).all()

    return jsonify(
        items=[
        {
            'description': {
                'href': url_for(".transactions_show", transaction_id=transaction.id),
                'title': transaction.description,
                'new_tab': True
            },
            'author': {
                'href': url_for("user.user_show",
                                user_id=transaction.author.id),
                'title': transaction.author.name,
                'new_tab': True
            },
            'date': date_format(transaction.posted_at),
            'amount': money_filter(transaction.amount),
            'details': {
                'href': url_for(".transactions_show", transaction_id=transaction.id),
                'title': 'Details',
                'btn_class': 'btn-primary',
                'new_tab': True
            },
            'actions': [{
                    'href': url_for(".transaction_confirm",
                                    transaction_id=transaction.id),
                    'title': 'Bestätigen',
                    'icon': 'glyphicon-ok'
                },{
                    'href': url_for(".transaction_delete",
                                    transaction_id=transaction.id),
                    'title': 'Löschen',
                    'icon': 'glyphicon-trash'
                }
            ],
        } for transaction in transactions])


@bp.route('/transaction/<int:transaction_id>/confirm', methods=['GET', 'POST'])
@access.require('finance_change')
def transaction_confirm(transaction_id):
    transaction = Transaction.q.get(transaction_id)

    if transaction is None:
        flash(u"Transaktion existiert nicht.", 'error')
        abort(404)

    if transaction.confirmed:
        flash(u"Diese Transaktion wurde bereits bestätigt.", 'error')
        abort(404)

    lib.finance.transaction_confirm(transaction)

    session.commit()

    flash(u'Transaktion bestätigt.', 'success')
    return redirect(url_for('.transactions_unconfirmed'))


@bp.route('/transaction/<int:transaction_id>/delete', methods=['GET', 'POST'])
@access.require('finance_change')
def transaction_delete(transaction_id):
    transaction = Transaction.q.get(transaction_id)

    if transaction is None:
        flash(u"Transaktion existiert nicht.", 'error')
        abort(404)

    if transaction.confirmed:
        flash(u"Diese Transaktion wurde bereits bestätigt und kann daher nicht gelöscht werden.", 'error')
        abort(400)

    form = FlaskForm()

    if form.is_submitted():
        lib.finance.transaction_delete(transaction)

        session.commit()

        flash(u'Transaktion gelöscht.', 'success')
        return redirect(url_for('.transactions_unconfirmed'))

    form_args = {
        'form': form,
        'cancel_to': url_for('.transactions_unconfirmed'),
        'submit_text': 'Löschen',
        'actions_offset': 0
    }

    return render_template('generic_form.html',
                           page_title="Transaktion löschen",
                           form_args=form_args,
                           form=form)

@access.require('finance_show')
@bp.route('/transactions')
def transactions_all():
    return render_template('finance/transactions_overview.html',
                           api_endpoint=url_for(".transactions_all_json",
                                                **request.args))


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

        end_payment_in_default_memberships()

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



@bp.route("/membership_fee/<int:fee_id>/book", methods=['GET', 'POST'])
@access.require('finance_change')
def membership_fee_book(fee_id):
    fee = MembershipFee.q.get(fee_id)

    if fee is None:
        flash(u'Ein Beitrag mit dieser ID existiert nicht!', 'error')
        abort(404)

    form = FeeApplyForm()
    if form.is_submitted():
        affected_users = post_transactions_for_membership_fee(
            fee, current_user)

        session.commit()

        flash("{} neue Buchungen erstellt.".format(len(affected_users)), "success")

        return redirect(url_for(".membership_fees"))

    table = UsersDueTable(data_url=url_for('.membership_fee_users_due_json', fee_id=fee.id))
    return render_template('finance/membership_fee_book.html', form=form,
                           page_title='Beitrag buchen', table=table)


@bp.route("/membership_fee/<int:fee_id>/users_due_json")
def membership_fee_users_due_json(fee_id):
    fee = MembershipFee.q.get(fee_id)

    if fee is None:
        abort(404)

    affected_users = post_transactions_for_membership_fee(
        fee, current_user, simulate=True)

    fee_amount = {'value': str(fee.regular_fee) + '€',
                  'is_positive': (fee.regular_fee < 0)}
    fee_description = localized(
        finance.membership_fee_description.format(fee_name=fee.name).to_json())

    return jsonify(items=[{
        'user_id': user['id'],
        'user': {'title': str(user['name']),
                 'href': url_for("user.user_show", user_id=user['id'])},
        'amount': fee_amount,
        'description': fee_description,
        'valid_on': fee.ends_on
    } for user in affected_users])


@bp.route("/membership_fees", methods=['GET', 'POST'])
@nav.navigate(u"Beiträge")
def membership_fees():
    table = MembershipFeeTable(data_url=url_for('.membership_fees_json'))
    return render_template('finance/membership_fees.html', table=table)


@bp.route("/membership_fees/json")
@access.require('finance_change')
def membership_fees_json():
    return jsonify(items=[
        {
            'name': localized(membership_fee.name),
            'regular_fee': money_filter(
                membership_fee.regular_fee),
            'payment_deadline': membership_fee.payment_deadline.days,
            'payment_deadline_final': membership_fee.payment_deadline_final.days,
            'begins_on': date_format(membership_fee.begins_on),
            'ends_on': date_format(membership_fee.ends_on),
            'finance_link': {'href': url_for(".transactions_all",
                                        filter="all",
                                        after=membership_fee.begins_on,
                                        before=membership_fee.ends_on),
                            'title': 'Finanzübersicht',
                            'icon': 'glyphicon-euro'},
            'book_link': {'href': url_for(".membership_fee_book",
                                          fee_id=membership_fee.id),
                          'title': 'Buchen',
                          'icon': 'glyphicon-book'},
            'edit_link': {'href': url_for(".membership_fee_edit",
                                        fee_id=membership_fee.id),
                            'title': 'Bearbeiten',
                            'icon': 'glyphicon-edit'},
        } for membership_fee in MembershipFee.q.order_by(MembershipFee.begins_on.desc()).all()])


@bp.route('/membership_fee/create', methods=("GET", "POST"))
@access.require('finance_change')
def membership_fee_create():
    previous_fee = MembershipFee.q.order_by(MembershipFee.id.desc()).first()
    if previous_fee:
        begins_on_default = previous_fee.ends_on + timedelta(1)

        next_month = begins_on_default.replace(day=28) + timedelta(4)
        ends_on_default = begins_on_default.replace(
            day=(next_month - timedelta(days=next_month.day)).day
        )

        name_default = str(begins_on_default.year) \
                       + "-" + "%02d" % begins_on_default.month

        form = MembershipFeeCreateForm(
            name=name_default,
            regular_fee=previous_fee.regular_fee,
            booking_begin=previous_fee.booking_begin.days,
            booking_end=previous_fee.booking_end.days,
            payment_deadline=previous_fee.payment_deadline.days,
            payment_deadline_final=previous_fee.payment_deadline_final.days,
            begins_on=begins_on_default,
            ends_on=ends_on_default,
        )
    else:
        form = MembershipFeeCreateForm()
    if form.validate_on_submit():
        mfee = MembershipFee(
            name=form.name.data,
            regular_fee=form.regular_fee.data,
            booking_begin=timedelta(days=form.booking_begin.data),
            booking_end=timedelta(days=form.booking_end.data),
            payment_deadline=timedelta(days=form.payment_deadline.data),
            payment_deadline_final=timedelta(days=form.payment_deadline_final.data),
            begins_on=form.begins_on.data,
            ends_on=form.ends_on.data,
        )
        session.add(mfee)
        session.commit()
        flash("Beitrag erfolgreich erstellt.", "success")
        return redirect(url_for(".membership_fees"))
    return render_template('finance/membership_fee_create.html', form=form)


@bp.route('/membership_fee/<int:fee_id>/edit', methods=("GET", "POST"))
@access.require('finance_change')
def membership_fee_edit(fee_id):
    fee = MembershipFee.q.get(fee_id)

    if fee is None:
        flash(u'Ein Beitrag mit dieser ID existiert nicht!', 'error')
        abort(404)

    form = MembershipFeeEditForm()

    if not form.is_submitted():
        form = MembershipFeeEditForm(
            name=fee.name,
            regular_fee=fee.regular_fee,
            booking_begin=fee.booking_begin.days,
            booking_end=fee.booking_end.days,
            payment_deadline=fee.payment_deadline.days,
            payment_deadline_final=fee.payment_deadline_final.days,
            begins_on=fee.begins_on,
            ends_on=fee.ends_on,
        )
    elif form.validate_on_submit():
        fee.name = form.name.data
        fee.regular_fee = form.regular_fee.data
        fee.booking_begin = timedelta(days=form.booking_begin.data)
        fee.booking_end = timedelta(days=form.booking_end.data)
        fee.payment_deadline = timedelta(days=form.payment_deadline.data)
        fee.payment_deadline_final = timedelta(days=form.payment_deadline_final.data)
        fee.begins_on = form.begins_on.data
        fee.ends_on = form.ends_on.data

        session.commit()
        return redirect(url_for(".membership_fees"))
    return render_template('finance/membership_fee_edit.html', form=form)


@bp.route('/membership_fees/handle_payments_in_default', methods=("GET", "POST"))
@access.require('finance_change')
def handle_payments_in_default():
    finance.end_payment_in_default_memberships()

    users_pid_membership_all, users_membership_terminated_all = finance.get_users_with_payment_in_default()

    form = HandlePaymentsInDefaultForm()

    # Using `query_factory` instead of `query`, because wtforms would not process an empty list as `query`
    form.new_pid_memberships.query_factory = lambda: users_pid_membership_all
    form.terminated_member_memberships.query_factory = lambda: users_membership_terminated_all

    if not form.is_submitted():
        form.new_pid_memberships.process_data(users_pid_membership_all)
        form.terminated_member_memberships.process_data(
            users_membership_terminated_all)

    if form.validate_on_submit():
        users_pid_membership = form.new_pid_memberships.data
        users_membership_terminated = form.terminated_member_memberships.data

        take_actions_for_payment_in_default_users(
            users_pid_membership=users_pid_membership,
            users_membership_terminated=users_membership_terminated,
            processor=current_user)
        session.commit()
        flash("Zahlungsrückstände behandelt.", "success")
        return redirect(url_for(".membership_fees"))

    form_args = {
        'form': form,
        'cancel_to': url_for('.membership_fees'),
        'submit_text': 'Anwenden',
        'actions_offset': 0
    }

    return render_template('generic_form.html',
                           page_title="Zahlungsrückstände behandeln",
                           form_args=form_args,
                           form=form)


@bp.route('/json/accounts/system')
def json_accounts_system():
    return jsonify(accounts=[
        {
            "account_id": account.id,
            "account_name": localized(account.name),
            "account_type": account.type
        } for account in Account.q.outerjoin(User).filter(
            and_(User.account == None,
            Account.type != "USER_ASSET")
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
