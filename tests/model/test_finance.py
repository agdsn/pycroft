# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy.exc import IntegrityError

from pycroft.model.finance import Account, IllegalTransactionError
from pycroft.model.user import User
from tests import FixtureDataTestBase
from pycroft.model import finance, session
from tests.fixtures.dummy.finance import AccountData
from tests.fixtures.dummy.user import UserData


class Test_010_TransactionSplits(FixtureDataTestBase):
    datasets = [AccountData, UserData]

    def setUp(self):
        super(Test_010_TransactionSplits, self).setUp()
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
