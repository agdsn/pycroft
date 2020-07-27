# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from pycroft.model.finance import (
    Account, BankAccount, BankAccountActivity, IllegalTransactionError)
from pycroft.model.user import User
from tests import FixtureDataTestBase
from pycroft.model import finance, session
from tests.fixtures.dummy.finance import AccountData, BankAccountData
from tests.fixtures.dummy.user import UserData


class FinanceModelTest(FixtureDataTestBase):
    def setUp(self):
        super(FinanceModelTest, self).setUp()
        self.author = User.q.filter_by(login=UserData.privileged.login).one()
        self.asset_account = Account.q.filter_by(
            name=AccountData.dummy_asset.name
        ).one()
        self.revenue_account = Account.q.filter_by(
            name=AccountData.dummy_revenue.name
        ).one()
        self.liability_account = Account.q.filter_by(
            name=AccountData.dummy_liability.name
        ).one()

    def create_transaction(self):
        return finance.Transaction(
            description=u"Transaction",
            author=self.author
        )

    def create_split(self, transaction, account, amount):
        return finance.Split(
            amount=amount,
            account=account,
            transaction=transaction
        )


class TestTransactionSplits(FinanceModelTest):
    datasets = (AccountData, UserData)

    def test_0010_empty_transaction(self):
        t = self.create_transaction()
        session.session.add(t)
        self.assertRaises(IllegalTransactionError, session.session.commit)
        session.session.rollback()

    def test_0020_fail_on_unbalanced(self):
        t = self.create_transaction()
        s = self.create_split(t, self.asset_account, 100)
        session.session.add_all([t, s])
        self.assertRaises(IllegalTransactionError, session.session.commit)
        session.session.rollback()

    def test_0030_insert_balanced(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.asset_account, 100)
        s2 = self.create_split(t, self.revenue_account, -100)
        session.session.add_all([t, s1, s2])
        try:
            session.session.commit()
        except IllegalTransactionError:
            session.session.rollback()
            self.fail()

    def test_0040_delete_cascade(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.asset_account, 100)
        s2 = self.create_split(t, self.revenue_account, -100)
        session.session.add_all([t, s1, s2])
        session.session.commit()
        session.session.delete(t)
        session.session.commit()
        self.assertEqual(finance.Split.q.count(), 0)

    def test_0050_fail_on_self_transaction(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.asset_account, 100)
        s2 = self.create_split(t, self.asset_account, -100)
        session.session.add_all([t, s1, s2])
        self.assertRaises(IntegrityError, session.session.commit)
        session.session.rollback()

    def test_0050_fail_on_multiple_split_same_account(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.asset_account, 100)
        s2 = self.create_split(t, self.revenue_account, -50)
        s3 = self.create_split(t, self.revenue_account, -50)
        session.session.add_all([t, s1, s2, s3])
        self.assertRaises(IntegrityError, session.session.commit)
        session.session.rollback()

    def test_unbalance_with_insert(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.asset_account, 100)
        s2 = self.create_split(t, self.revenue_account, -100)
        session.session.add_all([t, s1, s2])
        session.session.commit()
        s3 = self.create_split(t, self.liability_account, 50)
        session.session.add(s3)
        self.assertRaises(IllegalTransactionError, session.session.commit)

    def test_unbalance_with_update(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.asset_account, 100)
        s2 = self.create_split(t, self.revenue_account, -100)
        session.session.add_all([t, s1, s2])
        session.session.commit()
        s2.amount = -50
        self.assertRaises(IllegalTransactionError, session.session.commit)

    def test_unbalance_with_delete(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.asset_account, 100)
        s2 = self.create_split(t, self.revenue_account, -100)
        session.session.add_all([t, s1, s2])
        session.session.commit()
        session.session.delete(s2)
        self.assertRaises(IllegalTransactionError, session.session.commit)


class TestBankAccountActivity(FinanceModelTest):
    datasets = (AccountData, BankAccountData, UserData)

    def setUp(self):
        super(TestBankAccountActivity, self).setUp()
        self.bank_account = BankAccount.q.filter_by(
            iban=BankAccountData.dummy.iban
        ).one()
        session.session.execute("SET CONSTRAINTS bank_account_activity_matches_referenced_split_trigger IMMEDIATE")

    def tearDown(self):
        session.session.execute("SET CONSTRAINTS bank_account_activity_matches_referenced_split_trigger DEFERRED")
        super(TestBankAccountActivity, self).tearDown()

    def create_activity(self, amount):
        return BankAccountActivity(
            bank_account=self.bank_account,
            reference='Reference',
            other_name='John Doe',
            other_account_number='0123456789',
            other_routing_number='01245',
            amount=amount,
            imported_at=datetime.utcnow(),
            posted_on=datetime.utcnow().date(),
            valid_on=datetime.utcnow().date(),
        )

    def test_correct(self):
        bank_account_account = self.bank_account.account
        t = self.create_transaction()
        s1 = self.create_split(t, self.asset_account, 100)
        s2 = self.create_split(t, bank_account_account, -100)
        a = self.create_activity(-100)
        a.split = s2
        session.session.add_all((t, s1, s2, a))
        session.session.commit()

    def test_wrong_split_amount(self):
        bank_account_account = self.bank_account.account
        t = self.create_transaction()
        s1 = self.create_split(t, self.asset_account, 100)
        s2 = self.create_split(t, bank_account_account, -100)
        a = self.create_activity(-50)
        a.split = s2
        session.session.add_all((t, s1, s2, a))
        self.assertRaises(IntegrityError, session.session.commit)

    def test_wrong_split_account(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.asset_account, 100)
        s2 = self.create_split(t, self.revenue_account, -100)
        a = self.create_activity(-100)
        a.split = s2
        session.session.add_all((t, s1, s2, a))
        self.assertRaises(IntegrityError, session.session.commit)
