# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from factory import SubFactory, LazyAttribute
from factory.alchemy import SQLAlchemyModelFactory as Factory
from factory.faker import Faker

from pycroft.model.facilities import Site, Building, Room
from pycroft.model.finance import Account
from pycroft.model.session import session
from pycroft.model.user import User


class BaseFactory(Factory):
    class Meta:
        sqlalchemy_session = session


class SiteFactory(BaseFactory):
    class Meta:
        model = Site

    name = Faker('street_name')


class BuildingFactory(BaseFactory):
    class Meta:
        model = Building

    site = SubFactory(SiteFactory)

    number = Faker('building_number')
    street = LazyAttribute(lambda b: b.site.name)
    short_name = LazyAttribute(lambda b: "{}{}".format(b.street[:3], b.number))


class RoomFactory(BaseFactory):
    class Meta:
        model = Room

    number = Faker('numerify', text='## #')
    level = Faker('random_int', min=0, max=16)
    inhabitable = Faker('boolean')

    building = SubFactory(BuildingFactory)


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


class UserFactory(BaseFactory):
    class Meta:
        model = User

    login = Faker('user_name')
    name = Faker('name')
    registered_at = Faker('date_time')
    password = Faker('password')
    email = Faker('email')
    account = SubFactory(AccountFactory, type="USER_ASSET")
    room = SubFactory(RoomFactory)
    # TODO: create subclasses for `dummy` and `privileged` user
