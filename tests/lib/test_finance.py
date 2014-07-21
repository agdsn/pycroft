# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import date, timedelta

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from pycroft.lib.finance import (
    import_journal_csv, get_current_semester, simple_transaction,
    transferred_amount, cleanup_description, MatchUser, match_entry, 
    compute_matches_by_uid_in_words, compute_matches_by_user_names_in_words,
    combine_matches, tokenize, remove_keywords)
from pycroft.model.finance import (
    FinanceAccount, Journal, JournalEntry,
    Transaction)
from pycroft.model.user import User
from tests import FixtureDataTestBase
from tests.lib.fixtures.finance_fixtures import (
    FinanceAccountData, JournalData, JournalEntryData, SemesterData, UserData)


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
        non_sepa_description = u"1234-0 Dummy, User, with " \
                               u"a- space at postition 28"
        self.assertEqual(cleanup_description(non_sepa_description), non_sepa_description)

    def test_0060_cleanup_sepa_description(self):
        clean_sepa_description = u"EREF+Long EREF 1234567890 with a parasitic " \
                                 u"space SVWZ+A description with parasitic " \
                                 u"spaces at multiples of 28"
        sepa_description = u"EREF+Long EREF 1234567890 w ith a parasitic space " \
                           u"SVWZ+A description with par asitic spaces at " \
                           u"multiples  of 28"
        self.assertEqual(cleanup_description(sepa_description), clean_sepa_description)


class Test_020_Matching(FixtureDataTestBase):
    datasets = [ JournalEntryData ]
    
    def setUp(self):
        super(Test_020_Matching, self).setUp()
        self.user1 = MatchUser(1234, (u"max", u"mustermann"))
        self.user2 = MatchUser(1431, (u"max", u"musterfrau"))
        #make dict of self.users
        self.users = {user.user_id: user for user in (self.user1, self.user2)} 
        #pull journal and journalentry from finance_fixture
        self.entry = JournalEntry.q.filter_by(
            id = JournalEntryData.entry01.id
        ).one()
        
    def test_0100_match_entry(self):
        res = match_entry(self.entry, self.users)
        self.assertEqual(self.user1, res[0][1])
        #self.assertEqual(self.user2, res[1][1])

    def test_0200_combine_matches(self):
        #tuple[list[(float, MatchUser)]] user_matches+
        match1 = [(0.32, self.user1)]
        match2 = [(1.0, self.user1)]
        match3 = [(0.52, self.user2)]
        self.assertEqual([(1.0, self.user1),(0.52, self.user2)], 
                combine_matches(match1,match2,match3))

    def test_0300_compute_matches_by_type1_uid_in_words(self):
        words = [u'1234-0']
        res = compute_matches_by_uid_in_words(words, self.users)
        self.assertEqual(res, [(1.0, self.user1)])

    def test_0300_compute_matches_by_type2_uid_in_words(self):
        words = [u'1234-82']
        res = compute_matches_by_uid_in_words(words, self.users)
        self.assertEqual(res, [(1.0, self.user1)])

    def test_0400_compute_matches_by_user_names_in_words(self):
        # 
        words = [u'123-6', u'max', u'mustermann']
        res = compute_matches_by_user_names_in_words(words, self.users) 
        print res
        self.assertEqual(self.user1, res[0][1])
        #self.assertEqual(self.user2, res[1][1])
        
    def test_0501_tokenize_spaces(self):
        testString = u'Trenne Namen'
        expString = (u'trenne', u'namen')
        self.assertEqual(expString, tokenize(testString))

    def test_0502_tokenize_case_sensitive(self):
        testString = u'TrenneNamen'
        expString = (u'trenne', u'namen')
        self.assertEqual(expString, tokenize(testString))

    def test_0503_tokenize_dash(self):
        testString = u'Trenne-Namen'
        expString = (u'trenne', u'namen')
        self.assertEqual(expString, tokenize(testString))
    def test_0504_tokenize_uid(self):
        testString = u'11234-21 mehr-namen'
        expString = (u'11234-21', u'mehr', u'namen')
        self.assertEqual(expString, tokenize(testString))
    def test_0505_tokenize_number_inside_word(self):
        testString = u'Trenne4Namen'
        expString = (u'trenne4', u'namen')
        self.assertEqual(expString, tokenize(testString))

    def test_0601_remove_keywords_agdsn(self):
        testString = u'AGDSN Trenne Namen'
        expString = u'  Trenne Namen'
        self.assertEqual(expString, remove_keywords(testString))
    def test_0602_remove_keywords_zw(self):
        testString = u'ZW41a Trenne Namen'
        expString = u'  Trenne Namen'
        self.assertEqual(expString, remove_keywords(testString))

