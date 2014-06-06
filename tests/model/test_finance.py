from pycroft.model.finance import FinanceAccount, IllegalTransactionError, \
    Transaction, Split
from pycroft.model.user import User
from tests import FixtureDataTestBase
from pycroft.model import finance, session
from datetime import datetime
from tests.model.fixtures.finance_fixtures import FinanceAccountData, UserData


class Test_010_TransactionSplits(FixtureDataTestBase):
    datasets = [FinanceAccountData, UserData]

    def setUp(self):
        super(Test_010_TransactionSplits, self).setUp()
        self.author = User.q.one()
        self.account1 = FinanceAccount.q.filter(
            FinanceAccount.name == FinanceAccountData.Dummy1.name
        ).one()
        self.account2 = FinanceAccount.q.filter(
            FinanceAccount.name == FinanceAccountData.Dummy2.name
        ).one()

    def tearDown(self):
        Split.q.delete()
        Transaction.q.delete()
        super(Test_010_TransactionSplits, self).tearDown()

    def create_transaction(self):
        return finance.Transaction(
            description=u"Transaction",
            author=self.author,
            transaction_date=datetime.utcnow()
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
        s = self.create_split(t, self.account1, 100)
        session.session.add_all([t, s])
        self.assertRaises(IllegalTransactionError, session.session.commit)
        session.session.rollback()

    def test_0030_insert_balanced(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.account1, 100)
        s2 = self.create_split(t, self.account2, -100)
        session.session.add_all([t, s1, s2])
        try:
            session.session.commit()
        except IllegalTransactionError:
            session.session.rollback()
            self.fail()

    def test_0040_delete_cascade(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.account1, 100)
        s2 = self.create_split(t, self.account2, -100)
        session.session.add_all([t, s1, s2])
        session.session.commit()
        session.session.delete(t)
        session.session.commit()
        self.assertEqual(finance.Split.q.count(), 0)

    def test_0050_fail_on_self_transaction(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.account1, 100)
        s2 = self.create_split(t, self.account1, -100)
        session.session.add_all([t, s1, s2])
        self.assertRaises(IllegalTransactionError, session.session.commit)
        session.session.rollback()

    def test_0050_fail_on_multiple_split_same_account(self):
        t = self.create_transaction()
        s1 = self.create_split(t, self.account1, 100)
        s2 = self.create_split(t, self.account2, -50)
        s2 = self.create_split(t, self.account2, -50)
        session.session.add_all([t, s1, s2])
        self.assertRaises(IllegalTransactionError, session.session.commit)
        session.session.rollback()
