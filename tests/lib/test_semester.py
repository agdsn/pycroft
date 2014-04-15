# -*- coding: utf-8 -*-
__author__ = 'Florian Österreich'

from tests import OldPythonTestCase
from pycroft.lib.finance import create_semester
from pycroft import model
from pycroft.model import session
from datetime import date, timedelta

class Test_010_Create_Semester(OldPythonTestCase):

    @classmethod
    def setUpClass(cls):
        session.reinit_session("sqlite://")
        model.drop_db_model()
        model.create_db_model()

    def tearDown(self):
        session.session.remove()

    def test_010_new_semester(self):
        today = date.today()
        new_semester = create_semester(
            "Testsemester", "2500", "1500", "450", "150",
            today - timedelta(1), today,
            today + timedelta(1), today + timedelta(2))
        self.assertEqual(new_semester.registration_fee, 2500)
        self.assertEqual(new_semester.regular_membership_fee, 1500)
        self.assertEqual(new_semester.reduced_membership_fee, 450)
        self.assertEqual(new_semester.overdue_fine, 150)
        self.assertEqual(
            new_semester.premature_begin_date, today - timedelta(1))
        self.assertEqual(new_semester.begin_date, today)
        self.assertEqual(new_semester.end_date, today + timedelta(1))
        self.assertEqual(new_semester.belated_end_date, today + timedelta(2))