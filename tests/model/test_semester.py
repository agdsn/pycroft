# -*- coding: utf-8 -*-
__author__ = 'Florian Österreich'

from tests import OldPythonTestCase
from pycroft.lib import finance as financeHelper
from pycroft import model
from pycroft.model import session
from datetime import datetime

class Test_010_Create_Semester(OldPythonTestCase):

    @classmethod
    def setUpClass(cls):
        session.reinit_session("sqlite://")
        model.drop_db_model()
        model.create_db_model()

    def tearDown(self):
        session.session.remove()

    def test_010_new_semester(self):
        new_semester = financeHelper.semester_create("Testsemester", "2500", "1500", datetime.now(), datetime.now())
        self.assertIsNotNone(new_semester.registration_fee_account)
        self.assertEqual(new_semester.registration_fee_account.name,u"Anmeldegebühr Testsemester")
        self.assertEqual(new_semester.registration_fee_account.type,"EXPENSE")
        self.assertIsNotNone(new_semester.semester_fee_account)
        self.assertEqual(new_semester.semester_fee_account.name,u"Semestergebühr Testsemester")
        self.assertEqual(new_semester.semester_fee_account.type,"EXPENSE")
        self.assertEqual(new_semester.registration_fee,2500)
        self.assertEqual(new_semester.semester_fee,1500)