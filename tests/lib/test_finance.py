from tests import OldPythonTestCase

__author__ = 'felix_kluge'

from pycroft.lib.finance import create_semester, import_csv
from pycroft.lib.config import get, config
from pycroft.model.finance import FinanceAccount, Journal, JournalEntry
from pycroft.model import session
from datetime import date, datetime


class Test_010_Semester(OldPythonTestCase):

    def test_0010_create_semester_accounts(self):
        """
        This test should verify that all semester-related finance-accounts have
        been created.
        """
        new_semester = create_semester("NewSemesterName",
                                       2500, 1500, 450, 150,
                                       date(2013, 9, 1),
                                       date(2013, 10, 1),
                                       date(2014, 4, 1),
                                       date(2014, 5, 1),)
        config._configpath = "../tests/example/test_config.json"
        for account in config["finance"]["semester_accounts"]:
            new_created_account = FinanceAccount.q.filter(
                FinanceAccount.semester == new_semester,
                FinanceAccount.tag == account["tag"]).first()
            self.assertEqual(new_created_account.name, account["name"])
            self.assertEqual(new_created_account.type, account["type"])
        session.session.commit()



class Test_020_Journal(OldPythonTestCase):

    def test_0010_create_sepa_journal(self):
        """
        A Journal with an iban is created.
        """
        new_journal = Journal(account=u"SEPA-Konto",
                          bank=u"TolleBank",
                          hbci_url=u"testurl",
                          last_update=datetime.now(),
                          account_number=u"DE32444433332222111100",
                          bank_identification_code=u"000000")
        session.session.add(new_journal)
        session.session.commit()


    def test_0010_import_journal_csv(self):
        """
        This test should verify that the csv import works as expected.
        """
        journal = Journal(account=u"Konto bei der Sparkasse",
                          bank=u"Sparkasse Dresden",
                          hbci_url=u"testurl",
                          last_update=datetime.now(),
                          account_number=u"2312443512",
                          bank_identification_code=u"000000")
        session.session.add(journal)
        journal_sepa = Journal(account=u"SEPA-Konto bei der Sparkasse",
                          bank=u"Sparkasse Dresden",
                          hbci_url=u"testurl",
                          last_update=datetime.now(),
                          account_number=u"DE32444433332222111100",
                          bank_identification_code=u"000000")
        session.session.add(journal_sepa)
        import_csv("example/example.csv", datetime(2013, 1, 5, 0, 0, 0))
        session.session.commit()

        # test for correct dataimport
        entry = JournalEntry.q.filter(
            JournalEntry.journal == journal,
            JournalEntry.original_description == "0000-3, SCH, AAA, ZW41D/01 99 1, SS 13").first()
        self.assertEquals(entry.other_account, "12345678")
        self.assertEquals(entry.other_bank, "80040400")
        self.assertEquals(entry.other_person, "SCH, AAA")
        self.assertEquals(entry.amount, 9000)
        self.assertEquals(entry.transaction_date, date(2013, 1, 2))
        self.assertEquals(entry.valid_date, date(2013, 1, 2))

        # verify that the right year gets chosen for the transaction
        entry = JournalEntry.q.filter(
            JournalEntry.journal == journal,
            JournalEntry.original_description == "Pauschalen").first()
        self.assertEquals(entry.transaction_date, date(2012, 12, 24))
        self.assertEquals(entry.valid_date, date(2012, 12, 24))

        # verify that a negative amount is imported correctly
        self.assertEquals(entry.amount, -6.00)

        # verify that the correct transaction year gets chosen for a valuta date
        # which is in the next year
        entry = JournalEntry.q.filter(
            JournalEntry.journal == journal,
            JournalEntry.original_description == "BESTELLUNG SUPERMEGATOLLER SERVER").first()
        self.assertEquals(entry.transaction_date, date(2012, 12, 29))
        self.assertEquals(entry.valid_date, date(2013, 1, 10))