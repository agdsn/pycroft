#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import csv
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from itertools import chain

import pytest
from flask import url_for
from sqlalchemy.orm import Session
from sqlalchemy import select

import tests.factories as f
from pycroft import Config
from pycroft.lib.finance import simple_transaction
from pycroft.model.finance import (
    BankAccount,
    BankAccountActivity,
    Account,
    Transaction,
    Split,
)
from tests.frontend.assertions import TestClient
from .fixture_helpers import serialize_formdata


pytestmark = pytest.mark.usefixtures("treasurer_logged_in", "session")


@pytest.fixture(scope="module", autouse=True)
def client(module_test_client: TestClient) -> TestClient:
    return module_test_client


@pytest.fixture(scope="module", autouse=True)
def bank_account(module_session: Session) -> BankAccount:
    """Bank account with some unassigned activities."""
    bank_account = f.BankAccountFactory(name="Main bank account")
    f.BankAccountActivityFactory.create_batch(3, bank_account=bank_account)
    module_session.flush()
    return bank_account


@pytest.fixture(scope="module", autouse=True)
def config(module_session: Session, bank_account) -> Config:
    """Config ensuring no other bank accounts will be set up"""
    config = f.ConfigFactory(
        membership_fee_bank_account=bank_account,
    )
    module_session.flush()
    return config


@pytest.fixture(scope="module", autouse=True)
def activity(bank_account) -> BankAccountActivity:
    return bank_account.activities[0]


class TestBankAccount:
    def test_get_bank_accounts(self, client: TestClient):
        with client.renders_template("finance/bank_accounts_list.html"):
            client.assert_ok("finance.bank_accounts_list")

    def test_bank_accounts_list(self, client: TestClient, bank_account: BankAccount):
        response = client.assert_ok("finance.bank_accounts_list_json")
        assert "items" in (j := response.json)
        assert [account["name"] for account in j["items"]] == [bank_account.name]

    def test_bank_account_unassigned_activities(
        self, client: TestClient, bank_account: BankAccount
    ):
        response = client.assert_ok("finance.bank_accounts_activities_json")
        assert "items" in (j := response.json)
        assert len(j["items"]) == 3

    def test_bank_account_create_get(self, client: TestClient):
        client.assert_ok("finance.bank_accounts_create")

    def test_bank_account_create_post(self, client: TestClient):
        bank_account: BankAccount = f.BankAccountFactory.build()
        with client.flashes_message("Bankkonto", category="success"):
            client.assert_redirects(
                "finance.bank_accounts_create",
                method="POST",
                data={
                    "name": bank_account.name,
                    "bank": bank_account.bank,
                    "account_number": bank_account.account_number,
                    "routing_number": bank_account.routing_number,
                    "iban": bank_account.iban,
                    "bic": bank_account.bic,
                    "fints": bank_account.fints_endpoint,
                },
                expected_location=url_for("finance.bank_accounts_list"),
            )


@pytest.fixture(scope="module", autouse=True)
def account(module_session: Session) -> Account:
    account = f.AccountFactory(name="Mitgliedsbeiträge", type="EXPENSE")
    module_session.flush()
    return account


class TestActivityEdit:
    @pytest.fixture(scope="class")
    def transaction(
        self, class_session, bank_account, account, activity
    ) -> Transaction:
        transaction = f.TransactionFactory(bank_account_activities=[activity])
        activity.split = Split(
            account=bank_account.account, transaction=transaction, amount=100
        )
        Split(account=account, transaction=transaction, amount=-100)
        class_session.add_all([activity, transaction])
        class_session.flush()
        assert activity in transaction.bank_account_activities
        return transaction

    def test_edit_nonexistent_activity(self, client: TestClient):
        client.assert_url_response_code(
            url_for("finance.bank_account_activities_edit", activity_id=9999),
            code=404,
        )

    def test_edit_unassigned_activity(
        self,
        session,
        client: TestClient,
        activity: BankAccountActivity,
        account: Account,
    ):
        assert activity.transaction is None
        formdata = {
            "account_id": account.id,  # TODO add a finance account
            "description": "Test description",
        }
        # formdata for `BankAccountActivityEditForm`
        client.assert_url_redirects(
            url_for("finance.bank_account_activities_edit", activity_id=activity.id),
            method="POST",
            data=formdata,
            expected_location=url_for("finance.bank_accounts_list"),
        )
        session.refresh(activity)
        assert activity.transaction is not None

    def test_edit_unassigned_activity_bad_formdata(self, client: TestClient, activity):
        # TODO check for 400 (or even better 422) instead of 200
        client.assert_url_ok(
            url_for("finance.bank_account_activities_edit", activity_id=activity.id),
            method="POST",
            data={},
        )

    def test_edit_assigned_activity(
        self, client, session, activity, transaction, account
    ):
        # read-only form
        with client.renders_template("generic_form.html"), client.flashes_message(
            "bereits zugewiesen", "warning"
        ):
            client.assert_url_ok(
                url_for("finance.bank_account_activities_edit", activity_id=activity.id)
            )


class TestAccount:
    @pytest.fixture(scope="class")
    def member_account(self, treasurer) -> Account:
        return treasurer.account

    @pytest.fixture(scope="class", autouse=True)
    def member_account_transactions(
        self, member_account, class_session, bank_account, config, treasurer
    ) -> tuple[Transaction, Transaction]:
        kw = {"author": treasurer, "valid_on": date.today(), "amount": Decimal(100)}
        t1 = simple_transaction(
            description="Mitgliedsbeitrag",
            credit_account=config.membership_fee_account,
            debit_account=member_account,
            **kw,
        )
        t2 = simple_transaction(
            description="Zahlung",
            credit_account=member_account,
            debit_account=bank_account.account,
            **kw,
        )
        class_session.add_all([t1, t2])
        class_session.flush()
        return t1, t2

    def test_list_accounts(self, session, client: TestClient, account):
        with client.renders_template("finance/accounts_list.html") as recorded:
            client.assert_ok("finance.accounts_list")

        assert len(recorded) == 1
        [(_template, ctx)] = recorded
        accounts_by_type = ctx["accounts"]
        assert account in [*chain(*accounts_by_type.values())]

    def test_user_account_show(self, client, member_account):
        with client.renders_template("finance/accounts_show.html"):
            client.assert_url_ok(
                url_for("finance.accounts_show", account_id=member_account.id)
            )

    def test_nonexistent_account_show(self, client):
        client.assert_url_response_code(
            url_for("finance.accounts_show", account_id=9999), 404
        )

    def test_system_account_show(self, client, config):
        with client.renders_template("finance/accounts_show.html"):
            client.assert_url_ok(
                url_for(
                    "finance.accounts_show", account_id=config.membership_fee_account.id
                )
            )

    @pytest.mark.parametrize(
        "query_args",
        [
            {},
            {"limit": 1},
            {"sort": "description", "order": "desc"},
            {"splitted": True, "sort": "soll_description", "order": "desc"},
        ],
    )
    def test_accounts_show_json(self, client: TestClient, member_account, query_args):
        resp = client.assert_url_ok(
            url_for(
                "finance.accounts_show_json", account_id=member_account.id, **query_args
            ),
        )
        assert (j := resp.json)["name"] == member_account.name
        assert (i := j["items"])
        assert i["total"] == 2
        if not query_args.get("splitted", False):
            assert len(i["rows"]) == query_args.get("limit", 2)

    def test_get_system_accounts(self, config, client):
        accounts = client.assert_ok("finance.json_accounts_system").json["accounts"]
        assert len(accounts) > 0
        assert config.membership_fee_account.name in [
            a["account_name"] for a in accounts
        ]
        assert config.membership_fee_account.id in [a["account_id"] for a in accounts]

    @pytest.mark.parametrize(
        "query_from_account",
        [lambda a: a.user.name, lambda a: a.user.id, lambda a: a.user.login],
    )
    def test_search_user_account(self, member_account, client, query_from_account):
        query = query_from_account(member_account)
        resp = client.assert_url_ok(
            url_for("finance.json_accounts_user_search", query=query)
        )
        assert len(a := resp.json["accounts"]) == 1
        assert a[0]["account_id"] == member_account.id

    @pytest.mark.parametrize("invert", [False, True])
    def test_user_account_balance_json(self, member_account, client, invert):
        resp = client.assert_url_ok(
            url_for("finance.balance_json", account_id=member_account.id, invert=invert)
        )
        # we have 2 transactions on the same day, but on that day the balance is 0.
        # so we expect two data points for that day, both proclaiming a balance of `0`.
        assert len(items := resp.json["items"]) == 2
        assert [i["balance"] for i in items] == [0, 0]


class TestAccountToggleLegacy:
    @pytest.fixture(scope="class")
    def legacy_account(self, class_session: Session) -> Account:
        account = f.AccountFactory(type="ASSET", legacy=True)
        class_session.flush()
        return account

    def test_account_toggle_legacy_404(self, client: TestClient):
        client.assert_url_response_code(
            url_for("finance.account_toggle_legacy", account_id=9999), code=404
        )

    def test_account_set_legacy(self, session, client: TestClient, account: Account):
        assert account.legacy is False
        client.assert_url_redirects(
            url_for("finance.account_toggle_legacy", account_id=account.id),
            expected_location=url_for("finance.accounts_show", account_id=account.id),
        )
        session.refresh(account)
        assert account.legacy is True

    def test_account_unset_legacy(
        self, session, client: TestClient, legacy_account: Account
    ):
        assert legacy_account.legacy is True
        client.assert_url_redirects(
            url_for("finance.account_toggle_legacy", account_id=legacy_account.id),
            expected_location=url_for(
                "finance.accounts_show", account_id=legacy_account.id
            ),
        )
        session.refresh(legacy_account)
        assert legacy_account.legacy is False


class TestAccountCreate:
    def test_account_create_get(self, client: TestClient):
        with client.renders_template("finance/accounts_create.html"):
            client.assert_ok("finance.accounts_create")

    def test_account_create_invalid_post(self, client: TestClient):
        client.assert_url_ok(url_for("finance.accounts_create"), method="POST", data={})

    def test_account_create_valid_post(self, session, client: TestClient):
        formdata = {
            "name": "Test (newly created)",
            "type": "ASSET",
        }
        client.assert_url_redirects(
            url_for("finance.accounts_create"),
            method="POST",
            data=formdata,
            expected_location=url_for("finance.accounts_list"),
        )
        acc = session.scalars(
            select(Account).filter_by(name="Test (newly created)")
        ).one_or_none()
        assert acc is not None
        assert not acc.legacy


class TestPaymentInDefault:
    def test_get_handle_pid(self, client: TestClient):
        with client.renders_template("generic_form.html"):
            client.assert_ok("finance.handle_payments_in_default")

    def test_post_handle_pid(self, client: TestClient):
        with client.flashes_message("Zahlungsrückstände behandelt", "success"):
            client.assert_url_redirects(
                url_for("finance.handle_payments_in_default"),
                method="POST",
                data={},
                expected_location=url_for("finance.membership_fees"),
            )

    def test_get_payment_in_default_csv(self, client: TestClient):
        resp = client.assert_url_ok(url_for("finance.csv_payments_in_default"))
        assert resp.headers["Content-Type"] == "text/csv"
        assert list(csv.DictReader(StringIO(resp.data.decode()))) == []


class TestPaymentReminderMail:
    def test_get_payment_reminder_mail_get(self, client: TestClient):
        with client.renders_template("generic_form.html"):
            client.assert_ok("finance.payment_reminder_mail")

    def test_get_payment_reminder_mail_post_import_too_old(self, client: TestClient):
        with client.flashes_message("darf nicht älter als .* sein", "error"):
            client.assert_redirects(
                "finance.payment_reminder_mail", method="POST", data={"confirm": True}
            )

    def test_get_payment_reminder_mail_post(
        self, session, client: TestClient, activity
    ):
        activity.imported_at = datetime.now()
        session.add(activity)
        session.flush()
        with client.flashes_message("erinnerungen gesendet", "success"):
            client.assert_redirects(
                "finance.payment_reminder_mail", method="POST", data={"confirm": True}
            )


class TestTransactionsShow:
    @pytest.fixture(scope="class")
    def transaction(self, class_session) -> Transaction:
        t = f.TransactionFactory()
        class_session.flush()
        return t

    def test_transactions_show(self, client: TestClient, transaction: Transaction):
        with client.renders_template("finance/transactions_show.html"):
            client.assert_url_ok(
                url_for("finance.transactions_show", transaction_id=transaction.id)
            )

    def test_transactions_show_404(self, client: TestClient):
        client.assert_url_response_code(
            url_for("finance.transactions_show", transaction_id=9999), code=404
        )

    def test_transactions_show_json(self, client: TestClient, transaction: Transaction):
        resp = client.assert_url_ok(
            url_for("finance.transactions_show_json", transaction_id=transaction.id)
        )
        # 1 simple transaction = 2 splits
        assert len(resp.json["items"]) == 2


class TestNoTransactionsUnconfirmed:
    def test_transactions_unconfirmed(self, client: TestClient):
        with client.renders_template("finance/transactions_unconfirmed.html"):
            client.assert_ok("finance.transactions_unconfirmed")

    def test_transactions_unconfirmed_json(self, client: TestClient):
        resp = client.assert_url_ok(url_for("finance.transactions_unconfirmed_json"))
        assert len(resp.json["items"]) == 0


@pytest.fixture(scope="class")
def unconfirmed_transaction(class_session) -> Transaction:
    t = f.TransactionFactory(confirmed=False)
    class_session.flush()
    return t


@pytest.fixture(scope="class")
def confirmed_transaction(class_session) -> Transaction:
    t = f.TransactionFactory(confirmed=True)
    class_session.flush()
    return t


@pytest.mark.usefixtures("unconfirmed_transaction")
class TestUnconfirmedTransaction:
    def test_transactions_unconfirmed(self, client: TestClient):
        with client.renders_template("finance/transactions_unconfirmed.html"):
            client.assert_ok("finance.transactions_unconfirmed")

    def test_transactions_unconfirmed_json(self, client: TestClient):
        resp = client.assert_url_ok(url_for("finance.transactions_unconfirmed_json"))
        assert len(resp.json["items"]) == 1

    def test_transactions_all(self, client: TestClient):
        with client.renders_template("finance/transactions_overview.html"):
            client.assert_ok("finance.transactions_all")

    @pytest.mark.parametrize(
        "query_args",
        [
            {},
            {"filter": "nonuser"},
            {"filter": "user"},
            {"after": "2000-01-15"},
            {"before": "2060-01-01"},
        ],
    )
    def test_transactions_all_json(
        self, client: TestClient, query_args: dict[str, str]
    ):
        resp = client.assert_url_ok(
            url_for("finance.transactions_all_json", **query_args)
        )
        assert resp.json["items"]


class TestConfirmation:
    @pytest.mark.parametrize("method", ["GET", "POST"])
    def test_confirmation_post(
        self, client: TestClient, unconfirmed_transaction: Transaction, method: str
    ):
        client.assert_url_redirects(
            url_for(
                "finance.transaction_confirm", transaction_id=unconfirmed_transaction.id
            ),
            method=method,
            expected_location=url_for("finance.transactions_unconfirmed"),
        )

    def test_confirm_nonexistent(self, client: TestClient):
        with client.flashes_message("existiert nicht", "error"):
            client.assert_url_response_code(
                url_for("finance.transaction_confirm", transaction_id=9999), code=404
            )

    def test_confirm_confirmed_transaction(
        self, client: TestClient, confirmed_transaction: Transaction
    ):
        with client.flashes_message("bereits bestätigt", "error"):
            client.assert_url_response_code(
                url_for(
                    "finance.transaction_confirm",
                    transaction_id=confirmed_transaction.id,
                ),
                code=400,
            )

    def test_transaction_confirm_all_get(self, client: TestClient):
        with client.renders_template("generic_form.html"):
            client.assert_ok("finance.transaction_confirm_all")

    def test_transaction_confirm_all_post(self, client: TestClient):
        client.assert_url_redirects(
            url_for("finance.transaction_confirm_all"),
            method="POST",
            data={},
            expected_location=url_for("finance.transactions_unconfirmed"),
        )


class TestTransactionDelete:
    @pytest.fixture(scope="class", autouse=True)
    def transaction(self, class_session) -> Transaction:
        t = f.TransactionFactory(confirmed=False)
        class_session.flush()
        return t

    def test_transaction_delete_post(
        self, client: TestClient, transaction: Transaction
    ):
        assert transaction.id is not None
        client.assert_url_redirects(
            url_for("finance.transaction_delete", transaction_id=transaction.id),
            method="POST",
            data={},
            expected_location=url_for("finance.transactions_unconfirmed"),
        )

    def test_transaction_delete_404(self, client: TestClient):
        client.assert_url_response_code(
            url_for("finance.transaction_delete", transaction_id=9999), code=404
        )

    def test_transaction_delete_already_confirmed(
        self, client: TestClient, confirmed_transaction: Transaction
    ):
        with client.flashes_message("bereits bestätigt", "error"):
            client.assert_url_response_code(
                url_for(
                    "finance.transaction_delete",
                    transaction_id=confirmed_transaction.id,
                ),
                code=400,
            )

    def test_transaction_delete_get(self, client, transaction: Transaction):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(
                url_for("finance.transaction_delete", transaction_id=transaction.id)
            )


class TestTransactionCreate:
    def test_transaction_create_get(self, client: TestClient):
        with client.renders_template("finance/transactions_create.html"):
            client.assert_ok("finance.transactions_create")

    @pytest.fixture(scope="class")
    def account1(self, class_session):
        return f.AccountFactory()

    @pytest.fixture(scope="class")
    def account2(self, class_session):
        return f.AccountFactory()

    def test_transaction_create_post(
        self, client: TestClient, session: Session, account1, account2
    ):
        # see TransactionCreateForm
        formdata = serialize_formdata(
            {
                "valid_on": "2021-01-01",
                "description": "Test",
                "splits": [
                    {"account": "-", "account_id": account1.id, "amount": 1000},
                    {"account": "-", "account_id": account2.id, "amount": -1000},
                ],
            }
        )
        client.assert_url_redirects(
            url_for("finance.transactions_create"),
            method="POST",
            data=formdata,
            # return url depends on id of created transaction
        )
