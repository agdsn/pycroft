# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import cStringIO as StringIO
from datetime import date, datetime, time, timedelta
import pkgutil

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from pycroft import config
from pycroft.helpers.interval import closedopen, openclosed, single
from pycroft.lib.finance import (
    post_fees, cleanup_description, get_current_semester, import_journal_csv,
    simple_transaction, transferred_amount, Fee, LateFee, RegistrationFee,
    SemesterFee, get_semester_for_date)
from pycroft.lib.property import create_membership
from pycroft.model.finance import (
    FinanceAccount, Journal, JournalEntry, Transaction)
from pycroft.model.property import PropertyGroup
from pycroft.model import session
from pycroft.model.user import User
from tests import FixtureDataTestBase
from tests.lib.fixtures.finance_fixtures import (
    FinanceAccountData, JournalData, MembershipData, PropertyData,
    PropertyGroupData, SemesterData, SplitData, TransactionData, UserData)


class Test_010_Journal(FixtureDataTestBase):

    datasets = [FinanceAccountData, JournalData, SemesterData, UserData]

    def setUp(self):
        super(Test_010_Journal, self).setUp()
        self.asset_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.Asset.name
        ).one()
        self.liability_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.Liability.name
        ).one()
        self.expense_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.Expense.name
        ).one()
        self.revenue_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.Revenue.name
        ).one()
        self.journal = Journal.q.filter_by(
            account_number=JournalData.Journal1.account_number
        ).one()
        self.author = User.q.filter_by(
            login=UserData.dummy.login
        ).one()

    def test_0010_import_journal_csv(self):
        """
        This test should verify that the csv import works as expected.
        """
        data = pkgutil.get_data(__package__, "data_test_finance.csv")
        f = StringIO.StringIO(data)

        import_journal_csv(f, 4342, date(2015, 1, 1))

        journal = (Journal.q
                   .filter(Journal.iban == JournalData.Journal1.iban)
                   .one())

        # test for correct dataimport
        entry = JournalEntry.q.filter_by(
            journal=journal,
            original_description=u"0000-3, SCH, AAA, ZW41D/01 99 1, SS 13"
        ).first()
        self.assertEquals(entry.other_account_number, "12345678")
        self.assertEquals(entry.other_routing_number, "80040400")
        self.assertEquals(entry.other_name, u"SCH, AAA")
        self.assertEquals(entry.amount, 900000)
        self.assertEquals(entry.posted_at, date(2013, 1, 2))
        self.assertEquals(entry.valid_on, date(2013, 1, 2))

        # verify that the right year gets chosen for the transaction
        entry = JournalEntry.q.filter_by(
            journal=journal,
            original_description=u"Pauschalen"
        ).first()
        self.assertEquals(entry.posted_at, date(2012, 12, 24))
        self.assertEquals(entry.valid_on, date(2012, 12, 24))

        # verify that a negative amount is imported correctly
        self.assertEquals(entry.amount, -600)

        # verify that the correct transaction year gets chosen for a valuta date
        # which is in the next year
        entry = JournalEntry.q.filter_by(
            journal=journal,
            original_description=u"BESTELLUNG SUPERMEGATOLLER SERVER"
        ).first()
        self.assertEquals(entry.posted_at, date(2013, 12, 29))
        self.assertEquals(entry.valid_on, date(2013, 1, 10))

        JournalEntry.q.delete()
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
                u"transaction", self.asset_account, self.liability_account,
                9000, self.author
            )
        except Exception:
            self.fail()
        Transaction.q.delete()
        session.session.commit()

    def test_0030_transferred_value(self):
        amount = 9000
        today = session.utcnow().date()
        simple_transaction(
            u"transaction", self.asset_account, self.liability_account,
            amount, self.author, today - timedelta(1)
        )
        simple_transaction(
            u"transaction", self.asset_account, self.liability_account,
            amount, self.author, today
        )
        simple_transaction(
            u"transaction", self.asset_account, self.liability_account,
            amount, self.author, today + timedelta(1)
        )
        self.assertEqual(
            transferred_amount(
                self.asset_account, self.liability_account, single(today)
            ),
            amount
        )
        self.assertEqual(
            transferred_amount(
                self.asset_account, self.liability_account, closedopen(today, None)
            ),
            2*amount
        )
        self.assertEqual(
            transferred_amount(
                self.asset_account, self.liability_account, openclosed(None, today)
            ),
            2*amount
        )
        self.assertEqual(
            transferred_amount(
                self.asset_account, self.liability_account
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
                                 u"space SVWZ+A description with parasitic " \
                                 u"spaces at multiples of 28"
        sepa_description = u"EREF+Long EREF 1234567890 w ith a parasitic space " \
                           u"SVWZ+A description with par asitic spaces at " \
                           u"multiples  of 28"
        self.assertEqual(cleanup_description(sepa_description), clean_sepa_description)


class FeeTestBase(FixtureDataTestBase):
    def setUp(self):
        super(FeeTestBase, self).setUp()
        self.user = User.q.first()
        self.processor = self.user
        self.fee_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.fee_account.name
        ).one()

    def assertFeesPosted(self, user, expected_transactions):
        actual_transactions = map(
            lambda t: (
                t.description,
                t.valid_on,
                t.splits[0].amount
                if t.splits[0].account == user.finance_account else
                t.splits[1].amount),
            user.finance_account.transactions
        )
        self.assertEqual(expected_transactions, actual_transactions)


class Test_Fees(FeeTestBase):
    datasets = (FinanceAccountData, SemesterData, UserData)
    description = u"Fee"
    valid_on = datetime.utcnow().date()
    amount = 9000
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
        description = config['finance']['adjustment_description'].format(
            original_description=self.description,
            original_valid_on=self.valid_on
        )
        correction = [(description, self.valid_on, -self.amount)]
        self.assertFeesPosted(self.user, [self.params] * 2 + correction)

    def test_automatic_adjustment_idempotency(self):
        double_fee = self.FeeMock(self.fee_account, [self.params] * 2)
        post_fees([self.user], [double_fee], self.processor)
        single_fee = self.FeeMock(self.fee_account, [self.params])
        post_fees([self.user], [single_fee], self.processor)
        description = config['finance']['adjustment_description'].format(
            original_description=self.description,
            original_valid_on=self.valid_on
        )
        correction = [(description, self.valid_on, -self.amount)]
        post_fees([self.user], [single_fee], self.processor)
        self.assertFeesPosted(self.user, [self.params] * 2 + correction)


class TestRegistrationFee(FeeTestBase):
    datasets = [FinanceAccountData, MembershipData, PropertyData, SemesterData,
                UserData]

    def setUp(self):
        super(TestRegistrationFee, self).setUp()
        self.fee = RegistrationFee(self.fee_account)

    def test_registration_fee(self):
        description = config["finance"]["registration_fee_description"]
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
    datasets = [FinanceAccountData, MembershipData, PropertyData,
                PropertyGroupData, SemesterData, UserData]

    def setUp(self):
        super(TestSemesterFee, self).setUp()
        self.fee = SemesterFee(self.fee_account)
        self.away_group = PropertyGroup.q.filter_by(
            name=PropertyGroupData.away.name
        ).one()
        self.garbage = []

    def tearDown(self):
        for obj in self.garbage:
            session.session.delete(obj)
        self.garbage = []
        super(TestSemesterFee, self).tearDown()

    def expected_debt(self, semester, regular=True):
        description = config["finance"]["semester_fee_description"]
        registered_at = self.user.registered_at.date()
        if semester.begins_on <= registered_at <= semester.ends_on:
            valid_on = registered_at
        else:
            valid_on = semester.begins_on
        amount = (semester.regular_semester_fee
                  if regular else
                  semester.reduced_semester_fee)
        return description.format(semester=semester.name), valid_on, amount

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
        self.garbage.append(create_membership(
            begin, end - semester.reduced_semester_fee_threshold,
            self.user, self.away_group
        ))
        self.assertEqual(self.fee.compute(self.user), [
            self.expected_debt(SemesterData.with_registration_fee),
            self.expected_debt(semester, False)
        ])


class TestLateFee(FeeTestBase):
    datasets = [FinanceAccountData, MembershipData, PropertyData,
                PropertyGroupData, SemesterData, UserData]

    allowed_overdraft = 500
    payment_deadline = timedelta(31)
    valid_on = SemesterData.with_registration_fee.begins_on
    description = u"Fee description"
    amount = 1000

    def setUp(self):
        super(TestLateFee, self).setUp()
        self.fee_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.late_fee_account.name
        ).one()
        self.fee = LateFee(self.fee_account, date.today())
        self.other_fee_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.fee_account.name
        ).one()
        self.bank_account = FinanceAccount.q.filter_by(
            name=FinanceAccountData.bank_account.name
        ).one()

    def late_fee_for(self, transaction):
        description = config['finance']['late_fee_description'].format(
            original_valid_on=transaction.valid_on)
        valid_on = (transaction.valid_on + self.payment_deadline +
                    timedelta(days=1))
        amount = get_semester_for_date(valid_on).late_fee
        return description, amount, valid_on

    def book_a_fee(self):
        return simple_transaction(
            self.description, self.other_fee_account, self.user.finance_account,
            self.amount, self.user, self.valid_on)

    def pay_fee(self, delta):
        return simple_transaction(
            self.description, self.user.finance_account, self.bank_account,
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
                           self.user.finance_account, late_fee[1], self.user,
                           late_fee[2])
        self.pay_fee(self.payment_deadline + timedelta(days=1))
        session.session.commit()
        self.assertEqual(self.fee.compute(self.user),
                         [self.late_fee_for(transaction)])
