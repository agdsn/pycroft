# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web
    ~~~~~~~~~~~~~~

    This package contains the web interface based on flask

    :copyright: (c) 2012 by AG DSN.
"""
from flask import Flask, redirect, url_for, request, flash, render_template
from flask.ext.login import current_user, current_app
from flask.ext.babel import Babel
from pycroft.helpers.i18n import gettext
from pycroft.model import session
from . import template_filters
from . import template_tests
from .blueprints import (
    finance, infrastructure, properties, user, facilities, login)
from .blueprints.login import login_manager
from .form import widgets
from .templates import page_resources


def make_app():
    """  Create and configure the main? Flask app object

    :return: The fully configured app object
    """
    app = Flask(__name__)

    #initialization code
    login_manager.init_app(app)
    app.register_blueprint(user.bp, url_prefix="/user")
    app.register_blueprint(facilities.bp, url_prefix="/facilities")
    app.register_blueprint(infrastructure.bp, url_prefix="/infrastructure")
    app.register_blueprint(properties.bp, url_prefix="/properties")
    app.register_blueprint(finance.bp, url_prefix="/finance")
    app.register_blueprint(login.bp)

    template_filters.register_filters(app)
    template_tests.register_checks(app)

    babel = Babel(app)

    page_resources.init_app(app)

    user.nav.register_on(app)
    finance.nav.register_on(app)
    facilities.nav.register_on(app)
    infrastructure.nav.register_on(app)
    properties.nav.register_on(app)

    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(500)
    def errorpage(e):
        """Handle errors according to their error code

        :param e: The error from the errorhandler
        """
        if not hasattr(e, 'code'):
            code = 500
        else:
            code = e.code
        if code == 500:
            message = e.message
        elif code == 403:
            message = gettext(u"You are not allowed to access this page.")
        elif code == 404:
            message = gettext(u"Page not found.")
        else:
            raise AssertionError()
        return render_template('error.html', error=message), code

    @app.route('/')
    def redirect_to_index():
        return redirect(url_for('user.overview'))

    @app.teardown_request
    def shutdown_session(exception=None):
        session.Session.remove()

    @app.before_request
    def require_login():
        """Request a login for every page
        except the login blueprint and the static folder.

        Blueprint "None" is needed for "/static/*" GET requests.
        """
        if current_user.is_anonymous and request.blueprint not in ("login", None):
            return current_app.login_manager.unauthorized()

    return app
