# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import functools

import factory
from factory.faker import Faker

from pycroft.helpers.user import hash_password
from pycroft.model.user import User, RoomHistoryEntry, UnixAccount
from .base import BaseFactory
from .facilities import RoomFactory
from .finance import AccountFactory


@functools.lru_cache()
def cached_hash(plaintext):
    return hash_password(plaintext)

class UserFactory(BaseFactory):
    class Meta:
        model = User
        exclude = ('password',)

    login = Faker('user_name')
    name = Faker('name')
    registered_at = Faker('date_time')
    password = Faker('password')
    passwd_hash = factory.LazyAttribute(lambda o: cached_hash(o.password))
    email = Faker('email')
    account = factory.SubFactory(AccountFactory, type="USER_ASSET")
    room = factory.SubFactory(RoomFactory)
    address = factory.SelfAttribute('room.address')
    unix_account = None

    class Params:
        with_unix_account = factory.Trait(
            unix_account=factory.SubFactory('tests.factories.user.UnixAccountFactory',
                                            login=factory.SelfAttribute('..login'))
        )

    @factory.post_generation
    def room_history_entries(self, create, extracted, **kwargs):
        """Create a room history entry, which is required for consistency reasons."""
        if create and self.room is not None:
            # Set room history entry begin to registration date

            rhe = RoomHistoryEntry.q.filter_by(user=self, room=self.room).one()

            rhe.begins_at = self.registered_at

            for key, value in kwargs.items():
                setattr(rhe, key, value)


class UserWithHostFactory(UserFactory):
    host = factory.RelatedFactory('tests.factories.host.HostFactory', 'owner',
                                  room=factory.SelfAttribute('..room'))

    class Params:
        patched = factory.Trait(room__patched_with_subnet=True)


class UserWithMembershipFactory(UserFactory):
    membership = factory.RelatedFactory('tests.factories.property.MembershipFactory', 'user')

class UnixAccountFactory(BaseFactory):
    class Meta:
        model = UnixAccount

    class Params:
        login = Faker('user_name')

    uid = None
    gid = None
    login_shell = None

    @factory.lazy_attribute
    def home_directory(self):
        return f"/home/{self.login}"
