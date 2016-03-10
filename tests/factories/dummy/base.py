# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime

from factory import SubFactory, LazyAttribute
from factory.alchemy import SQLAlchemyModelFactory as Factory
from factory.fuzzy import FuzzyChoice, FuzzyDateTime, FuzzyInteger, FuzzyText

from pycroft.model.session import session
from pycroft.model.facilities import Site, Building, Room
from pycroft.model.finance import Account
from pycroft.model.user import User

from tests.factories.dummy.utc import utc


class BaseFactory(Factory):
    class Meta:
        sqlalchemy_session = session


class SiteFactory(BaseFactory):
    class Meta:
        model = Site

    name = FuzzyText()


class BuildingFactory(BaseFactory):
    class Meta:
        model = Building

    site = SubFactory(SiteFactory)
    site_id = LazyAttribute(lambda self: self.site.id)

    number = FuzzyText(length=3)
    short_name = FuzzyText(length=8)
    street = FuzzyText(length=20)


class RoomFactory(BaseFactory):
    class Meta:
        model = Room

    number = FuzzyText(length=36)
    level = FuzzyInteger(0)
    inhabitable = FuzzyChoice([True, False])

    # many to one from Room to Building
    building = SubFactory(BuildingFactory)
    building_id = LazyAttribute(lambda self: self.building.id)


class AccountFactory(BaseFactory):
    class Meta:
        model = Account

    name = FuzzyText(length=127)
    type = FuzzyChoice([
        "ASSET",       # Aktivkonto
        "USER_ASSET",  # Aktivkonto for users
        "BANK_ASSET",  # Aktivkonto for bank accounts
        "LIABILITY",   # Passivkonto
        "EXPENSE",     # Aufwandskonto
        "REVENUE",     # Ertragskonto
    ])


class UserFactory(BaseFactory):
    class Meta:
        model = User

    login = FuzzyText(length=40)
    name = FuzzyText(length=255)
    registered_at = FuzzyDateTime(datetime(2001, 9, 11, tzinfo=utc))
    passwd_hash = FuzzyText()
    email = FuzzyText(length=255)
    # one to one from User to Account
    account = SubFactory(AccountFactory)
    account_id = LazyAttribute(lambda self: self.account.id)

    # many to one from User to Room
    room = SubFactory(RoomFactory)
    room_id = LazyAttribute(lambda self: self.room.id)
    # TODO: create subclasses for `dummy` and `privileged` user
