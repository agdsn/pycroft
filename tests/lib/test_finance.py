# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import operator
import pkgutil
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import MagicMock

import pytest
from factory import Iterator
from sqlalchemy.orm.exc import NoResultFound

from pycroft import config
from pycroft.helpers.date import last_day_of_month
from pycroft.helpers.interval import closedopen, openclosed, single, closed
from pycroft.lib import finance
from pycroft.lib.finance import (
    cleanup_description,
    import_bank_account_activities_csv, simple_transaction,
    transferred_amount,
    is_ordered, get_last_applied_membership_fee, estimate_balance,
    post_transactions_for_membership_fee, get_users_with_payment_in_default,
    end_payment_in_default_memberships,
    take_actions_for_payment_in_default_users)
from pycroft.model import session
from pycroft.model.finance import BankAccountActivity, Transaction, Split
from pycroft.model.user import User
from tests import FactoryDataTestBase
from tests.factories import MembershipFactory, ConfigFactory, BuildingFactory
from tests.factories.address import AddressFactory
from tests.factories.finance import MembershipFeeFactory, TransactionFactory, \
    AccountFactory, BankAccountFactory
from tests.factories.user import UserFactory, UserWithMembershipFactory


class Test_010_BankAccount(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.bank_account = BankAccountFactory.create(
            name="Hauptkonto",
            bank="Spaßkasse",
            account__name="Bankkonto 3120219540",
            account_number='3120219540',
        )
        self.fee_account = AccountFactory.create(name="Membership Fees", type='REVENUE')
        self.user = UserFactory.create(name="Dummy User", account__name="Dummy User")
        self.author = UserFactory.create()

    @property
    def user_account(self):
        return self.user.account

    def test_0010_import_bank_account_csv(self):
        """
        This test should verify that the csv import works as expected.
        """
        data = pkgutil.get_data(__package__, "data_test_finance.csv")
        f = StringIO(data.decode('utf-8'))

        import_bank_account_activities_csv(f, Decimal('43.42'),
                                           date(2015, 1, 1))

        # test for correct dataimport
        activity = BankAccountActivity.q.filter_by(
            bank_account=self.bank_account,
            reference="0000-3, SCH, AAA, ZW41D/01 99 1, SS 13"
        ).first()
        assert activity.other_account_number == "12345678"
        assert activity.other_routing_number == "80040400"
        assert activity.other_name == "SCH, AAA"
        assert activity.amount == 9000.00
        assert activity.posted_on == date(2013, 1, 2)
        assert activity.valid_on == date(2013, 1, 2)

        # verify that the right year gets chosen for the transaction
        activity = BankAccountActivity.q.filter_by(
            bank_account=self.bank_account,
            reference="Pauschalen"
        ).first()
        assert activity.posted_on == date(2012, 12, 24)
        assert activity.valid_on == date(2012, 12, 24)

        # verify that a negative amount is imported correctly
        assert activity.amount == -6.00

        # verify that the correct transaction year gets chosen for a valuta date
        # which is in the next year
        activity = BankAccountActivity.q.filter_by(
            bank_account=self.bank_account,
            reference="BESTELLUNG SUPERMEGATOLLER SERVER"
        ).first()
        assert activity.posted_on == date(2013, 12, 29)
        assert activity.valid_on == date(2013, 1, 10)

        BankAccountActivity.q.delete()
        session.session.commit()

    def test_0020_get_last_applied_membership_fee(self):
        try:
            get_last_applied_membership_fee()
        except NoResultFound:
            self.fail("No fee found")

    def test_0030_simple_transaction(self):
        try:
            simple_transaction(
                "transaction", self.fee_account, self.user_account,
                Decimal(90), self.author
            )
        except Exception:
            self.fail()
        Transaction.q.delete()
        session.session.commit()

    def test_0030_transferred_value(self):
        amount = Decimal(90)
        today = session.utcnow().date()
        simple_transaction(
            "transaction", self.fee_account, self.user_account,
            amount, self.author, today - timedelta(1)
        )
        simple_transaction(
            "transaction", self.fee_account, self.user_account,
            amount, self.author, today
        )
        simple_transaction(
            "transaction", self.fee_account, self.user_account,
            amount, self.author, today + timedelta(1)
        )
        assert (
            transferred_amount(
                self.fee_account, self.user_account, single(today)
            )
            == amount
        )
        assert (
            transferred_amount(
                self.fee_account, self.user_account, closedopen(today, None)
            )
            == 2 * amount
        )
        assert (
            transferred_amount(
                self.fee_account, self.user_account, openclosed(None, today)
            )
            == 2 * amount
        )
        assert (
            transferred_amount(
                self.fee_account, self.user_account
            )
            == 3 * amount
        )
        Transaction.q.delete()
        session.session.commit()

    def test_0050_cleanup_non_sepa_description(self):
        non_sepa_description = "1234-0 Dummy, User, with " \
                               "a- space at postition 28"
        assert cleanup_description(non_sepa_description) == non_sepa_description

    def test_0060_cleanup_sepa_description(self):
        clean_sepa_description = "EREF+Long EREF 1234567890 with a parasitic " \
                                 "space SVWZ+A reference with parasitic " \
                                 "spaces at multiples of 28"
        sepa_description = "EREF+Long EREF 1234567890 w ith a parasitic space " \
                           "SVWZ+A reference with paras itic spaces at " \
                           "multiples of  28"
        assert cleanup_description(sepa_description) == clean_sepa_description


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

        return UserWithMembershipFactory(
            registered_at=reg_date,
            membership__active_during=closedopen(reg_date, None),
            membership__group=config.member_group,
            **kwargs
        )

    def create_user_move_in_grace(self):
        reg_date = self.last_month_last.replace(day=self.membership_fee_last.booking_end.days) + timedelta(1)

        return UserWithMembershipFactory(
            registered_at=reg_date,
            membership__active_during=closedopen(reg_date, None),
            membership__group=config.member_group
        )

    def create_user_move_in_no_grace(self):
        reg_date = self.last_month_last.replace(day=self.membership_fee_last.booking_end.days)

        return UserWithMembershipFactory(
            registered_at=reg_date,
            membership__active_during=closedopen(reg_date, None),
            membership__group=config.member_group
        )

    def create_user_move_out_grace(self):
        reg_date = session.utcnow() - timedelta(weeks=52)

        membership_end_date = self.last_month_last.replace(day=self.membership_fee_last.booking_begin.days) - timedelta(1)

        return UserWithMembershipFactory(
            registered_at=reg_date,
            membership__active_during=closedopen(reg_date, membership_end_date),
            membership__group=config.member_group,
            room_history_entries__active_during=closedopen(reg_date, membership_end_date),
        )

    def create_user_move_out_no_grace(self):
        reg_date = session.utcnow() - timedelta(weeks=52)
        membership_end_date = self.last_month_last.replace(day=self.membership_fee_last.booking_begin.days)

        return UserWithMembershipFactory(
            registered_at=reg_date,
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
        users_pid_membership, users_membership_terminated = get_users_with_payment_in_default()
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


class BalanceEstimationTestCase(FactoryDataTestBase):
    def create_factories(self):
        ConfigFactory.create()

        self.user = UserFactory.create()

        self.user_membership = MembershipFactory.create(
            active_during=closedopen(session.utcnow() - timedelta(weeks=52), None),
            user=self.user,
            group=config.member_group
        )

        last_month_last = session.utcnow().date().replace(day=1) - timedelta(1)

        self.membership_fee_current = MembershipFeeFactory.create()
        self.membership_fee_last = MembershipFeeFactory.create(
            begins_on=last_month_last.replace(day=1),
            ends_on=last_month_last
        )

    def create_transaction_current(self):
        # Membership fee booking for current month
        TransactionFactory.create(
            valid_on=self.membership_fee_current.ends_on,
            splits__account=Iterator(
                [self.user.account, AccountFactory.create()])
        )

    def create_transaction_last(self):
        # Membership fee booking for last month
        TransactionFactory.create(
            valid_on=self.membership_fee_last.ends_on,
            splits__account=Iterator(
                [self.user.account, AccountFactory.create()])
        )

    def check_current_and_next_month(self, base):
        # End in grace-period in current month
        end_date = session.utcnow().date().replace(day=self.membership_fee_current.booking_begin.days - 1)
        assert base == estimate_balance(self.user, end_date)

        # End after grace-period in current month
        end_date = self.membership_fee_current.ends_on
        assert base - 5.00 == estimate_balance(self.user, end_date)

        # End in the middle of next month
        end_date = session.utcnow().date().replace(day=14) + timedelta(weeks=4)
        assert base - 10.00 == estimate_balance(self.user, end_date)

        # End in grace-period of next month
        end_date = end_date.replace(day=self.membership_fee_current.booking_begin.days - 1)
        assert base - 5.00 == estimate_balance(self.user, end_date)

    def test_last_booked__current_not_booked(self):
        assert self.user.has_property('member')
        self.create_transaction_last()
        self.check_current_and_next_month(-5.00)

    def test_last_booked__current_booked(self):
        assert self.user.has_property('member')

        self.create_transaction_last()
        self.create_transaction_current()

        self.check_current_and_next_month(-5.00)

    def test_last_not_booked__current_not_booked(self):
        assert self.user.has_property('member')

        self.check_current_and_next_month(-5.00)

    def test_last_not_due__current_not_booked(self):
        self.user_membership.active_during \
            = closedopen(self.membership_fee_current.begins_on, None)
        assert self.user.has_property('member')
        self.check_current_and_next_month(0.00)

    def test_free_membership(self):
        new_start = session.utcnow().replace(day=self.membership_fee_current.booking_end.days + 1)
        self.user_membership.active_during = closedopen(new_start, None)
        end_date = last_day_of_month(session.utcnow().date())
        assert estimate_balance(self.user, end_date) == 0.00


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
