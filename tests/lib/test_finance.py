from tests import OldPythonTestCase

__author__ = 'felix_kluge'

from pycroft.lib.finance import create_semester, import_csv
from pycroft.lib.config import get, config
from pycroft.model.finance import FinanceAccount, Journal, JournalEntry
from sqlalchemy.orm import backref
from pycroft.model import session
import time
from datetime import date, datetime


class Test_010_Semester(OldPythonTestCase):

    def test_0010_create_semester_accounts(self):
        """
        This test should verify that all semester-related finance-accounts have
        been created.
        """
        new_semester = create_semester("NewSemesterName",
                                       2500, 1500,
                                       date(2013, 9, 1),
                                       date(2014, 2, 1))
        config._configpath = "../tests/example/test_config.json"
        for account in config["finance"]["semester_accounts"]:
            new_created_account = FinanceAccount.q.filter(
                FinanceAccount.semester == new_semester,
                FinanceAccount.tag == account["tag"]).first()
            self.assertEqual(new_created_account.name, account["name"])
            self.assertEqual(new_created_account.type, account["type"])
        session.session.commit()