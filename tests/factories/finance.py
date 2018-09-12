# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from factory import SubFactory
from factory.faker import Faker

from pycroft.model.finance import Account, BankAccount

from .base import BaseFactory


class AccountFactory(BaseFactory):
    class Meta:
        model = Account

    name = Faker('word')
    type = Faker('random_element', elements=(
        "ASSET",       # Aktivkonto
        "USER_ASSET",  # Aktivkonto for users
        "BANK_ASSET",  # Aktivkonto for bank accounts
        "LIABILITY",   # Passivkonto
        "EXPENSE",     # Aufwandskonto
        "REVENUE",     # Ertragskonto
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
