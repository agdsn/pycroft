import unittest
from pycroft import model
from pycroft.model import session, finance
from datetime import datetime


class Test_010_TransactionSplits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        session.reinit_session("sqlite://")
        model.drop_db_model()
        model.create_db_model()
        cls.account = finance.FinanceAccount(name="Testaccount", type="EXPENSE")
        cls.s = session.session
        cls.s.add(cls.account)
        cls.s.commit()

    def tearDown(self):
        super(Test_010_TransactionSplits, self).tearDown()
        print "bla"
        self.s.remove()

    def test_0010_empty_transaction(self):
        tr = finance.Transaction(description="Transaction1", transaction_date=datetime.now())
        self.s.add(tr)
        self.s.commit()
        self.assertEqual(finance.Transaction.q.filter_by(description="Transaction1").count(), 1)

    def test_0020_fail_on_unbalanced(self):
        tr = finance.Transaction(description="Transaction2", transaction_date=datetime.now())
        self.s.add(tr)
        self.s.commit()
        sp1 = finance.Split(amount=100, account=self.account, transaction=tr)
        self.s.add(sp1)
        self.assertRaisesRegexp(Exception, 'Transaction "Transaction2" is not balanced!', self.s.commit)
        #self.s.rollback()

    def test_0030_insert_balanced(self):
        tr = finance.Transaction(description="Transaction3", transaction_date=datetime.now())
        self.s.add(tr)
        self.s.commit()
        sp1 = finance.Split(amount=100, account=self.account, transaction=tr)
        sp2 = finance.Split(amount=-100, account=self.account, transaction=tr)
        self.s.add(sp1)
        self.s.add(sp2)
        self.s.commit()

    def test_0040_delete_cascade(self):
        tr = finance.Transaction(description="Transaction4", transaction_date=datetime.now())
        sp1 = finance.Split(amount=234, account=self.account, transaction=tr)
        sp2 = finance.Split(amount=-234, account=self.account, transaction=tr)
        self.s.add(tr)
        self.s.add(sp1)
        self.s.add(sp2)
        self.s.commit()

        tr = finance.Transaction.q.filter_by(description="Transaction4").one()
        self.s.delete(tr)
        self.s.commit()

        self.assertEqual(finance.Split.q.filter_by(amount=-234).count(), 0)