# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from factory import SubFactory
from factory.faker import Faker

from pycroft.model.user import User
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
    account = SubFactory(AccountFactory, type="USER_ASSET")
    room = SubFactory(RoomFactory)
    # TODO: create subclasses for `dummy` and `privileged` user
    # Q: How can we add memberships on the factory level?
    # A: By using `RelatedFactory, although that can only do one`
