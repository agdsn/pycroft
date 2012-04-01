# -*- coding: utf-8 -*-
"""
    web
    ~~~~~~~~~~~~~~

    This package contains the web interface based on flask

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Flask
from blueprints import finance, infrastructure, rights, user

from pycroft.model.session import session


def make_app():
    """  Create and configure the main? Flask app object

    :return: The fully configured app object
    """
    app = Flask(__name__)

    #initialization code
    app.secret_key = r"eiNohfaefaig5Iek6oshai0eijuph4ohla6Eo1vi5bahnaeh3Bah7ohy1einuaxu"

    app.register_blueprint(user.bp, url_prefix="/user")
    app.register_blueprint(infrastructure.bp, url_prefix="/infrastructure")
    app.register_blueprint(rights.bp, url_prefix="/rights")
    app.register_blueprint(finance.bp, url_prefix="/finance")

    @app.teardown_request
    def shutdown_session(exception=None):
        session.remove()

    return app

