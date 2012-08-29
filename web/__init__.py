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

from flask import Flask, redirect, url_for
from blueprints import finance, infrastructure, properties, user, dormitories, login
import template_filters
import template_tests

from pycroft.model import session
from web.blueprints.login import login_manager


def make_app():
    """  Create and configure the main? Flask app object

    :return: The fully configured app object
    """
    session.init_session()

    app = Flask(__name__)

    #initialization code
    app.secret_key = \
        r"eiNohfaefaig5Iek6oshai0eijuph4ohla6Eo1vi5bahnaeh3Bah7ohy1einuaxu"

    login_manager.setup_app(app)

    app.register_blueprint(user.bp, url_prefix="/user")
    app.register_blueprint(dormitories.bp, url_prefix="/dormitories")
    app.register_blueprint(infrastructure.bp, url_prefix="/infrastructure")
    app.register_blueprint(properties.bp, url_prefix="/properties")
    app.register_blueprint(finance.bp, url_prefix="/finance")
    app.register_blueprint(login.bp)

    template_filters.register_filters(app)
    template_tests.register_tests(app)

    user.nav.register_on(app)
    finance.nav.register_on(app)
    dormitories.nav.register_on(app)
    infrastructure.nav.register_on(app)
    properties.nav.register_on(app)

    @app.route('/')
    def redirect_to_index():
        return redirect(url_for('user.overview'))

    @app.teardown_request
    def shutdown_session(exception=None):
        session.session.remove()

    return app
