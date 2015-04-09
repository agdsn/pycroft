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
from flask import Flask, redirect, url_for, request, flash
from flask.ext.babel import Babel
from .blueprints import (finance, infrastructure, properties, user, facilities,
                        login)
from web.form import widgets
from . import template_filters
from . import template_tests

from pycroft.model import session
from web.blueprints.login import login_manager
from flask.ext.login import current_user, current_app
from web.templates import page_resources


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

    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(500)
    def errorpage(e):
        """Handle errors according to their error code

        :param e: The error from the errorhandler
        """
        if e.code in (401, 403):
            flash(u"Nicht genügend Rechte um die Seite zu sehen!", "error")
        elif e.code in (404,):
            flash(u"Seite wurde nicht gefunden!", "error")
        elif e.code in (500,):
            flash(e, "error")
        else:
            flash(u"Fehler!", "error")

        if request.referrer:
            return redirect(request.referrer)
        return redirect("/")

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
        if current_user.is_anonymous() and request.blueprint not in ("login", None):
            return current_app.login_manager.unauthorized()

    return app
