# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import warnings

import factory
from factory.faker import Faker

from pycroft.helpers.interval import closedopen
from pycroft.model.user import User, RoomHistoryEntry, UnixAccount
from .base import BaseFactory
from .facilities import RoomFactory
from .finance import AccountFactory



# `password`
PASSWORD = "{CRYPT}$6$rounds=656000$aeo5Ma91eY3B0DMm$HS7WtvbNAOVO.uBiBC66" \
           "/r0zgIQP5fkjAfVsHhIeqzMUTgpLi1ToK9IwsBYWCzlS20dGrBN7hsickMsFg7Kkg/"

class UserFactory(BaseFactory):
    class Meta:
        model = User

    login = Faker('user_name')
    name = Faker('name')
    registered_at = Faker('date_time')
    password = None
    passwd_hash = PASSWORD
    email = Faker('email')
    account = factory.SubFactory(AccountFactory, type="USER_ASSET")
    room = factory.SubFactory(RoomFactory)
    address = factory.SelfAttribute('room.address')
    unix_account = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Set `password_hash` only when `password` is not set.

        See https://factoryboy.readthedocs.io/en/stable/recipes.html#custom-manager-methods.
        """
        assert 'password' in kwargs
        assert 'passwd_hash' in kwargs
        if kwargs.get('password'):
            kwargs.pop('passwd_hash')
        return super()._create(model_class, *args, **kwargs)

    class Params:
        with_unix_account = factory.Trait(
            unix_account=factory.SubFactory('tests.factories.user.UnixAccountFactory',
                                            login=factory.SelfAttribute('..login'))
        )
        with_membership = factory.Trait(
            membership=factory.RelatedFactory('tests.factories.property.MembershipFactory',
                                              'user')
        )
        with_host = factory.Trait(
            host=factory.RelatedFactory('tests.factories.host.HostFactory', 'owner',
                                        room=factory.SelfAttribute('..room'))
        )
        # needs either with_host or a room!
        patched = factory.Trait(room__patched_with_subnet=True)
        without_room = factory.Trait(
            room=None,
            address=factory.SubFactory('tests.factories.address.AddressFactory'),
        )

    @factory.post_generation
    def room_history_entries(self, create, extracted, **kwargs):
        """Create a room history entry, which is required for consistency reasons."""
        if create and self.room is not None:
            # Set room history entry begin to registration date
            rhe = RoomHistoryEntry.q.filter_by(user=self, room=self.room).one()
            rhe.active_during = closedopen(self.registered_at, None)

            for key, value in kwargs.items():
                setattr(rhe, key, value)


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
