# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from factory import SubFactory, LazyAttribute, RelatedFactory
from factory.faker import Faker

from pycroft.helpers.date import last_day_of_month
from pycroft.model import session

from pycroft.model.finance import Account, BankAccount, MembershipFee, Split, \
    Transaction

from .base import BaseFactory


class AccountFactory(BaseFactory):
    class Meta:
        model = Account

    name = Faker('word')
    type = Faker('random_element', elements=(
        "ASSET",  # Aktivkonto
        "USER_ASSET",  # Aktivkonto for users
        "BANK_ASSET",  # Aktivkonto for bank accounts
        "LIABILITY",  # Passivkonto
        "EXPENSE",  # Aufwandskonto
        "REVENUE",  # Ertragskonto
    ))


class BankAccountFactory(BaseFactory):
    class Meta:
        model = BankAccount

    name = Faker('word')
    bank = Faker('word')
    account_number = Faker('random_number', digits=10)
    routing_number = Faker('random_number', digits=8)
    iban = Faker('iban')
    bic = Faker('random_number', digits=11)
    fints_endpoint = Faker('url')
    account = SubFactory(AccountFactory, type='BANK_ASSET')


class MembershipFeeFactory(BaseFactory):
    class Meta:
        model = MembershipFee

    name = Faker('word')
    regular_fee = 5.00
    booking_begin = timedelta(3)
    booking_end = timedelta(14)
    payment_deadline = timedelta(14)
    payment_deadline_final = timedelta(62)
    begins_on = LazyAttribute(lambda o: session.utcnow().date().replace(day=1))
    ends_on = LazyAttribute(lambda o: last_day_of_month(session.utcnow()))


class SplitFactory(BaseFactory):
    class Meta:
        model = Split

    # Required
    amount = 0

    account = SubFactory(AccountFactory, type='EXPENSE')

    # Required
    transaction = None


class TransactionFactory(BaseFactory):
    class Meta:
        model = Transaction

    description = Faker('word')
    author = SubFactory('tests.factories.user.UserFactory')

    posted_at = Faker('date')
    valid_on = Faker('date')

    confirmed = True

    split_1 = RelatedFactory(SplitFactory,
                             factory_related_name='transaction',
                             amount=5)

    split_2 = RelatedFactory(SplitFactory,
                             factory_related_name='transaction',
                             amount=-5)
