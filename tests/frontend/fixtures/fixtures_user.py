#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import datetime
from fixture import DataSet

from pycroft.helpers.user import hash_password
from fixtures_dormitory import RoomData


class BaseUser():
    """Data every user model needs"""
    name = "John Die"
    passwd_hash = hash_password("password")
    registration_date = datetime.datetime.utcnow()
    room = RoomData.dummy_room1  # yes, they all live in the same room


class UserData(DataSet):
    class user1_admin(BaseUser):
        # Normal admin
        login = "admin"

    class user2_finance(BaseUser):
        # Admin with permission to view Finance
        login = "finanzer"

    class user3_user(BaseUser):
        # User without any usergroup
        login = "user"
