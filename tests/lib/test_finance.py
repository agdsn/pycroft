from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from pycroft.model.user import User
from tests import FixtureDataTestBase
from tests.lib.fixtures.finance_fixtures import FinanceAccountData, \
    JournalData, SemesterData, UserData
from pycroft.lib.finance import import_journal_csv, get_current_semester, \
    simple_transaction, transferred_amount, cleanup_description
from pycroft.model.finance import FinanceAccount, Journal, JournalEntry, \
    Transaction
from datetime import date, timedelta


class Test_010_Journal(FixtureDataTestBase):

    datasets = [FinanceAccountData, JournalData, SemesterData, UserData]

    def setUp(self):
        super(Test_010_Journal, self).setUp()
        self.asset_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.Asset.name
        ).one()
        self.liability_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.Liability.name
        ).one()
        self.expense_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.Expense.name
        ).one()
        self.revenue_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.Revenue.name
        ).one()
        self.journal = Journal.q.filter_by(
            account_number=JournalData.Journal1.account_number
        ).one()
        self.author = User.q.filter_by(
            login=UserData.Dummy.login
        ).one()

    def test_0010_import_journal_csv(self):
        """
        This test should verify that the csv import works as expected.
        """
        f = open("example/example.csv")
        import_journal_csv(f, date(2013, 1, 5))

        journal = (Journal.q
                   .filter(Journal.iban == JournalData.Journal1.iban)
                   .one())

        # test for correct dataimport
        entry = JournalEntry.q.filter(
            JournalEntry.journal == journal,
            JournalEntry.original_description == u"0000-3, SCH, AAA, ZW41D/01 99 1, SS 13").first()
        self.assertEquals(entry.other_account_number, "12345678")
        self.assertEquals(entry.other_routing_number, "80040400")
        self.assertEquals(entry.other_name, u"SCH, AAA")
        self.assertEquals(entry.amount, 900000)
        self.assertEquals(entry.transaction_date, date(2013, 1, 2))
        self.assertEquals(entry.valid_date, date(2013, 1, 2))

        # verify that the right year gets chosen for the transaction
        entry = JournalEntry.q.filter(
            JournalEntry.journal == journal,
            JournalEntry.original_description == u"Pauschalen").first()
        self.assertEquals(entry.transaction_date, date(2012, 12, 24))
        self.assertEquals(entry.valid_date, date(2012, 12, 24))

        # verify that a negative amount is imported correctly
        self.assertEquals(entry.amount, -600)

        # verify that the correct transaction year gets chosen for a valuta date
        # which is in the next year
        entry = JournalEntry.q.filter(
            JournalEntry.journal == journal,
            JournalEntry.original_description == u"BESTELLUNG SUPERMEGATOLLER SERVER").first()
        self.assertEquals(entry.transaction_date, date(2012, 12, 29))
        self.assertEquals(entry.valid_date, date(2013, 1, 10))

        JournalEntry.q.delete()

    def test_0020_get_current_semester(self):
        from pprint import pprint
        from pycroft.model.finance import Semester
        pprint(date.today())
        pprint(Semester.q.one().__dict__)
        try:
            get_current_semester()
        except NoResultFound:
            self.fail("No semester found")
        except MultipleResultsFound:
            self.fail("Multiple semesters found")

    def test_0030_simple_transaction(self):
        try:
            simple_transaction(
                u"transaction", self.asset_account, self.liability_account,
                9000, self.author
            )
        except Exception:
            self.fail()
        Transaction.q.delete()

    def test_0030_transferred_value(self):
        amount = 9000
        today = date.today()
        simple_transaction(
            u"transaction", self.asset_account, self.liability_account,
            amount, self.author, today - timedelta(1)
        )
        simple_transaction(
            u"transaction", self.asset_account, self.liability_account,
            amount, self.author, today
        )
        simple_transaction(
            u"transaction", self.asset_account, self.liability_account,
            amount, self.author, today + timedelta(1)
        )
        self.assertEqual(
            transferred_amount(
                self.asset_account, self.liability_account, today, today
            ),
            amount
        )
        self.assertEqual(
            transferred_amount(
                self.asset_account, self.liability_account, today, None
            ),
            2*amount
        )
        self.assertEqual(
            transferred_amount(
                self.asset_account, self.liability_account, None, today
            ),
            2*amount
        )
        self.assertEqual(
            transferred_amount(
                self.asset_account, self.liability_account, None, None
            ),
            3*amount
        )
        Transaction.q.delete()

    def test_0050_cleanup_non_sepa_description(self):
        non_sepa_description = u"1234-0 Dummy, User, with a- space at postition 28"
        self.assertEqual(cleanup_description(non_sepa_description), non_sepa_description)

    def test_0060_cleanup_sepa_description(self):
        clean_sepa_description = u"EREF+Long EREF 1234567890 with parasitic space SVWZ+A description with parasitic spaces at multiples of 28"
        sepa_description = u"EREF+Long EREF 1234567890 w ith parasitic space SVWZ+A description with par asitic spaces at multiples  of 28"
        self.assertEqual(cleanup_description(sepa_description), clean_sepa_description)
