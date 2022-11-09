# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import operator
import pkgutil
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from io import StringIO

import pytest
from factory import Iterator
from sqlalchemy.orm import Session

from pycroft import config, Config
from pycroft.helpers.date import last_day_of_month
from pycroft.helpers.interval import closedopen, openclosed, single
from pycroft.lib import finance
from pycroft.lib.finance import (
    cleanup_description,
    import_bank_account_activities_csv, simple_transaction,
    transferred_amount,
    is_ordered, estimate_balance,
    post_transactions_for_membership_fee, get_users_with_payment_in_default,
    end_payment_in_default_memberships,
    take_actions_for_payment_in_default_users)
from pycroft.model import session
from pycroft.model.finance import (
    BankAccountActivity,
    Transaction,
    Split,
    Account,
    MembershipFee,
    BankAccount,
)
from pycroft.model.user import Membership, User
from tests.factories import MembershipFactory, ConfigFactory
from tests.factories.address import AddressFactory
from tests.factories.finance import MembershipFeeFactory, TransactionFactory, \
    AccountFactory, BankAccountFactory, BankAccountActivityFactory
from tests.factories.user import UserFactory
from tests.legacy_base import FactoryDataTestBase


@pytest.mark.usefixtures("session")
class TestBankAccount:
    @pytest.fixture(scope="class")
    def bank_account(self, class_session) -> BankAccount:
        return BankAccountFactory.create(
            name="Hauptkonto",
            bank="Spaßkasse",
            account__name="Bankkonto 3120219540",
            account_number='3120219540',
        )

    @pytest.fixture(scope="class")
    def fee_account(self, class_session) -> Account:
        return AccountFactory.create(name="Membership Fees", type="REVENUE")

    @pytest.fixture(scope="class")
    def user(self, class_session):
        return UserFactory.create(name="Dummy User", account__name="Dummy User")

    @pytest.fixture(scope="class")
    def user_account(self, user):
        return user.account

    def test_import_bank_account_csv(self, bank_account):
        """
        This test should verify that the csv import works as expected.
        """
        data = pkgutil.get_data(__package__, "data_test_finance.csv")
        f = StringIO(data.decode("utf-8"))
        import_bank_account_activities_csv(f, Decimal("43.42"), date(2015, 1, 1))

        # test for correct dataimport
        activity = BankAccountActivity.q.filter_by(
            bank_account=bank_account,
            reference="0000-3, SCH, AAA, ZW41D/01 99 1, SS 13",
        ).first()
        assert activity.other_account_number == "12345678"
        assert activity.other_routing_number == "80040400"
        assert activity.other_name == "SCH, AAA"
        assert activity.amount == 9000.00
        assert activity.posted_on == date(2013, 1, 2)
        assert activity.valid_on == date(2013, 1, 2)

        # verify that the right year gets chosen for the transaction
        activity = BankAccountActivity.q.filter_by(
            bank_account=bank_account, reference="Pauschalen"
        ).first()
        assert activity.posted_on == date(2012, 12, 24)
        assert activity.valid_on == date(2012, 12, 24)

        # verify that a negative amount is imported correctly
        assert activity.amount == -6.00

        # verify that the correct transaction year gets chosen for a valuta date
        # which is in the next year
        activity = BankAccountActivity.q.filter_by(
            bank_account=bank_account, reference="BESTELLUNG SUPERMEGATOLLER SERVER"
        ).first()
        assert activity.posted_on == date(2013, 12, 29)
        assert activity.valid_on == date(2013, 1, 10)

    # TODO move && expand.
    #  this has nothing to do with a bank account.
    def test_simple_transaction(self, fee_account, user_account, processor):
        t = simple_transaction(
            "transaction", fee_account, user_account, Decimal(90), processor
        )
        assert t is not None

    def test_transferred_value(self, utcnow, fee_account, user_account, processor):
        author = processor
        amount = Decimal(90)
        today = utcnow.date()
        for valid_on in (today - timedelta(1), today, today + timedelta(1)):
            simple_transaction(
                description="transaction",
                debit_account=fee_account,
                credit_account=user_account,
                amount=amount,
                author=author,
                valid_on=valid_on,
            )

        assert transferred_amount(fee_account, user_account, single(today)) == amount
        assert (
            transferred_amount(fee_account, user_account, closedopen(today, None))
            == 2 * amount
        )
        assert (
            transferred_amount(fee_account, user_account, openclosed(None, today))
            == 2 * amount
        )
        assert transferred_amount(fee_account, user_account) == 3 * amount


# noinspection SpellCheckingInspection
@pytest.mark.parametrize(
    "description, clean_description",
    (
        ["1234-0 Dummy, User, with a- space at position 28"] * 2,
        (
            "EREF+Long EREF 1234567890 w ith a parasitic space "
            "SVWZ+A reference with paras itic spaces at multiples of  28",
            "EREF+Long EREF 1234567890 with a parasitic space "
            "SVWZ+A reference with parasitic spaces at multiples of 28",
        ),
    ),
)
def test_description_cleanup(description, clean_description):
    assert cleanup_description(description) == clean_description


class MembershipFeeTestCase(FactoryDataTestBase):
    def create_factories(self):
        ConfigFactory.create()

        self.processor = UserFactory.create()

        self.last_month_last = session.utcnow().replace(day=1) - timedelta(1)
        self.last_month_last_date = self.last_month_last.date()

        self.membership_fee_last = MembershipFeeFactory.create(
            begins_on=self.last_month_last_date.replace(day=1),
            ends_on=self.last_month_last_date
        )

        payment_deadline = timedelta(14)
        payment_deadline_final = timedelta(62)

        no_pid_action_date = session.utcnow() - payment_deadline + timedelta(1)
        pid_state_date = no_pid_action_date - timedelta(1)
        pid_no_end_membership_date = session.utcnow() - payment_deadline_final + timedelta(1)
        pid_end_membership_date = pid_no_end_membership_date - timedelta(1)

        self.membership_fee_no_pid_action = MembershipFeeFactory.create(
            begins_on=no_pid_action_date,
            ends_on=no_pid_action_date,
            booking_begin=timedelta(1),
            booking_end=timedelta(1),
        )

        self.membership_fee_pid_state = MembershipFeeFactory.create(
            begins_on=pid_state_date,
            ends_on=pid_state_date,
            booking_begin=timedelta(1),
            booking_end=timedelta(1),
        )

        self.membership_fee_no_end_membership = MembershipFeeFactory.create(
            begins_on=pid_no_end_membership_date,
            ends_on=pid_no_end_membership_date,
            booking_begin=timedelta(1),
            booking_end=timedelta(1),
        )

        self.membership_fee_pid_end_membership = MembershipFeeFactory.create(
            begins_on=pid_end_membership_date,
            ends_on=pid_end_membership_date,
            booking_begin=timedelta(1),
            booking_end=timedelta(1),
        )

    def create_user_from1y(self, **kwargs):
        reg_date = session.utcnow() - timedelta(weeks=52)

        return UserFactory(
            registered_at=reg_date,
            with_membership=True,
            membership__active_during=closedopen(reg_date, None),
            membership__group=config.member_group,
            **kwargs
        )

    def create_user_move_in_grace(self):
        reg_date = self.last_month_last.replace(day=self.membership_fee_last.booking_end.days) + timedelta(1)

        return UserFactory(
            registered_at=reg_date,
            with_membership=True,
            membership__active_during=closedopen(reg_date, None),
            membership__group=config.member_group
        )

    def create_user_move_in_no_grace(self):
        reg_date = self.last_month_last.replace(day=self.membership_fee_last.booking_end.days)

        return UserFactory(
            registered_at=reg_date,
            with_membership=True,
            membership__active_during=closedopen(reg_date, None),
            membership__group=config.member_group
        )

    def create_user_move_out_grace(self):
        reg_date = session.utcnow() - timedelta(weeks=52)

        membership_end_date = self.last_month_last.replace(day=self.membership_fee_last.booking_begin.days) - timedelta(1)

        return UserFactory(
            registered_at=reg_date,
            with_membership=True,
            membership__active_during=closedopen(reg_date, membership_end_date),
            membership__group=config.member_group,
            room_history_entries__active_during=closedopen(reg_date, membership_end_date),
        )

    def create_user_move_out_no_grace(self):
        reg_date = session.utcnow() - timedelta(weeks=52)
        membership_end_date = self.last_month_last.replace(day=self.membership_fee_last.booking_begin.days)

        return UserFactory(
            registered_at=reg_date,
            with_membership=True,
            membership__active_during=closedopen(reg_date, membership_end_date),
            membership__group=config.member_group,
            room_history_entries__active_during=closedopen(reg_date, membership_end_date),
        )

    def grace_check(self, user_grace, user_no_grace):
        assert user_grace.account.balance == 0.00, \
            "Initial user grace account balance not zero"
        assert user_no_grace.account.balance == 0.00, \
            "Initial user no grace account balance not zero"

        affected = post_transactions_for_membership_fee(self.membership_fee_last, self.processor)

        session.session.refresh(user_grace.account)
        session.session.refresh(user_no_grace.account)

        assert len(affected) == 1, "Wrong affected user count"

        assert user_grace.account.balance == 0.00, "User grace balance not zero"
        assert user_no_grace.account.balance == self.membership_fee_last.regular_fee, \
            "User no grace balance wrong"

    def test_basic_from1y(self):
        user1y = self.create_user_from1y()

        assert user1y.account.balance == 0.00, "Initial user account balance not zero"

        affected = post_transactions_for_membership_fee(self.membership_fee_last, self.processor)
        session.session.refresh(user1y.account)

        assert len(affected) == 1, "Wrong affected user count"
        assert user1y.account.balance == self.membership_fee_last.regular_fee, "User balance incorrect"

        transaction = Transaction.q.filter_by(valid_on=self.membership_fee_last.ends_on)\
            .filter(Transaction.description.contains(self.membership_fee_last.name)).first()

        assert transaction is not None, "Transaction not found"

        split_user = Split.q.filter_by(transaction=transaction, account=user1y.account,
                                       amount=self.membership_fee_last.regular_fee).first()

        assert split_user is not None, "User split not found"

        split_fee_account = Split.q.filter_by(transaction=transaction,
                                              account=user1y.room.building.fee_account,
                                              amount=-self.membership_fee_last.regular_fee).first()

        assert split_fee_account is not None, "Fee account split not found"

        affected = post_transactions_for_membership_fee(self.membership_fee_last, self.processor)

        session.session.refresh(user1y.account)

        assert len(affected) == 0, "Affected users not zero"

        assert user1y.account.balance == self.membership_fee_last.regular_fee, "User balance changed"

    def test_membership_begin_grace(self):
        user_grace = self.create_user_move_in_grace()
        user_no_grace = self.create_user_move_in_no_grace()

        self.grace_check(user_grace, user_no_grace)

    def test_membership_end_grace(self):
        user_grace = self.create_user_move_out_grace()
        user_no_grace = self.create_user_move_out_no_grace()

        self.grace_check(user_grace, user_no_grace)

    def test_fallback_fee_account(self):
        # No room at fee.ends_on -> room from fee.begins_on should be taken
        user_no_room = self.create_user_from1y(room=None,
                                               address=AddressFactory())

        transaction = Transaction.q.filter_by(valid_on=self.membership_fee_last.ends_on) \
            .filter(Transaction.description.contains(self.membership_fee_last.name)).first()

        assert transaction is None, "Transaction found, but should not exist yet."

        post_transactions_for_membership_fee(self.membership_fee_last, self.processor)
        session.session.refresh(user_no_room.account)

        assert user_no_room.account.balance == self.membership_fee_last.regular_fee, "User balance incorrect"

        transaction = Transaction.q.filter_by(valid_on=self.membership_fee_last.ends_on) \
            .filter(Transaction.description.contains(self.membership_fee_last.name)).first()

        assert transaction is not None, "Transaction not found"

        split_fee_account = Split.q.filter_by(transaction=transaction,
                                              account=config.membership_fee_account,
                                              amount=-self.membership_fee_last.regular_fee).first()

        assert split_fee_account is not None, "Fee account split not found"

    def handle_payment_in_default_users(self):
        end_payment_in_default_memberships(self.processor)
        users_pid_membership, users_membership_terminated = get_users_with_payment_in_default(
            self.session
        )
        take_actions_for_payment_in_default_users(users_pid_membership,
                                                  users_membership_terminated, self.processor)

        return users_pid_membership, users_membership_terminated

    def test_payment_in_default_actions(self):
        user = self.create_user_from1y()

        assert user.account.balance == 0.00, "Initial user account balance not zero"
        assert user.account.in_default_days == 0
        assert user.has_property("member"), "User is not a member"

        # Test fee with no action
        post_transactions_for_membership_fee(self.membership_fee_no_pid_action, self.processor)
        session.session.refresh(user.account)

        assert user.account.balance == self.membership_fee_no_pid_action.regular_fee, "User balance incorrect"

        users_pid_membership, users_membership_terminated = self.handle_payment_in_default_users()

        assert user.has_property("member"), "User is not a member"
        assert not user.has_property("payment_in_default"), "User has payment_in_default property"


        # Test fee with payment_in_default group action (minimum)
        post_transactions_for_membership_fee(self.membership_fee_pid_state, self.processor)
        session.session.refresh(user.account)

        assert self.membership_fee_no_pid_action.regular_fee + self.membership_fee_pid_state.regular_fee \
            == user.account.balance, \
            "User balance incorrect"

        users_pid_membership, users_membership_terminated = self.handle_payment_in_default_users()

        self.session.refresh(user)
        assert user.has_property("member"), "User is not a member"
        assert user.has_property("payment_in_default"), "User has no payment_in_default property"

        # Test fee with payment_in_default group action (maximum)
        post_transactions_for_membership_fee(self.membership_fee_no_end_membership, self.processor)
        session.session.refresh(user.account)

        assert self.membership_fee_no_pid_action.regular_fee \
               + self.membership_fee_pid_state.regular_fee \
               + self.membership_fee_no_end_membership.regular_fee \
               == user.account.balance, \
               "User balance incorrect"

        users_pid_membership, users_membership_terminated = self.handle_payment_in_default_users()

        self.session.refresh(user)
        assert user.has_property("member"), "User is not a member"
        assert user.has_property("payment_in_default"), "User has no payment_in_default property"

        # Test fee with terminating membership
        post_transactions_for_membership_fee(self.membership_fee_pid_end_membership, self.processor)
        session.session.refresh(user.account)

        assert self.membership_fee_no_pid_action.regular_fee \
               + self.membership_fee_pid_state.regular_fee \
               + self.membership_fee_no_end_membership.regular_fee \
               + self.membership_fee_pid_end_membership.regular_fee \
               == user.account.balance, \
               "User balance incorrect"

        users_pid_membership, users_membership_terminated = self.handle_payment_in_default_users()

        self.session.refresh(user)
        assert not user.has_property("member"), "User is a member"
        assert user.has_property("payment_in_default"), "User has no payment_in_default property"

    def test_payment_in_default_recover(self):
        user = self.create_user_from1y()

        assert user.account.balance == 0.00, "Initial user account balance not zero"
        assert user.account.in_default_days == 0
        assert user.has_property("member"), "User is not a member"

        # Test fee with payment_in_default group action
        post_transactions_for_membership_fee(self.membership_fee_pid_state, self.processor)
        session.session.refresh(user.account)

        assert user.account.balance == self.membership_fee_pid_state.regular_fee, "User balance incorrect"

        self.handle_payment_in_default_users()

        self.session.refresh(user)
        assert user.has_property("member"), "User is not a member"
        assert user.has_property("payment_in_default"), "User has no payment_in_default property"

        # this transaction…
        simple_transaction(description="deposit",
                           debit_account=user.account,
                           credit_account=AccountFactory(),
                           amount=self.membership_fee_pid_state.regular_fee,
                           author=self.processor)
        # …should unblock the user now
        self.handle_payment_in_default_users()

        self.session.refresh(user)
        assert user.has_property("member"), "User is not a member"
        assert not user.has_property("payment_in_default"), "User has payment_in_default property"


class TestIsOrdered:
    def test_ordered(self):
        assert is_ordered((1, 2, 3))

    def test_not_ordered(self):
        assert not is_ordered((1, 3, 2))

    def test_custom_operator(self):
        assert is_ordered((3, 2, 1), relation=operator.gt)

class TestSplitTypes:
    @pytest.fixture
    def a_user(self) -> Account:
        return Account(name="user_account", type="USER_ASSET")

    @pytest.fixture
    def a_bank(self) -> Account:
        return Account(name="bank", type="BANK_ASSET")

    @pytest.fixture
    def a_liability(self) -> Account:
        return Account(name="liabilities", type="LIABILITY")

    @pytest.fixture
    def a_fees(self) -> Account:
        return Account(name="fees", type="REVENUE")

    @pytest.fixture
    def t(self) -> Transaction:
        """An empty transaction"""
        return TransactionFactory.build(splits=[])

    def test_empty_transaction(self, t):
        assert finance.get_transaction_type(t) is None

    def test_simple_transaction(self, t, a_user, a_fees):
        t.splits = [Split(amount=300, account=a_user), Split(amount=-300, account=a_fees)]
        assert finance.get_transaction_type(t) == ("USER_ASSET", "REVENUE")

    def test_simple_transaction_flipped(self, t, a_user, a_fees):
        t.splits = [Split(amount=-300, account=a_user), Split(amount=300, account=a_fees)]
        assert finance.get_transaction_type(t) == ("REVENUE", "USER_ASSET")

    def test_complex_transaction(self, t, a_user, a_fees):
        t.splits = [
            Split(amount=-300, account=a_user),
            Split(amount=-100, account=a_user),
            Split(amount=150, account=a_fees),
            Split(amount=350, account=a_fees),
        ]
        assert finance.get_transaction_type(t) == ("REVENUE", "USER_ASSET")

    def test_heterogeneous_transaction(self, t, a_user, a_fees, a_liability):
        t.splits = [
            Split(amount=300, account=a_user),
            Split(amount=-100, account=a_fees),
            Split(amount=-200, account=a_liability),
        ]
        assert finance.get_transaction_type(t) is None


@pytest.fixture(scope="module")
def config(module_session: Session):
    return ConfigFactory.create()


@pytest.mark.usefixtures("session")
class TestBalanceEstimation:
    @pytest.fixture(scope="class", autouse=True)
    def user(self, class_session: Session, config: Config) -> User:
        return UserFactory.create()

    @pytest.fixture(scope="class", autouse=True)
    def user_membership(
        self, user: User, class_session: Session, utcnow, config: Config
    ) -> Membership:
        return MembershipFactory.create(
            active_during=closedopen(utcnow - timedelta(weeks=52), None),
            user=user,
            group=config.member_group
        )

    @pytest.fixture(scope="class", autouse=True)
    def membership_fee_current(self, class_session: Session) -> MembershipFee:
        return MembershipFeeFactory.create()

    @pytest.fixture(scope="class", autouse=True)
    def membership_fee_last(self, class_session: Session, utcnow):
        last_month_last = utcnow.date().replace(day=1) - timedelta(1)
        return MembershipFeeFactory.create(
            begins_on=last_month_last.replace(day=1),
            ends_on=last_month_last,
        )

    @pytest.fixture
    def transaction_current(self, session, membership_fee_current, user):
        t = TransactionFactory.create(
            valid_on=membership_fee_current.ends_on,
            splits__account=Iterator([user.account, AccountFactory.create()]),
        )
        session.flush()
        return t

    @pytest.fixture
    def transaction_last(self, session, membership_fee_last, user):
        # Membership fee booking for last month
        t = TransactionFactory.create(
            valid_on=membership_fee_last.ends_on,
            splits__account=Iterator([user.account, AccountFactory.create()]),
        )
        session.flush()
        return t

    @pytest.fixture
    def check_current_and_next_month(
        self,
        utcnow,
        session: Session,
        user: User,
        membership_fee_current: MembershipFee,
    ):
        def _check_current_and_next_month(base: Decimal):
            session.refresh(user)
            # `estimate_balance` needs an up-to-date `account.balance`, which relies on the
            # account's `splits`
            session.refresh(user.account)

            # End in grace-period in current month
            in_grace_current_month = utcnow.date().replace(
                day=membership_fee_current.booking_begin.days - 1
            )
            assert base == estimate_balance(session, user, in_grace_current_month)

            # End after grace-period in current month
            after_grace_current_month = membership_fee_current.ends_on
            assert base - Decimal(5) == estimate_balance(
                session, user, after_grace_current_month
            )

            # End in the middle of next month
            middle_next_month = utcnow.date().replace(day=14) + timedelta(weeks=4)
            assert base - Decimal(10) == estimate_balance(
                session, user, middle_next_month
            )

            # End in grace-period of next month
            in_grace_next_month = middle_next_month.replace(
                day=membership_fee_current.booking_begin.days - 1
            )
            assert base - Decimal(5) == estimate_balance(
                session, user, in_grace_next_month
            )

        return _check_current_and_next_month

    @pytest.mark.meta
    def test_user_is_member(self, user: User):
        assert user.has_property("member")

    def test_last_booked__current_not_booked(
        self, transaction_last, check_current_and_next_month
    ):
        check_current_and_next_month(Decimal(-5))

    def test_last_booked__current_booked(
        self,
        transaction_last,
        transaction_current,
        check_current_and_next_month,
    ):
        check_current_and_next_month(Decimal(-5))

    def test_last_not_booked__current_not_booked(self, check_current_and_next_month):
        check_current_and_next_month(Decimal(-5))

    def test_last_not_due__current_not_booked(
        self, user_membership, membership_fee_current, check_current_and_next_month
    ):
        user_membership.active_during = closedopen(
            membership_fee_current.begins_on, None
        )
        check_current_and_next_month(Decimal(0))

    def test_free_membership(
        self,
        session,
        utcnow,
        user,
        user_membership,
        membership_fee_current,
    ):
        new_start = utcnow.replace(day=membership_fee_current.booking_end.days + 1)
        user_membership.active_during = closedopen(new_start, None)
        end_date = last_day_of_month(utcnow.date())
        assert estimate_balance(session, user, end_date) == Decimal(0)


class TestMatching:
    # noinspection SpellCheckingInspection
    @pytest.mark.parametrize('reference, expected', [
        ("11111-36, Hans Wurst, HSS46/A 01 B", "pyc-11111"),
        ("11111-36, JustOneName, /My fancy room", "pyc-11111"),
        ("12345-65465, Hans Wurst, HSS46/A 01 B", None),  # checksum too long
        ("12345-65, Hans Wurst, HSS46/A 01 B", None),  # bad checksum
        ("12345-20, Hans Wurst, HSS46/A 01 B", "pyc-12345"),
        ("1, Hans Wurst, HSS46/A 01 B", None),
        ("n1colas, Nicolas Bourbaki, HSS48 76-3", None),
        ("n1cOLAS, Nicolas Bourbaki, HSS48 76-3", None),
        ("  admin,Ich Bin Hier der Admin , ficticous location , garbage", None),
        ("FOO, FOO BAR, HSS46 16-11", None),
    ])
    def test_matching(self, reference, expected):
        result = finance.match_reference(reference, lambda uid: f"pyc-{uid}")
        assert result == expected


class TestLastImportedAt:
    def test_last_imported_at(self, session: Session):
        BankAccountActivityFactory.create(
            reference="Test transaction",
            imported_at=datetime(2020, 1, 1),
        )
        session.flush()
        assert finance.get_last_import_date(session) == datetime(
            2020, 1, 1, tzinfo=timezone.utc
        )
