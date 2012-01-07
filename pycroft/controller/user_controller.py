# -*- coding: utf-8 -*-
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
