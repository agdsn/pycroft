from tests import OldPythonTestCase

__author__ = 'felix_kluge'

from pycroft.lib.finance import create_semester
from pycroft.lib.config import get,config
from pycroft.model.finance import FinanceAccount
from sqlalchemy.orm import backref
from pycroft.model import session
import time
from datetime import date


class Test_010_Semester(OldPythonTestCase):

    def test_0010_create_semester_accounts(self):
        """
        This test should verify that all semester-related finance-accounts have
        been created.
        """
        new_semester = create_semester("NewSemesterName", 2500, 1500, date(2013, 9, 1), date(2014, 2, 1))
        config._configpath = "../tests/example/test_config.json"
        for account in config["finance"]["semester_accounts"]:
            for new_account in new_semester.accounts:
                if(new_account.tag == account["tag"]):
                    new_account_equivalent = new_account
            compare_account = FinanceAccount(type=account["type"],name=account["name"],semester=new_semester,tag=account["tag"])
            self.assertEqual(new_account_equivalent.name, compare_account.name)
            self.assertEqual(new_account_equivalent.type, compare_account.type)