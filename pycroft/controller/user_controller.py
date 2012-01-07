# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.controller.user_controller
    ~~~~~~~~~~~~~~

    This package contains the classes UserController.

    :copyright: (c) 2011 by AG DSN.
"""
from pycroft.model import user

class UserController:

    @staticmethod
    def new_user(name, dormitory, room, login, host):

        result_user = user.User()

        return result_user
