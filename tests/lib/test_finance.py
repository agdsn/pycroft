# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import operator
import pkgutil
import unittest
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import StringIO

from factory import Iterator
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from pycroft import config
from pycroft.helpers.date import last_day_of_month
from tests.factories import MembershipFactory, ConfigFactory

from pycroft.helpers.interval import closed, closedopen, openclosed, single
from pycroft.lib.finance import (
    cleanup_description,
    import_bank_account_activities_csv, simple_transaction,
    transferred_amount,
    is_ordered, get_last_applied_membership_fee, estimate_balance,
    post_transactions_for_membership_fee)
from pycroft.lib.membership import make_member_of
from pycroft.model import session
from pycroft.model.finance import (
    Account, BankAccount, BankAccountActivity, Transaction, Split)
from pycroft.model.user import PropertyGroup, User, Membership
from tests import FixtureDataTestBase, FactoryDataTestBase, UserFactory
from tests.factories.finance import MembershipFeeFactory, TransactionFactory, \
    AccountFactory
from tests.factories.user import UserWithMembershipFactory
from tests.fixtures.config import ConfigData, PropertyGroupData, PropertyData
from tests.lib.finance_fixtures import (
    AccountData, BankAccountData, MembershipData, UserData)


class Test_010_BankAccount(FixtureDataTestBase):
    datasets = [AccountData, BankAccountData, UserData]

    def setUp(self):
        super(Test_010_BankAccount, self).setUp()
        self.fee_account = Account.q.filter_by(
            name=AccountData.membership_fee_account.name
        ).one()
        self.user_account = Account.q.filter_by(
            name=AccountData.user_account.name
        ).one()
        self.author = User.q.filter_by(
            login=UserData.dummy_1.login
        ).one()

    def test_0010_import_bank_account_csv(self):
        """
        This test should verify that the csv import works as expected.
        """
        data = pkgutil.get_data(__package__, "data_test_finance.csv")
        f = StringIO(data.decode('utf-8'))

        import_bank_account_activities_csv(f, Decimal('43.42'),
                                           date(2015, 1, 1))

        bank_account = BankAccount.q.filter(
            BankAccount.iban == BankAccountData.dummy.iban
        ).one()

        # test for correct dataimport
        activity = BankAccountActivity.q.filter_by(
            bank_account=bank_account,
            reference=u"0000-3, SCH, AAA, ZW41D/01 99 1, SS 13"
        ).first()
        self.assertEqual(activity.other_account_number, "12345678")
        self.assertEqual(activity.other_routing_number, "80040400")
        self.assertEqual(activity.other_name, u"SCH, AAA")
        self.assertEqual(activity.amount, 9000.00)
        self.assertEqual(activity.posted_on, date(2013, 1, 2))
        self.assertEqual(activity.valid_on, date(2013, 1, 2))

        # verify that the right year gets chosen for the transaction
        activity = BankAccountActivity.q.filter_by(
            bank_account=bank_account,
            reference=u"Pauschalen"
        ).first()
        self.assertEqual(activity.posted_on, date(2012, 12, 24))
        self.assertEqual(activity.valid_on, date(2012, 12, 24))

        # verify that a negative amount is imported correctly
        self.assertEqual(activity.amount, -6.00)

        # verify that the correct transaction year gets chosen for a valuta date
        # which is in the next year
        activity = BankAccountActivity.q.filter_by(
            bank_account=bank_account,
            reference=u"BESTELLUNG SUPERMEGATOLLER SERVER"
        ).first()
        self.assertEqual(activity.posted_on, date(2013, 12, 29))
        self.assertEqual(activity.valid_on, date(2013, 1, 10))

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
                u"transaction", self.fee_account, self.user_account,
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
            u"transaction", self.fee_account, self.user_account,
            amount, self.author, today - timedelta(1)
        )
        simple_transaction(
            u"transaction", self.fee_account, self.user_account,
            amount, self.author, today
        )
        simple_transaction(
            u"transaction", self.fee_account, self.user_account,
            amount, self.author, today + timedelta(1)
        )
        self.assertEqual(
            transferred_amount(
                self.fee_account, self.user_account, single(today)
            ),
            amount
        )
        self.assertEqual(
            transferred_amount(
                self.fee_account, self.user_account, closedopen(today, None)
            ),
            2 * amount
        )
        self.assertEqual(
            transferred_amount(
                self.fee_account, self.user_account, openclosed(None, today)
            ),
            2 * amount
        )
        self.assertEqual(
            transferred_amount(
                self.fee_account, self.user_account
            ),
            3 * amount
        )
        Transaction.q.delete()
        session.session.commit()

    def test_0050_cleanup_non_sepa_description(self):
        non_sepa_description = u"1234-0 Dummy, User, with " \
                               u"a- space at postition 28"
        self.assertEqual(cleanup_description(non_sepa_description),
                         non_sepa_description)

    def test_0060_cleanup_sepa_description(self):
        clean_sepa_description = u"EREF+Long EREF 1234567890 with a parasitic " \
                                 u"space SVWZ+A reference with parasitic " \
                                 u"spaces at multiples of 28"
        sepa_description = u"EREF+Long EREF 1234567890 w ith a parasitic space " \
                           u"SVWZ+A reference with paras itic spaces at " \
                           u"multiples of  28"
        self.assertEqual(cleanup_description(sepa_description),
                         clean_sepa_description)


class MembershipFeeTestCase(FactoryDataTestBase):
    def create_factories(self):
        ConfigFactory.create()

        self.processor = UserFactory.create()

        self.user_until_1st = UserFactory.create()
        self.user_until_13th = UserFactory.create()
        self.user_from_13th = UserFactory.create()
        self.user_from_14th = UserFactory.create()

        self.last_month_last = session.utcnow().replace(day=1) - timedelta(1)
        self.last_month_last_date = self.last_month_last.date()

        self.membership_fee_current = MembershipFeeFactory.create()
        self.membership_fee_last = MembershipFeeFactory.create(
            begins_on=self.last_month_last_date.replace(day=1),
            ends_on=self.last_month_last_date
        )

    def create_user_from1y(self):
        reg_date = session.utcnow() - timedelta(weeks=52),

        return UserWithMembershipFactory(
            registered_at=reg_date,
            membership__begins_at=reg_date,
            membership__ends_at=None,
            membership__group=config.member_group
        )

    def create_user_move_in_grace(self):
        reg_date = self.last_month_last.replace(day=self.membership_fee_last.booking_end.days) + timedelta(1)

        return UserWithMembershipFactory(
            registered_at=reg_date,
            membership__begins_at=reg_date,
            membership__ends_at=None,
            membership__group=config.member_group
        )

    def create_user_move_in_no_grace(self):
        reg_date = self.last_month_last.replace(day=self.membership_fee_last.booking_end.days)

        return UserWithMembershipFactory(
            registered_at=reg_date,
            membership__begins_at=reg_date,
            membership__ends_at=None,
            membership__group=config.member_group
        )

    def create_user_move_out_grace(self):
        reg_date = session.utcnow() - timedelta(weeks=52)

        return UserWithMembershipFactory(
            registered_at=reg_date,
            membership__begins_at=reg_date,
            membership__ends_at=self.last_month_last.replace(day=self.membership_fee_last.booking_begin.days) - timedelta(1),
            membership__group=config.member_group
        )

    def create_user_move_out_no_grace(self):
        reg_date = session.utcnow() - timedelta(weeks=52)

        return UserWithMembershipFactory(
            registered_at=reg_date,
            membership__begins_at=reg_date,
            membership__ends_at=self.last_month_last.replace(day=self.membership_fee_last.booking_begin.days),
            membership__group=config.member_group
        )

    def grace_check(self, user_grace, user_no_grace):
        self.assertEqual(user_grace.account.balance, 0.00,
                         "Initial user grace account balance not zero")
        self.assertEqual(user_no_grace.account.balance, 0.00,
                         "Initial user no grace account balance not zero")

        affected = post_transactions_for_membership_fee(self.membership_fee_last, self.processor)

        session.session.refresh(user_grace.account)
        session.session.refresh(user_no_grace.account)

        self.assertEqual(len(affected), 1, "Wrong affected user count")

        self.assertEqual(user_grace.account.balance, 0.00, "User grace balance not zero")
        self.assertEqual(user_no_grace.account.balance, self.membership_fee_last.regular_fee,
                         "User no grace balance wrong")

    def test_basic_from1y(self):
        user1y = self.create_user_from1y()

        self.assertEqual(user1y.account.balance, 0.00,
                         "Initial user account balance not zero")

        affected = post_transactions_for_membership_fee(self.membership_fee_last, self.processor)

        session.session.refresh(user1y.account)

        self.assertEqual(len(affected), 1,
                         "Wrong affected user count")

        self.assertEqual(user1y.account.balance, self.membership_fee_last.regular_fee,
                         "User balance incorrect")

        transaction = Transaction.q.filter_by(valid_on=self.membership_fee_last.ends_on)\
            .filter(Transaction.description.contains(self.membership_fee_last.name)).first()

        self.assertIsNotNone(transaction, "Transaction not found")

        split_user = Split.q.filter_by(transaction=transaction, account=user1y.account,
                                       amount=self.membership_fee_last.regular_fee).first()

        self.assertIsNotNone(split_user, "User split not found")

        split_fee_account = Split.q.filter_by(transaction=transaction,
                                              account=user1y.room.building.fee_account,
                                              amount=-self.membership_fee_last.regular_fee).first()

        self.assertIsNotNone(split_fee_account, "Fee account split not found")

        affected = post_transactions_for_membership_fee(self.membership_fee_last, self.processor)

        session.session.refresh(user1y.account)

        self.assertEqual(len(affected), 0, "Affected users not zero")

        self.assertEqual(user1y.account.balance, self.membership_fee_last.regular_fee,
                         "User balance changed")

    def test_membership_begin_grace(self):
        user_grace = self.create_user_move_in_grace()
        user_no_grace = self.create_user_move_in_no_grace()

        self.grace_check(user_grace, user_no_grace)

    def test_membership_end_grace(self):
        user_grace = self.create_user_move_out_grace()
        user_no_grace = self.create_user_move_out_no_grace()

        self.grace_check(user_grace, user_no_grace)

    # ToDo: Test payment in default / in default days


class TestIsOrdered(unittest.TestCase):
    def test_ordered(self):
        self.assertTrue(is_ordered((1, 2, 3)))
        self.assertFalse(is_ordered((1, 3, 2)))
        self.assertTrue(is_ordered((3, 2, 1), relation=operator.gt))


class BalanceEstimationTestCase(FactoryDataTestBase):
    def create_factories(self):
        ConfigFactory.create()

        self.user = UserFactory.create()

        self.user_membership = MembershipFactory.create(
            begins_at=session.utcnow() - timedelta(weeks=52),
            ends_at=None,
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
        end_date = session.utcnow().date().replace(
            day=self.membership_fee_current.booking_begin.days - 1)
        self.assertEquals(base, estimate_balance(self.user, end_date))

        # End after grace-period in current month
        end_date = self.membership_fee_current.ends_on
        self.assertEquals(base - 5.00, estimate_balance(self.user, end_date))

        # End in the middle of next month
        end_date = session.utcnow().date().replace(day=14) + timedelta(weeks=4)
        self.assertEquals(base - 10.00, estimate_balance(self.user, end_date))

        # End in grace-period of next month
        end_date = end_date.replace(
            day=self.membership_fee_current.booking_begin.days - 1)
        self.assertEquals(base - 5.00, estimate_balance(self.user, end_date))

    def test_last_booked__current_not_booked(self):
        self.assertTrue(self.user.has_property('member'))

        self.create_transaction_last()

        self.check_current_and_next_month(-5.00)

    def test_last_booked__current_booked(self):
        self.assertTrue(self.user.has_property('member'))

        self.create_transaction_last()
        self.create_transaction_current()

        self.check_current_and_next_month(-5.00)

    def test_last_not_booked__current_not_booked(self):
        self.assertTrue(self.user.has_property('member'))

        self.check_current_and_next_month(-5.00)

    def test_last_not_due__current_not_booked(self):
        self.user_membership.begins_at = self.membership_fee_current.begins_on

        self.assertTrue(self.user.has_property('member'))

        self.check_current_and_next_month(0.00)

    def test_free_membership(self):
        self.user_membership.begins_at = session.utcnow().replace(
            day=self.membership_fee_current.booking_end.days + 1)

        end_date = last_day_of_month(session.utcnow().date())

        self.assertEquals(0.00, estimate_balance(self.user, end_date))
