from pycroft.model.finance import FinanceAccount, UnbalancedTransactionError, \
    Transaction, Split
from pycroft.model.user import User
from tests import FixtureDataTestBase
from pycroft.model import session, finance
from datetime import datetime
from tests.model.fixtures.finance_fixtures import FinanceAccountData, UserData


class Test_010_TransactionSplits(FixtureDataTestBase):
    datasets = [FinanceAccountData, UserData]

    def setUp(self):
        super(Test_010_TransactionSplits, self).setUp()
        self.author = User.q.one()
        self.account = FinanceAccount.q.one()

    def tearDown(self):
        Split.q.delete()
        Transaction.q.delete()
        super(Test_010_TransactionSplits, self).tearDown()

    def create_transaction(self):
        return finance.Transaction(
            description=u"Transaction",
            author=self.author,
            transaction_date=datetime.now()
        )

    def create_split(self, transaction, amount):
        return finance.Split(
            amount=amount,
            account=self.account,
            transaction=transaction
        )

    def test_0010_empty_transaction(self):
        t = self.create_transaction()
        session.session.add(t)
        try:
            session.session.commit()
        except UnbalancedTransactionError:
            session.session.rollback()
            self.fail()

    def test_0020_fail_on_unbalanced(self):
        t = self.create_transaction()
        s = self.create_split(t, 100)
        session.session.add_all([t, s])
        self.assertRaises(UnbalancedTransactionError, session.session.commit)
        session.session.rollback()

    def test_0030_insert_balanced(self):
        t = self.create_transaction()
        s1 = self.create_split(t, 100)
        s2 = self.create_split(t, -100)
        session.session.add_all([t, s1, s2])
        try:
            session.session.commit()
        except UnbalancedTransactionError:
            session.session.rollback()
            self.fail()

    def test_0040_delete_cascade(self):
        t = self.create_transaction()
        s1 = self.create_split(t, 100)
        s2 = self.create_split(t, -100)
        session.session.add_all([t, s1, s2])
        session.session.commit()
        session.session.delete(t)
        session.session.commit()
        self.assertEqual(finance.Split.q.count(), 0)
