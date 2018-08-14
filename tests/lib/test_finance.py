# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import operator
import pkgutil
import unittest
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import StringIO

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from pycroft.helpers.interval import closed, closedopen, openclosed, single
from pycroft.lib.finance import (
    cleanup_description,
    import_bank_account_activities_csv, simple_transaction,
    transferred_amount,
    is_ordered, get_last_applied_membership_fee,
    get_membership_fee_for_date, handle_payments_in_default,
    end_payment_in_default_memberships, membership_fee_description)
from pycroft.lib.membership import make_member_of
from pycroft.model import session
from pycroft.model.finance import (
    Account, BankAccount, BankAccountActivity, Transaction)
from pycroft.model.user import PropertyGroup, User, Membership
from tests import FixtureDataTestBase
from tests.fixtures.config import ConfigData, PropertyGroupData, PropertyData
from tests.lib.finance_fixtures import (
    AccountData, BankAccountData, MembershipData, UserData,
    MembershipFeeData)


class Test_010_BankAccount(FixtureDataTestBase):

    datasets = [AccountData, BankAccountData, MembershipFeeData, UserData]

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

        import_bank_account_activities_csv(f, Decimal('43.42'), date(2015, 1, 1))

        bank_account = BankAccount.q.filter(
            BankAccount.iban == BankAccountData.dummy.iban
        ).one()

        # test for correct dataimport
        activity = BankAccountActivity.q.filter_by(
            bank_account=bank_account,
            original_reference=u"0000-3, SCH, AAA, ZW41D/01 99 1, SS 13"
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
            original_reference=u"Pauschalen"
        ).first()
        self.assertEqual(activity.posted_on, date(2012, 12, 24))
        self.assertEqual(activity.valid_on, date(2012, 12, 24))

        # verify that a negative amount is imported correctly
        self.assertEqual(activity.amount, -6.00)

        # verify that the correct transaction year gets chosen for a valuta date
        # which is in the next year
        activity = BankAccountActivity.q.filter_by(
            bank_account=bank_account,
            original_reference=u"BESTELLUNG SUPERMEGATOLLER SERVER"
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
            2*amount
        )
        self.assertEqual(
            transferred_amount(
                self.fee_account, self.user_account, openclosed(None, today)
            ),
            2*amount
        )
        self.assertEqual(
            transferred_amount(
                self.fee_account, self.user_account
            ),
            3*amount
        )
        Transaction.q.delete()
        session.session.commit()

    def test_0050_cleanup_non_sepa_description(self):
        non_sepa_description = u"1234-0 Dummy, User, with " \
                               u"a- space at postition 28"
        self.assertEqual(cleanup_description(non_sepa_description), non_sepa_description)

    def test_0060_cleanup_sepa_description(self):
        clean_sepa_description = u"EREF+Long EREF 1234567890 with a parasitic " \
                                 u"space SVWZ+A reference with parasitic " \
                                 u"spaces at multiples of 28"
        sepa_description = u"EREF+Long EREF 1234567890 w ith a parasitic space " \
                           u"SVWZ+A reference with paras itic spaces at " \
                           u"multiples of  28"
        self.assertEqual(cleanup_description(sepa_description), clean_sepa_description)


# TODO: Rework tests for new membership fee implementation
'''
class FeeTestBase(FixtureDataTestBase):
    fee_account_name = None

    def setUp(self):
        super(FeeTestBase, self).setUp()
        self.user = User.q.first()
        self.processor = self.user
        self.fee_account = Account.q.filter_by(
            name=self.fee_account_name
        ).one()

    def assertFeesPosted(self, user, expected_transactions):
        actual_transactions = [
            (t.description,
             t.valid_on,
             t.splits[0].amount if t.splits[0].account == user.account
             else t.splits[1].amount)
            for t in user.account.transactions]
        self.assertEqual(expected_transactions, actual_transactions)


class TestMembershipFee(FeeTestBase):
    datasets = (AccountData, ConfigData, MembershipData, PropertyData,
                PropertyGroupData, MembershipFeeData, UserData)
    fee_account_name = ConfigData.config.membership_fee_account.name

    payment_deadline = timedelta(14)
    valid_on = MembershipFeeData.with_registration_fee.ends_on
    description = u"Fee description"
    amount = Decimal(20.00)

    def setUp(self):
        super(TestMembershipFee, self).setUp()
        self.away_group = PropertyGroup.q.filter_by(
            name=PropertyGroupData.away.name
        ).one()
        self.bank_account = Account.q.filter_by(
            name=AccountData.bank_account.name).one()

    def expected_debt(self, fee):
        description = memvership_fee_description.format(fee_name=fee.name).to_json()

        valid_on = fee.ends_on

        amount = fee.regular_fee

        return description, valid_on, amount

    def set_registered_at(self, when):
        registered_at = datetime.combine(when, time.min)
        self.user.registered_at = registered_at
        for membership in self.user.memberships:
            membership.begins_at = registered_at

    def test_membership_fee(self):
        self.assertEqual(self.fee.compute(self.user), [
            self.expected_debt(MembershipFeeData.with_registration_fee),
            self.expected_debt(MembershipFeeData.without_registration_fee)
        ])

    def test_property_absent(self):
        self.user.memberships = []
        self.assertEqual(self.fee.compute(self.user), [])

    def test_grace_period(self):
        fee = MembershipFeeData.with_registration_fee
        self.set_registered_at(
            fee.ends_on - fee.grace_period)
        self.assertEqual(self.fee.compute(self.user), [self.expected_debt(
            MembershipFeeData.without_registration_fee)])

    def test_away(self):
        fee = MembershipFeeData.without_registration_fee
        begin = datetime.combine(
            fee.begins_on, time.min
        )
        end = datetime.combine(
            fee.ends_on, time.min
        )
        make_member_of(self.user, self.away_group, self.processor, closed(
            begin, end - fee.reduced_fee_threshold))
        self.assertEqual(self.fee.compute(self.user), [
            self.expected_debt(MembershipFeeData.with_registration_fee),
            self.expected_debt(fee, False)
        ])

    def test_payment_in_default_group(self):
        handle_payments_in_default()
        self.assertFalse(self.user.has_property('payment_in_default'))
        membership_fee = MembershipFee(self.fee_account)
        post_fees([self.user], [membership_fee], self.user)
        self.assertFalse(self.user.has_property('payment_in_default'))
        handle_payments_in_default()
        self.assertTrue(self.user.has_property('payment_in_default'))
        simple_transaction(
            self.description, self.user.account, self.bank_account,
            self.amount, self.user, self.valid_on)
        end_payment_in_default_memberships()
        handle_payments_in_default()
        self.assertFalse(self.user.has_property('payment_in_default'))

    def test_payment_in_default_membership_end(self):
        user = User.q.all()[1]

        self.assertFalse(user.has_property('payment_in_default'))
        self.assertTrue(user.has_property('member'))

        membership_fee = MembershipFee(self.fee_account)
        post_fees([user], [membership_fee], self.user)

        handle_payments_in_default()

        self.assertTrue(user.has_property('payment_in_default'))
        self.assertFalse(user.has_property('member'))

    def test_grace(self):
        user = User.q.all()[2]

        membership_fee = MembershipFee(self.fee_account)

        self.assertEqual(post_fees([user], [membership_fee], self.user), [])

    def test_no_grace(self):
        user = User.q.all()[3]

        membership_fee = MembershipFeeData.fee_three

        self.assertEqual(len(post_fees([user], [membership_fee], self.user)), 1)
'''


class TestIsOrdered(unittest.TestCase):
    def test_ordered(self):
        self.assertTrue(is_ordered((1, 2, 3)))
        self.assertFalse(is_ordered((1, 3, 2)))
        self.assertTrue(is_ordered((3, 2, 1), relation=operator.gt))
