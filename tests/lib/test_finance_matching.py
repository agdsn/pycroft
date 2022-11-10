import pytest
from sqlalchemy.orm import Session

from pycroft.lib.finance import match_activities
from pycroft.model.finance import AccountPattern, Account, BankAccountActivity
from tests.factories import AccountFactory
from tests.factories.finance import BankAccountFactory, BankAccountActivityFactory


@pytest.fixture(scope="module")
def team_account(module_session: Session) -> Account:
    team_account = AccountFactory.create(type="ASSET", name="Team Network")
    team_account.patterns = [AccountPattern(pattern=r"2[0-9]{3}-N\d\d")]
    return team_account


@pytest.fixture(scope="module")
def activity(module_session: Session) -> BankAccountActivity:
    bank_account = BankAccountFactory.create()
    activity, *rest = (
        BankAccountActivityFactory.create(
            bank_account=bank_account, reference=reference
        )
        for reference in [
            "Erstattung 2020-N15 (Pizza)",  # this activity should match
            "Erstattung 2020-NN",
            "Other reference, which should not match our regex",
        ]
    )
    return activity


def test_team_matching(activity, team_account):
    assert match_activities() == ({}, {activity: team_account})
