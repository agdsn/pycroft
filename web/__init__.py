# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web
    ~~~~~~~~~~~~~~

    This package contains the web interface based on flask

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Flask


def make_app():
    """  Create and configure the main? Flask app object

    :return: The fully configured app object
    """
    app = Flask(__name__)

    #initialization code
    app.secret_key = "eiNohfaefaig5Iek6oshai0eijuph4ohla6Eo1vi5bahnaeh3Bah7ohy1einuaxu"

    return app

from blueprints import finance, infrastructure, rights, user
