# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from tests import OldPythonTestCase, FixtureDataTestBase
from tests.lib.fixtures.finance_fixtures import JournalData

__author__ = 'felix_kluge'

from pycroft.lib.finance import create_semester, import_journal_csv
from pycroft.model.finance import FinanceAccount, Journal, JournalEntry, \
    Semester
from pycroft.model import session
from datetime import date, datetime


class Test_010_Semester(OldPythonTestCase):

    def test_0010_create_semester(self):
        """
        This test should verify that all semester-related finance-accounts have
        been created.
        """
        new_semester = create_semester("NewSemesterName",
                                       2500, 1500, 450, 250,
                                       date(2013, 9, 1),
                                       date(2013, 10, 1),
                                       date(2014, 4, 1),
                                       date(2014, 5, 1),)
        queried_semester = Semester.q.filter(
            Semester.name == "NewSemesterName"
        ).one()
        self.assertEqual(new_semester, queried_semester)
        session.session.commit()


class Test_020_Journal(FixtureDataTestBase):

    datasets = [JournalData]

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
