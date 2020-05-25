# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import factory
from factory.faker import Faker

from pycroft.model.user import User, RoomHistoryEntry
from .base import BaseFactory
from .facilities import RoomFactory
from .finance import AccountFactory


class UserFactory(BaseFactory):
    class Meta:
        model = User

    login = Faker('user_name')
    name = Faker('name')
    registered_at = Faker('date_time')
    password = Faker('password')
    email = Faker('email')
    account = factory.SubFactory(AccountFactory, type="USER_ASSET")
    room = factory.SubFactory(RoomFactory)
    address = factory.SelfAttribute('room.address')

    @factory.post_generation
    def room_history_entries(self, create, extracted, **kwargs):
        if self.room is not None:
            # Set room history entry begin to registration date

            rhe = RoomHistoryEntry.q.filter_by(user=self, room=self.room).one()

            rhe.begins_at = self.registered_at

            for key, value in kwargs.items():
                setattr(rhe, key, value)


class UserWithHostFactory(UserFactory):
    host = factory.RelatedFactory('tests.factories.host.HostFactory', 'owner')


class UserWithMembershipFactory(UserFactory):
    membership = factory.RelatedFactory('tests.factories.property.MembershipFactory', 'user')
