# -*- coding: utf-8 -*-
"""
    web
    ~~~~~~~~~~~~~~

    This package contains the web interface based on flask

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Flask, redirect, url_for
from blueprints import finance, infrastructure, rights, user, housing
import template_filters

from pycroft.model.session import session


def make_app():
    """  Create and configure the main? Flask app object

    :return: The fully configured app object
    """
    app = Flask(__name__)

    #initialization code
    app.secret_key = r"eiNohfaefaig5Iek6oshai0eijuph4ohla6Eo1vi5bahnaeh3Bah7ohy1einuaxu"

    app.register_blueprint(user.bp, url_prefix="/user")
    app.register_blueprint(housing.bp, url_prefix="/housing")
    app.register_blueprint(infrastructure.bp, url_prefix="/infrastructure")
    app.register_blueprint(rights.bp, url_prefix="/rights")
    app.register_blueprint(finance.bp, url_prefix="/finance")

    template_filters.register_filters(app)

    @app.route('/')
    def redirect_to_index():
        return redirect(url_for('user.overview'))

    @app.teardown_request
    def shutdown_session(exception=None):
        session.remove()

    return app

