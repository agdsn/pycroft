#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import pytest
from flask import url_for
from sqlalchemy.orm import Session

import tests.factories as f
from pycroft import Config
from pycroft.model.finance import (
    BankAccount,
    BankAccountActivity,
    Account,
    Transaction,
    Split,
)
from tests.frontend.assertions import TestClient


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
