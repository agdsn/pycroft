# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import operator
import pkgutil
import unittest
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from pycroft._compat import StringIO
from pycroft.helpers.interval import closed, closedopen, openclosed, single
from pycroft.lib.finance import (
    Fee, LateFee, RegistrationFee, SemesterFee, adjustment_description,
    cleanup_description, get_current_semester, get_semester_for_date,
    import_bank_account_activities_csv, post_fees, simple_transaction,
    transferred_amount,
    is_ordered)
from pycroft.lib.user import make_member_of
from pycroft.model import session
from pycroft.model.finance import (
    Account, BankAccount, BankAccountActivity, Transaction)
from pycroft.model.user import PropertyGroup, User
from tests import FixtureDataTestBase
from tests.fixtures.config import ConfigData, PropertyGroupData, PropertyData
from tests.lib.finance_fixtures import (
    AccountData, BankAccountData, MembershipData, SemesterData, UserData)


class Test_010_BankAccount(FixtureDataTestBase):

    datasets = [AccountData, BankAccountData, SemesterData, UserData]

    def setUp(self):
        super(Test_010_BankAccount, self).setUp()
        self.fee_account = Account.q.filter_by(
            name=AccountData.semester_fee_account.name
        ).one()
        self.user_account = Account.q.filter_by(
            name=AccountData.user_account.name
        ).one()
        self.author = User.q.filter_by(
            login=UserData.dummy.login
        ).one()

    def test_0010_import_bank_account_csv(self):
        """
        This test should verify that the csv import works as expected.
        """
        data = pkgutil.get_data(__package__, "data_test_finance.csv")
        f = StringIO(data)

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
        self.assertEqual(activity.posted_at, date(2013, 1, 2))
        self.assertEqual(activity.valid_on, date(2013, 1, 2))

        # verify that the right year gets chosen for the transaction
        activity = BankAccountActivity.q.filter_by(
            bank_account=bank_account,
            original_reference=u"Pauschalen"
        ).first()
        self.assertEqual(activity.posted_at, date(2012, 12, 24))
        self.assertEqual(activity.valid_on, date(2012, 12, 24))

        # verify that a negative amount is imported correctly
        self.assertEqual(activity.amount, -6.00)

        # verify that the correct transaction year gets chosen for a valuta date
        # which is in the next year
        activity = BankAccountActivity.q.filter_by(
            bank_account=bank_account,
            original_reference=u"BESTELLUNG SUPERMEGATOLLER SERVER"
        ).first()
        self.assertEqual(activity.posted_at, date(2013, 12, 29))
        self.assertEqual(activity.valid_on, date(2013, 1, 10))

        BankAccountActivity.q.delete()
        session.session.commit()

    def test_0020_get_current_semester(self):
        try:
            get_current_semester()
        except NoResultFound:
            self.fail("No semester found")
        except MultipleResultsFound:
            self.fail("Multiple semesters found")

    def test_0030_simple_transaction(self):
        try:
            simple_transaction(
                u"transaction", self.fee_account, self.user_account,
                90.00, self.author
            )
        except Exception:
            self.fail()
        Transaction.q.delete()
        session.session.commit()

    def test_0030_transferred_value(self):
        amount = 90.00
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
        print type(transferred_amount(
                self.fee_account, self.user_account, single(today)
            ))
        print type(amount)
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


class Test_Fees(FeeTestBase):
    datasets = (AccountData, ConfigData, PropertyData, SemesterData, UserData)
    fee_account_name = ConfigData.config.semester_fee_account.name
    description = u"Fee"
    valid_on = datetime.utcnow().date()
    amount = 90.00
    params = (description, valid_on, amount)

    class FeeMock(Fee):
        def __init__(self, account, params):
            super(Test_Fees.FeeMock, self).__init__(account)
            self.params = params

        def compute(self, user):
            return self.params

    def test_fee_posting(self):
        """Verify that fees are posted correctly to user accounts."""
        fee = self.FeeMock(self.fee_account, [self.params])
        post_fees([self.user], [fee], self.processor)
        self.assertFeesPosted(self.user, [self.params])

    def test_idempotency(self):
        """Test that subsequent invocations won't post additional fees."""
        fee = self.FeeMock(self.fee_account, [self.params])
        post_fees([self.user], [fee], self.processor)
        post_fees([self.user], [fee], self.processor)
        self.assertFeesPosted(self.user, [self.params])

    def test_automatic_adjustment(self):
        # Post fee twice
        double_fee = self.FeeMock(self.fee_account, [self.params] * 2)
        post_fees([self.user], [double_fee], self.processor)
        single_fee = self.FeeMock(self.fee_account, [self.params])
        post_fees([self.user], [single_fee], self.processor)
        description = adjustment_description.format(
            original_description=self.description,
            original_valid_on=self.valid_on
        ).to_json()
        correction = [(description, self.valid_on, -self.amount)]
        self.assertFeesPosted(self.user, [self.params] * 2 + correction)

    def test_automatic_adjustment_idempotency(self):
        double_fee = self.FeeMock(self.fee_account, [self.params] * 2)
        post_fees([self.user], [double_fee], self.processor)
        single_fee = self.FeeMock(self.fee_account, [self.params])
        post_fees([self.user], [single_fee], self.processor)
        description = adjustment_description.format(
            original_description=self.description,
            original_valid_on=self.valid_on
        ).to_json()
        correction = [(description, self.valid_on, -self.amount)]
        post_fees([self.user], [single_fee], self.processor)
        self.assertFeesPosted(self.user, [self.params] * 2 + correction)


class TestRegistrationFee(FeeTestBase):
    datasets = (AccountData, ConfigData, MembershipData, PropertyData,
                SemesterData, UserData)
    fee_account_name = ConfigData.config.registration_fee_account.name

    def setUp(self):
        super(TestRegistrationFee, self).setUp()
        self.fee = RegistrationFee(self.fee_account)

    def test_registration_fee(self):
        description = RegistrationFee.description
        amount = SemesterData.with_registration_fee.registration_fee
        valid_on = self.user.registered_at.date()
        self.assertEqual(self.fee.compute(self.user), [(description, valid_on, amount)])

    def test_property_absent(self):
        self.user.memberships = []
        self.assertEqual(self.fee.compute(self.user), [])

    def test_fee_zero(self):
        self.user.registered_at = datetime.combine(
            SemesterData.without_registration_fee.begins_on,
            time.min
        )
        self.assertEqual(self.fee.compute(self.user), [])


class TestSemesterFee(FeeTestBase):
    datasets = (AccountData, ConfigData, MembershipData, PropertyData,
                PropertyGroupData, SemesterData, UserData)
    fee_account_name = ConfigData.config.semester_fee_account.name

    def setUp(self):
        super(TestSemesterFee, self).setUp()
        self.fee = SemesterFee(self.fee_account)
        self.away_group = PropertyGroup.q.filter_by(
            name=PropertyGroupData.away.name
        ).one()

    def expected_debt(self, semester, regular=True):
        description = (SemesterFee.description.format(semester=semester.name)
                       .to_json())
        registered_at = self.user.registered_at.date()
        if semester.begins_on <= registered_at <= semester.ends_on:
            valid_on = registered_at
        else:
            valid_on = semester.begins_on
        amount = (semester.regular_semester_fee
                  if regular else
                  semester.reduced_semester_fee)
        return description, valid_on, amount

    def set_registered_at(self, when):
        registered_at = datetime.combine(when, time.min)
        self.user.registered_at = registered_at
        for membership in self.user.memberships:
            membership.begins_at = registered_at

    def test_semester_fee(self):
        self.assertEqual(self.fee.compute(self.user), [
            self.expected_debt(SemesterData.with_registration_fee),
            self.expected_debt(SemesterData.without_registration_fee)
        ])

    def test_property_absent(self):
        self.user.memberships = []
        self.assertEqual(self.fee.compute(self.user), [])

    def test_grace_period(self):
        semester = SemesterData.with_registration_fee
        self.set_registered_at(
            semester.ends_on - semester.grace_period)
        self.assertEqual(self.fee.compute(self.user), [self.expected_debt(
            SemesterData.without_registration_fee)])

    def test_away(self):
        semester = SemesterData.without_registration_fee
        begin = datetime.combine(
            semester.begins_on, time.min
        )
        end = datetime.combine(
            semester.ends_on, time.min
        )
        make_member_of(self.user, self.away_group, self.processor, closed(
            begin, end - semester.reduced_semester_fee_threshold))
        self.assertEqual(self.fee.compute(self.user), [
            self.expected_debt(SemesterData.with_registration_fee),
            self.expected_debt(semester, False)
        ])


class TestLateFee(FeeTestBase):
    datasets = (AccountData, ConfigData, MembershipData, PropertyData,
                PropertyGroupData, SemesterData, UserData)
    fee_account_name = ConfigData.config.late_fee_account.name

    allowed_overdraft = 5.00
    payment_deadline = timedelta(31)
    valid_on = SemesterData.with_registration_fee.begins_on
    description = u"Fee description"
    amount = 10.00

    def setUp(self):
        super(TestLateFee, self).setUp()
        self.fee = LateFee(self.fee_account, date.today())
        self.other_fee_account = Account.q.filter_by(
            name=ConfigData.config.semester_fee_account.name
        ).one()
        self.bank_account = Account.q.filter_by(
            name=AccountData.bank_account.name
        ).one()

    def late_fee_for(self, transaction):
        description = LateFee.description.format(
            original_valid_on=transaction.valid_on).to_json()
        valid_on = (transaction.valid_on + self.payment_deadline +
                    timedelta(days=1))
        amount = get_semester_for_date(valid_on).late_fee
        return description, amount, valid_on

    def book_a_fee(self):
        return simple_transaction(
            self.description, self.other_fee_account, self.user.account,
            self.amount, self.user, self.valid_on)

    def pay_fee(self, delta):
        return simple_transaction(
            self.description, self.user.account, self.bank_account,
            self.amount, self.user, self.valid_on + delta)

    def test_no_fees_bocked(self):
        self.assertEqual(self.fee.compute(self.user), [])

    def test_booked_fee_paid_in_time(self):
        self.book_a_fee()
        self.pay_fee(self.payment_deadline - timedelta(days=1))
        session.session.commit()
        self.assertEqual(self.fee.compute(self.user), [])

    def test_booked_fee_unpaid(self):
        transaction = self.book_a_fee()
        session.session.commit()
        self.assertEqual(self.fee.compute(self.user),
                         [self.late_fee_for(transaction)])

    def test_booked_fee_paid_too_late(self):
        transaction = self.book_a_fee()
        self.pay_fee(self.payment_deadline + timedelta(days=1))
        session.session.commit()
        self.assertEqual(self.fee.compute(self.user),
                         [self.late_fee_for(transaction)])

    def test_booked_fee_paid_too_late_with_late_fee_already_booked(self):
        transaction = self.book_a_fee()
        late_fee = self.late_fee_for(transaction)
        simple_transaction(late_fee[0], self.fee_account,
                           self.user.account, late_fee[1], self.user,
                           late_fee[2])
        self.pay_fee(self.payment_deadline + timedelta(days=1))
        session.session.commit()
        self.assertEqual(self.fee.compute(self.user),
                         [self.late_fee_for(transaction)])


class TestIsOrdered(unittest.TestCase):
    def test_ordered(self):
        self.assertTrue(is_ordered((1, 2, 3)))
        self.assertFalse(is_ordered((1, 3, 2)))
        self.assertTrue(is_ordered((3, 2, 1), relation=operator.gt))
