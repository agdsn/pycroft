from pycroft.lib.finance import match_activities
from pycroft.model.finance import AccountPattern
from tests import FactoryDataTestBase
from tests.factories import AccountFactory
from tests.factories.finance import BankAccountFactory, BankAccountActivityFactory


class TestTeamActivityMatching(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.team_account = AccountFactory.create(type='ASSET', name='Team Network')
        self.team_account.patterns = [AccountPattern(pattern=r"2[0-9]{3}-N\d\d")]
        self.bank_account = BankAccountFactory.create()
        self.activity, *rest = [
            BankAccountActivityFactory.create(bank_account=self.bank_account,
                                              reference=reference)
            for reference in [
                'Erstattung 2020-N15 (Pizza)',
                'Erstattung 2020-NN',
                'Other reference, which should not match our regex',
            ]
        ]

    def test_team_matching(self):
        assert match_activities() == ({}, {self.activity: self.team_account})
