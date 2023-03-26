# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.finance
    ~~~~~~~~~~~~~~

    This module defines view functions for /finance

    :copyright: (c) 2012 by AG DSN.
"""
import typing as t
from datetime import date
from datetime import timedelta, datetime
from functools import partial
from itertools import zip_longest, chain

import wtforms
from fints.dialog import FinTSDialogError
from fints.exceptions import (
    FinTSClientPINError,
    FinTSError,
    FinTSClientTemporaryAuthError,
)
from fints.utils import mt940_to_array
from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request,
    url_for, make_response)
from flask_login import current_user
from flask_wtf import FlaskForm
from mt940.models import Transaction as MT940Transaction
from sqlalchemy import or_, Text, cast, ColumnClause, FromClause
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.sql.expression import literal_column, func, select, Join
from wtforms import BooleanField

from pycroft import config, lib
from pycroft.exc import PycroftException
from pycroft.helpers.i18n import localized
from pycroft.lib import finance
from pycroft.lib.finance import (
    end_payment_in_default_memberships,
    post_transactions_for_membership_fee,
    build_transactions_query,
    take_actions_for_payment_in_default_users,
    get_pid_csv,
    get_negative_members,
    get_system_accounts,
    ImportedTransactions,
    match_activities,
    get_all_bank_accounts,
    get_unassigned_bank_account_activities,
    get_all_mt940_errors,
    get_accounts_by_type,
    get_last_import_date,
    get_last_membership_fee,
)
from pycroft.lib.finance.fints import get_fints_transactions
from pycroft.lib.mail import MemberNegativeBalance
from pycroft.lib.user import encode_type2_user_id, user_send_mails
from pycroft.model.finance import Account, Transaction
from pycroft.model.finance import (
    BankAccount, BankAccountActivity, Split, MembershipFee, MT940Error)
from pycroft.model.session import session, utcnow
from pycroft.model.user import User
from web.blueprints.access import BlueprintAccess
from web.blueprints.finance.forms import (
    AccountCreateForm, BankAccountCreateForm, BankAccountActivityEditForm,
    BankAccountActivitiesImportForm, TransactionCreateForm,
    MembershipFeeCreateForm, MembershipFeeEditForm, FeeApplyForm,
    HandlePaymentsInDefaultForm, FixMT940Form, BankAccountActivityReadForm,
    BankAccountActivitiesImportManualForm, ConfirmPaymentReminderMail)
from web.blueprints.finance.tables import FinanceTable, FinanceTableSplitted, \
    MembershipFeeTable, UsersDueTable, BankAccountTable, \
    BankAccountActivityTable, TransactionTable, ImportErrorTable, \
    UnconfirmedTransactionsTable
from web.blueprints.helpers.api import json_agg_core
from web.blueprints.helpers.exception import handle_errors
from web.blueprints.navigation import BlueprintNavigation
from web.table.table import date_format
from web.template_filters import date_filter, money_filter, datetime_filter
from web.template_tests import privilege_check

from . import forms

bp = Blueprint('finance', __name__)
access = BlueprintAccess(bp, required_properties=['finance_show'])
nav = BlueprintNavigation(bp, "Finanzen", icon='fa-euro-sign', blueprint_access=access)


@bp.route('/')
@bp.route('/bank-accounts')
@bp.route('/bank-accounts/list')
@nav.navigate("Bankkonten", icon='fa-university')
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
    return jsonify(
        items=[
            {
                "name": bank_account.name,
                "bank": bank_account.bank,
                "ktonr": bank_account.account_number,
                "blz": bank_account.routing_number,
                "iban": bank_account.iban,
                "bic": bank_account.bic,
                "kto": BankAccountTable.kto.value(
                    href=url_for(".accounts_show", account_id=bank_account.account_id),
                    title="Konto anzeigen",
                    btn_class="btn-primary",
                ),
                "balance": money_filter(bank_account.balance),
                "last_imported_at": (
                    str(datetime.date(i))
                    if (i := bank_account.last_imported_at) is not None
                    else "nie"
                ),
            }
            for bank_account in get_all_bank_accounts(session)
        ]
    )


@bp.route('/bank-accounts/activities/json')
def bank_accounts_activities_json():
    def actions(activity_id):
        return [BankAccountActivityTable.actions.single_value(
            href=url_for('.bank_account_activities_edit', activity_id=activity_id),
            title='',
            btn_class='btn-primary',
            icon='fa-edit'
        )]

    activity_q = get_unassigned_bank_account_activities(session)

    return jsonify(
        items=[
            {
                "bank_account": activity.bank_account.name,
                "name": activity.other_name,
                "valid_on": date_format(activity.valid_on, formatter=date_filter),
                "imported_at": date_format(activity.imported_at, formatter=date_filter),
                "reference": activity.reference,
                "amount": activity.amount,
                "iban": activity.other_account_number,
                "actions": actions(activity.id),
                "row_positive": activity.amount >= 0,
            }
            for activity in activity_q
        ]
    )


@bp.route('/bank-accounts/import/errors/json')
def bank_accounts_errors_json():
    T = ImportErrorTable
    return jsonify(
        items=[
            {
                "name": error.bank_account.name,
                "fix": T.fix.value(
                    href=url_for(".fix_import_error", error_id=error.id),
                    title="korrigieren",
                    btn_class="btn-primary",
                ),
                "imported_at": (
                    str(datetime.date(i))
                    if (i := error.imported_at) is not None
                    else "nie"
                ),
            }
            for error in get_all_mt940_errors(session)
        ]
    )


from contextlib import contextmanager

@contextmanager
def flash_fints_errors():
    try:
        yield
    except (FinTSDialogError, FinTSClientPINError) as e:
        flash(f"Ungültige FinTS-Logindaten: '{e}'", 'error')
        raise PycroftException from e
    except FinTSClientTemporaryAuthError as e:
        flash(f"Temporärer Fehler bei der Authentifizierung: '{e}'", "error")
        raise PycroftException from e
    except FinTSError as e:
        flash(f"Anderer FinTS-Fehler: '{e}'", 'error')
        raise PycroftException from e
    except KeyError as e:
        flash('Das gewünschte Konto kann mit diesem Online-Banking-Zugang\
                nicht erreicht werden.', 'error')
        raise PycroftException from e

@bp.route('/bank-accounts/import', methods=['GET', 'POST'])
@access.require('finance_change')
@nav.navigate("Bankkontobewegungen importieren", icon='fa-file-import')
def bank_accounts_import():
    form = BankAccountActivitiesImportForm()
    form.account.choices = [
        (acc.id, acc.name) for acc in get_all_bank_accounts(session)
    ]
    imported = ImportedTransactions([], [], [])

    def display_form_response(
        imported: ImportedTransactions,
    ):
        return render_template(
            'finance/bank_accounts_import.html', form=form,
            transactions=imported.new,
            old_transactions=imported.old,
            doubtful_transactions=imported.doubtful,
        )

    if not form.is_submitted():
        del (form.start_date)
        form.end_date.data = date.today() - timedelta(days=1)
        return display_form_response(imported)

    if not form.validate():
        return display_form_response(imported)

    bank_account = BankAccount.get(form.account.data)

    # set start_date, end_date
    if form.start_date.data is None:
        # NB: start date default depends on `bank_account`
        form.start_date.data = (
            datetime.date(i)
            if (i := bank_account.last_imported_at) is not None
            else date(2018, 1, 1)
        )
    if form.end_date.data is None:
        form.end_date.data = date.today()
    start_date = form.start_date.data
    end_date = form.end_date.data

    try:
        with flash_fints_errors():
            statement, errors = get_fints_transactions(
                product_id=config.fints_product_id,
                user_id=form.user.data,
                secret_pin=form.secret_pin.data,
                bank_account=bank_account,
                start_date=start_date,
                end_date=end_date,
            )
    except PycroftException:
        return display_form_response(imported)

    flash(f"Transaktionen vom {start_date} bis {end_date}.")
    if errors:
        flash(
            f"{len(errors)} Statements enthielten fehlerhafte Daten und müssen "
            "vor dem Import manuell korrigiert werden",
            "error",
        )

    imported = finance.process_transactions(bank_account, statement)
    flash(
        f"Klassifizierung: {len(imported.new)} neu "
        f"/ {len(imported.old)} alt "
        f"/ {len(imported.doubtful)} zu neu (Buchung >= {date.today()}T00:00Z)."
    )
    if not form.do_import.data:
        return display_form_response(imported)

    # persist transactions and errors
    session.add_all(
        MT940Error(
            mt940=error.statement,
            exception=error.error,
            author=current_user,
            bank_account=bank_account,
        )
        for error in errors
    )
    session.add_all(imported.new)
    session.commit()
    flash(
        f"{len(imported.new)} Bankkontobewegungen wurden importiert.",
        "success" if imported.new else "info",
    )
    return redirect(url_for(".accounts_show", account_id=bank_account.account_id))


@bp.route('/bank-accounts/importmanual', methods=['GET', 'POST'])
@access.require('finance_change')
def bank_accounts_import_manual():
    form = BankAccountActivitiesImportManualForm()
    form.account.query = get_all_bank_accounts(session)

    if form.validate_on_submit():
        bank_account = form.account.data

        if form.file.data:
            mt940 = form.file.data.read().decode()

            mt940_entry = MT940Error(mt940=mt940, exception="manual import",
                                     author=current_user,
                                     bank_account=bank_account)
            session.add(mt940_entry)

            session.commit()
            flash('Datensatz wurde importiert. Buchungen können jetzt importiert werden.')
            return redirect(url_for(".fix_import_error", error_id=mt940_entry.id))
        else:
            flash("Kein MT940 hochgeladen.", 'error')

    return render_template('finance/bank_accounts_import_manual.html', form=form)


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
    error = MT940Error.get(error_id)
    form = FixMT940Form()
    imported = ImportedTransactions([], [], [])
    new_exception = None

    def default_response():
        return render_template(
            "finance/bank_accounts_error_fix.html",
            error_id=error_id,
            exception=error.exception,
            new_exception=new_exception,
            form=form,
            transactions=imported.new,
            old_transactions=imported.old,
            doubtful_transactions=imported.doubtful,
        )

    if not form.is_submitted():
        form.mt940.data = error.mt940
        return default_response()

    if not form.validate():
        return default_response()

    try:
        statement: list[MT940Transaction] = mt940_to_array(form.mt940.data)
    except Exception as e:
        new_exception = str(e)
        flash("Es existieren weiterhin Fehler.", "error")
        return default_response()

    if not statement:
        flash("MT940 ist valide, enthält aber keine statements", "warning")
        return default_response()

    flash(f"MT940 ist jetzt valide ({len(statement)} statements)", "success")
    imported = finance.process_transactions(error.bank_account, statement)

    # save transactions to database
    if not form.do_import.data:
        return default_response()

    session.add_all(imported.new)
    session.delete(error)
    session.commit()
    flash("Bankkontobewegungen wurden importiert.")
    return redirect(url_for(".bank_accounts_import_errors"))


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
        flash("Bankkonto wurde erstellt.", "success")
        return redirect(url_for('.bank_accounts_list'))

    return render_template('finance/bank_accounts_create.html',
                           form=form, page_title="Bankkonto erstellen")


@bp.route('/bank-account-activities/<activity_id>',
          methods=["GET", "POST"])
def bank_account_activities_edit(activity_id):
    activity = BankAccountActivity.get(activity_id)

    if activity is None:
        flash(f"Bankbewegung mit ID {activity_id} existiert nicht!", 'error')
        abort(404)

    if activity.transaction_id is not None:
        form = BankAccountActivityReadForm(
            obj=activity, bank_account_name=activity.bank_account.name)

        if activity.transaction_id:
            flash("Bankbewegung ist bereits zugewiesen!", "warning")

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
            obj=activity, bank_account_name=activity.bank_account.name,
            description=activity.reference)

        if form.validate_on_submit():
            # TODO use `session.get`
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

            end_payment_in_default_memberships(current_user)

            session.commit()

            flash("Transaktion erfolgreich erstellt.", 'success')

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
    matching_user, matching_team = match_activities()

    field_list_user, matched_activities_user \
        = _create_field_list_and_matched_activities_dict(matching_user, "user")
    field_list_team, matched_activities_team \
        = _create_field_list_and_matched_activities_dict(matching_team, "team")

    form = _create_combined_form(field_list_user, field_list_team)

    return render_template('finance/bank_accounts_match.html', form=form,
                           activities_user=matched_activities_user,
                           activities_team=matched_activities_team)


def _create_field_list_and_matched_activities_dict(matching, prefix):
    matched_activities = {}
    field_list = []
    for activity, entity in matching.items():
        matched_activities[f"{prefix}-{str(activity.id)}"] = {
            'purpose': activity.reference,
            'name': activity.other_name,
            prefix: entity,
            'amount': activity.amount
        }
        field_list.append((str(activity.id), BooleanField(str(activity.id), default=True)))

    return field_list, matched_activities


@bp.route('/bank-account-activities/match/do/', methods=['GET', 'POST'])
@access.require('finance_change')
def bank_account_activities_do_match():
    # Generate form again
    matching_user, matching_team = match_activities()

    field_list_user = _create_field_list(matching_user)
    field_list_team = _create_field_list(matching_team)
    form = _create_combined_form(field_list_user, field_list_team)

    matched_user = []
    matched_team = []
    if form.user.validate_on_submit() or form.team.validate_on_submit():
        # parse data
        matched_user = _apply_checked_matches(matching_user, form.user)
        matched_team = _apply_checked_matches(matching_team, form.team)
        end_payment_in_default_memberships(current_user)

        session.flush()
        session.commit()

    return render_template('finance/bank_accounts_matched.html', matched_user=matched_user,
                           matched_team=matched_team)


def _create_field_list(matching):
    field_list = []
    for activity, entity in matching.items():
        field_list.append(
            (str(activity.id), BooleanField('{} ({}€) -> {} ({})'.format(
                activity.reference, activity.amount, entity.name, entity.id
            ))))

    return field_list


def _create_combined_form(field_list_user, field_list_team):
    form_user = _create_form(field_list_user)
    form_team = _create_form(field_list_team)

    class Form(FlaskForm):
        user = wtforms.FormField(form_user)
        team = wtforms.FormField(form_team)

    return Form()


def _create_form(field_list):
    class F(forms.ActivityMatchForm):
        pass

    for (name, field) in field_list:
        setattr(F, name, field)
    return F


def _apply_checked_matches(matching, subform):
    # look for all matches which were checked
    matched = []
    for activity, entity in matching.items():
        if subform[str(activity.id)].data and activity.transaction_id is None:
            debit_account = entity if type(entity) is Account else entity.account
            credit_account = activity.bank_account.account
            transaction = finance.simple_transaction(
                description=activity.reference,
                debit_account=debit_account,
                credit_account=credit_account, amount=activity.amount,
                author=current_user, valid_on=activity.valid_on
            )
            activity.split = next(split for split in transaction.splits
                                  if split.account_id == credit_account.id)

            session.add(activity)
            matched.append((activity, entity))

    return matched


@bp.route('/accounts/')
@bp.route('/accounts/list')
@nav.navigate("Konten", icon='fa-money-check-alt')
def accounts_list():
    return render_template(
        "finance/accounts_list.html",
        accounts=get_accounts_by_type(session),
    )


@bp.route('/account/<int:account_id>/toggle-legacy')
@access.require('finance_change')
def account_toggle_legacy(account_id):
    account = Account.get(account_id)

    if not account:
        abort(404)

    account.legacy = not account.legacy

    session.commit()

    flash("Der Status des Kontos wurde umgeschaltet.", "success")

    return redirect(url_for('.accounts_show', account_id=account_id))


@bp.route('/accounts/<int:account_id>/balance/json')
def balance_json(account_id):
    invert = request.args.get('invert', 'False') == 'True'

    sum_exp = func.sum(Split.amount).over(order_by=Transaction.valid_on)

    if invert:
        sum_exp = -sum_exp

    balance_json = (select(Transaction.valid_on,
                           sum_exp.label("balance")
                           )
                    .select_from(
        Join(Split, Transaction,
             Split.transaction_id == Transaction.id))
                    .where(Split.account_id == account_id))

    res = session.execute(json_agg_core(balance_json)).first()[0]
    return jsonify(items=res)


@bp.route('/accounts/<int:account_id>')
def accounts_show(account_id):
    account = session.get(Account, account_id)

    if account is None:
        flash(f"Konto mit ID {account_id} existiert nicht!", 'error')
        abort(404)

    # TODO extract to lib function
    try:
        user = User.q.filter_by(account_id=account.id).one()
    except NoResultFound:
        user = None
    except MultipleResultsFound:
        user = User.q.filter_by(account_id=account.id).first()
        flash("Es existieren mehrere Nutzer, die mit diesem Konto"
              " verbunden sind!", "warning")

    inverted = account.type == "USER_ASSET"

    _table_kwargs = {
        'data_url': url_for("finance.accounts_show_json", account_id=account_id),
        'saldo': account.balance,
        'inverted': inverted
    }

    balance = -account.balance if inverted else account.balance

    return render_template(
        'finance/accounts_show.html',
        account=account, user=user, balance=balance,
        balance_json_url=url_for('.balance_json', account_id=account_id,
                                 invert=inverted),
        finance_table_regular=FinanceTable(**_table_kwargs),
        finance_table_splitted=FinanceTableSplitted(**_table_kwargs),
        account_name=localized(account.name, {int: {'insert_commas': False}})
    )


def _format_row(split, style, prefix=None):
    T = FinanceTable
    row = {
        'posted_at': datetime_filter(split.transaction.posted_at),
        # 'posted_by': (split.transaction.author.id, split.transaction.author.name),
        'valid_on': date_filter(split.transaction.valid_on),
        'description': T.description.value(
            href=url_for("finance.transactions_show",
                         transaction_id=split.transaction_id),
            title=localized(split.transaction.description)
            if split.transaction.description
            else 'Keine Beschreibung'
        ),
        'amount': T.amount.value(
            value=money_filter(-split.amount) if (style == "inverted") else money_filter(
                split.amount),
            is_positive=(split.amount > 0) ^ (style == "inverted"),
        ),
        'row_positive': (split.amount > 0) ^ (style == "inverted"),
    }
    if prefix is None:
        return row
    return {f'{prefix}_{key}': val for key, val in row.items()}


T = t.TypeVar("T")
U = t.TypeVar("U")


def _prefixed_merge(
    a: dict[str, T], prefix_a: str, b: dict[str, U], prefix_b: str
) -> dict[str, T | U]:
    result: dict[str, T | U] = {}
    result.update(**{f'{prefix_a}_{k}': v
                     for k, v in a.items()})
    result.update(**{f'{prefix_b}_{k}': v
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

    account = Account.get(account_id) or abort(404)

    total = Split.q.join(Transaction).filter(Split.account == account).count()

    build_this_query = partial(build_transactions_query,
                               account=account, search=search, sort_by=sort_by,
                               sort_order=sort_order, offset=offset,
                               limit=limit, eagerload=True)

    def rows_from_query(query):
        # iterating over `query` executes it
        return [_format_row(split, style) for split in session.scalars(query)]

    if splitted:
        rows_pos = rows_from_query(build_this_query(positive=True))
        rows_neg = rows_from_query(build_this_query(positive=False))

        _keys = ['posted_at', 'valid_on', 'description', 'amount']
        _filler = {key: None for key in chain(('soll_' + key for key in _keys),
                                              ('haben_' + key for key in _keys))}

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
    transaction = Transaction.get(transaction_id)

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
    transaction = Transaction.get(transaction_id)
    return jsonify(
        description=transaction.description,
        items=[
            {
                'account': TransactionTable.account.value(
                    href=url_for(".accounts_show", account_id=split.account_id),
                    title=localized(split.account.name, {int: {'insert_commas': False}})
                ),
                'amount': money_filter(split.amount),
                'row_positive': split.amount > 0
            } for split in transaction.splits])


@bp.route('/transactions/unconfirmed')
@nav.navigate("Unbestätigte Transaktionen", icon='fa-question')
def transactions_unconfirmed():
    return render_template(
        'finance/transactions_unconfirmed.html',
        page_title="Unbestätigte Transaktionen",
        unconfirmed_transactions_table=UnconfirmedTransactionsTable(
            data_url=url_for(".transactions_unconfirmed_json"))
    )


@bp.route('/transactions/unconfirmed/json')
def transactions_unconfirmed_json():
    transactions = Transaction.q.filter_by(confirmed=False).order_by(Transaction.posted_at).limit(
        100).all()

    items = []
    T = UnconfirmedTransactionsTable

    for transaction in transactions:
        user_account = next(
            (a for a in transaction.accounts if a.type == "USER_ASSET"), None
        )
        bank_acc_act = BankAccountActivity.q.filter_by(
            transaction_id=transaction.id
        ).first()

        items.append(
            {
                'description': T.description.value(
                    href=url_for(".transactions_show", transaction_id=transaction.id),
                    title=transaction.description,
                    new_tab=True,
                    glyphicon='fa-external-link-alt'
                ),
                'user': T.user.value(
                    href=url_for("user.user_show", user_id=user_account.user.id),
                    title="{} ({})".format(user_account.user.name,
                                           encode_type2_user_id(user_account.user.id)),
                    new_tab=True
                ) if user_account else None,
                'room': user_account.user.room.short_name if user_account and user_account.user.room else None,
                'author': T.author.value(
                    href=url_for("user.user_show", user_id=transaction.author.id),
                    title=transaction.author.name,
                    new_tab=True
                ),
                'date': date_format(transaction.posted_at, formatter=date_filter),
                'amount': money_filter(transaction.amount),
                'actions': [
                    T.actions.single_value(
                        href=url_for(".bank_account_activities_edit",
                                     activity_id=bank_acc_act.id),
                        title='Bankbewegung', icon='fa-credit-card',
                        btn_class='btn-info btn-sm',
                        new_tab=True
                    ) if bank_acc_act is not None else {},
                    T.actions.single_value(
                        href=url_for(".transaction_confirm",
                                     transaction_id=transaction.id), title='Bestätigen',
                        icon='fa-check', btn_class='btn-success btn-sm'
                    ),
                    T.actions.single_value(
                        href=url_for(".transaction_delete",
                                     transaction_id=transaction.id), title='Löschen',
                        icon='fa-trash',
                        btn_class='btn-danger btn-sm'
                    )
                ] if privilege_check(current_user, 'finance_change') else [],
            })

    return jsonify(items=items)


@bp.route('/transaction/<int:transaction_id>/confirm', methods=['GET', 'POST'])
@access.require('finance_change')
def transaction_confirm(transaction_id):
    transaction = Transaction.get(transaction_id)

    if transaction is None:
        flash("Transaktion existiert nicht.", 'error')
        abort(404)

    if transaction.confirmed:
        flash("Diese Transaktion wurde bereits bestätigt.", 'error')
        abort(400)

    lib.finance.transaction_confirm(transaction, current_user)

    session.commit()

    flash('Transaktion bestätigt.', 'success')
    return redirect(url_for('.transactions_unconfirmed'))


@bp.route('/transaction/confirm', methods=['GET', 'POST'])
@access.require('finance_change')
def transaction_confirm_all():
    form = FlaskForm()

    def default_response():
        form_args = {
            'form': form,
            'cancel_to': url_for('.transactions_unconfirmed'),
            'submit_text': 'Alle Bestätigen',
            'actions_offset': 0
        }
        return render_template('generic_form.html',
                               page_title="Alle Transaktionen (älter als 1h) bestätigen",
                               form_args=form_args,
                               form=form)

    if not form.is_submitted():
        return default_response()

    try:
        with handle_errors(session):
            lib.finance.transaction_confirm_all(current_user)
            session.commit()
    except PycroftException:
        return default_response()

    flash("Alle Transaktionen wurden bestätigt.", 'success')
    return redirect(url_for('.transactions_unconfirmed'))


@bp.route('/transaction/<int:transaction_id>/delete', methods=['GET', 'POST'])
@access.require('finance_change')
def transaction_delete(transaction_id):
    transaction = Transaction.get(transaction_id)

    if transaction is None:
        flash("Transaktion existiert nicht.", 'error')
        abort(404)

    if transaction.confirmed:
        flash("Diese Transaktion wurde bereits bestätigt und kann daher nicht gelöscht werden.",
              'error')
        abort(400)

    form = FlaskForm()

    if form.is_submitted():
        lib.finance.transaction_delete(transaction, current_user)

        session.commit()

        flash('Transaktion gelöscht.', 'success')
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
    transactions: FromClause
    if filter == "nonuser":
        non_user_transactions = (select(Split.transaction_id)
                                 .select_from(
            Join(Split, User,
                 (User.account_id == Split.account_id),
                 isouter=True))
                                 .group_by(Split.transaction_id)
                                 .having(func.bool_and(User.id.is_(None)))
                                 .alias("nut"))

        tid: ColumnClause[int] = literal_column("nut.transaction_id")
        transactions = non_user_transactions.join(Transaction,
                                                  Transaction.id == tid)
    else:
        transactions = Transaction.__table__

    q = (select(Transaction.id,
                Transaction.valid_on,
                Split.account_id,
                Account.type,
                Split.amount)
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
@nav.navigate('Buchung erstellen', icon='fa-plus')
@access.require('finance_change')
def transactions_create():
    form = TransactionCreateForm()
    if form.validate_on_submit():
        splits = [(
            Account.get(split_form.account_id.data),
            split_form.amount.data
        ) for split_form in form.splits]
        transaction = finance.complex_transaction(
            description=form.description.data,
            author=current_user,
            splits=splits,
            valid_on=form.valid_on.data,
            confirmed=current_user.member_of(config.treasurer_group),
        )

        end_payment_in_default_memberships(current_user)

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
                           page_title="Konto erstellen")


@bp.route("/membership_fee/<int:fee_id>/book", methods=['GET', 'POST'])
@access.require('finance_change')
def membership_fee_book(fee_id):
    fee = MembershipFee.get(fee_id)

    if fee is None:
        flash('Ein Beitrag mit dieser ID existiert nicht!', 'error')
        abort(404)

    form = FeeApplyForm()
    if form.is_submitted():
        affected_users = post_transactions_for_membership_fee(
            fee, current_user)

        session.commit()

        flash(f"{len(affected_users)} neue Buchungen erstellt.", "success")

        return redirect(url_for(".membership_fees"))

    table = UsersDueTable(data_url=url_for('.membership_fee_users_due_json', fee_id=fee.id))
    return render_template('finance/membership_fee_book.html', form=form,
                           page_title='Beitrag buchen', table=table)


@bp.route("/membership_fee/<int:fee_id>/users_due_json")
def membership_fee_users_due_json(fee_id):
    fee = MembershipFee.get(fee_id)

    if fee is None:
        abort(404)

    affected_users = post_transactions_for_membership_fee(
        fee, current_user, simulate=True)

    fee_amount = {'value': str(fee.regular_fee) + '€',
                  'is_positive': (fee.regular_fee < 0)}
    fee_description = localized(
        finance.membership_fee_description.format(fee_name=fee.name).to_json())

    T = UsersDueTable
    return jsonify(items=[{
        'user_id': user['id'],
        'user': T.user.value(
            title=str(user['name']),
            href=url_for("user.user_show", user_id=user['id'])
        ),
        'amount': fee_amount,
        'description': fee_description,
        'valid_on': fee.ends_on,
        'fee_account_id': T.fee_account_id.value(
            title=str(user['fee_account_id']),
            href=url_for(".accounts_show", account_id=user['fee_account_id'])
        ),
    } for user in affected_users])


@bp.route("/membership_fees", methods=['GET', 'POST'])
@nav.navigate("Beiträge", icon='fa-hand-holding-usd')
def membership_fees():
    table = MembershipFeeTable(data_url=url_for('.membership_fees_json'))
    return render_template('finance/membership_fees.html', table=table)


@bp.route("/membership_fees/json")
@access.require('finance_change')
def membership_fees_json():
    T = MembershipFeeTable
    return jsonify(items=[
        {
            'name': localized(membership_fee.name),
            'regular_fee': money_filter(
                membership_fee.regular_fee),
            'payment_deadline': membership_fee.payment_deadline.days,
            'payment_deadline_final': membership_fee.payment_deadline_final.days,
            'begins_on': date_format(membership_fee.begins_on, formatter=date_filter),
            'ends_on': date_format(membership_fee.ends_on, formatter=date_filter),
            'actions': [
                T.actions.single_value(
                    href=url_for(".transactions_all",
                                 filter="all",
                                 after=membership_fee.begins_on,
                                 before=membership_fee.ends_on),
                    title='Finanzübersicht',
                    icon='fa-euro-sign', btn_class='btn-success btn-sm'
                ),
                T.actions.single_value(
                    href=url_for(".membership_fee_book", fee_id=membership_fee.id),
                    title='Buchen', icon='fa-book', btn_class='btn-warning btn-sm'
                ),
                T.actions.single_value(
                    href=url_for(".membership_fee_edit", fee_id=membership_fee.id),
                    title='Bearbeiten', icon='fa-edit', btn_class='btn-primary btn-sm'
                )
            ]
        } for membership_fee in
        MembershipFee.q.order_by(MembershipFee.begins_on.desc()).all()])


@bp.route('/membership_fee/create', methods=("GET", "POST"))
@access.require('finance_change')
def membership_fee_create():
    previous_fee = get_last_membership_fee(session)
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
    fee = MembershipFee.get(fee_id)

    if fee is None:
        flash('Ein Beitrag mit dieser ID existiert nicht!', 'error')
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
    finance.end_payment_in_default_memberships(current_user)

    users_pid_membership_all, users_membership_terminated_all = \
        finance.get_users_with_payment_in_default(session)

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
    return {
        "accounts": [
            {
                "account_id": account.id,
                "account_name": localized(account.name),
                "account_type": account.type,
            }
            for account in get_system_accounts(session)
        ]
    }


@bp.route('/json/accounts/user-search')
def json_accounts_user_search():
    query = request.args['query']
    results = session.query(
        Account.id, User.id, User.login, User.name
    ).select_from(User).join(Account).filter(
        or_(func.lower(User.name).like(func.lower(f"%{query}%")),
            func.lower(User.login).like(func.lower(f"%{query}%")),
            cast(User.id, Text).like(f"{query}%"))
    ).all()
    accounts = [
        {"account_id": account_id,
         "user_id": user_id,
         "user_login": user_login,
         "user_name": user_name}
        for account_id, user_id, user_login, user_name in results
    ]
    return jsonify(accounts=accounts)


@bp.route('/membership_fees/payments_in_default_csv')
@access.require('finance_change')
def csv_payments_in_default():
    csv_str = get_pid_csv()

    output = make_response(csv_str)
    output.headers["Content-Disposition"] = "attachment; filename=payments_in_default.csv"
    output.headers["Content-type"] = "text/csv"

    return output


@bp.route('/membership_fees/payment_reminder_mail', methods=("GET", "POST"))
@access.require('finance_change')
def payment_reminder_mail():
    form = ConfirmPaymentReminderMail()

    if form.validate_on_submit() and form.confirm.data:
        last_import_date = get_last_import_date(session).date()
        if last_import_date >= utcnow().date() - timedelta(days=3):
            negative_users = get_negative_members()
            user_send_mails(negative_users, MemberNegativeBalance())

            flash("Zahlungserinnerungen gesendet.", "success")
        else:
            flash("Letzter Bankimport darf nicht älter als 3 Tage sein.", "error")

        return redirect(url_for(".membership_fees"))

    form_args = {
        'form': form,
        'cancel_to': url_for('.membership_fees'),
        'submit_text': 'Mails versenden',
        'actions_offset': 0,
        'form_render_mode': 'basic',
        'field_render_mode': 'basic',
    }

    return render_template('generic_form.html',
                           page_title="Zahlungserinnerungen per E-Mail versenden",
                           form_args=form_args,
                           form=form)
