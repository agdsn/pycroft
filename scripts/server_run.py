#!/usr/bin/env python3
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import logging
import os
import sys
import time
import tomllib

from babel.support import Translations
from flask import g, request, Flask
from flask.globals import request_ctx
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.middleware.profiler import ProfilerMiddleware

import pycroft
import web
from pycroft.helpers.i18n import set_translation_lookup, get_locale
from pycroft.lib.mail import _config_var, MailConfig
from pycroft.model.session import set_scoped_session
from scripts.connection import get_connection_string
from pycroft.model.alembic import determine_schema_state
from web import make_app, PycroftFlask

default_handler = logging.StreamHandler(sys.stdout)
default_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
)


def prepare_server(echo=False, ensure_schema=False) -> PycroftFlask:
    if echo:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
    logging.getLogger('pycroft').addHandler(default_handler)

    app = make_app()
    app.config.from_file("default_config.toml", load=tomllib.load, text=False)
    app.config.from_prefixed_env()

    engine = create_engine(get_connection_string())
    if ensure_schema:
        with engine.connect() as connection:
            _ensure_schema_up_to_date(app, connection)

    _setup_simple_profiling(app)
    set_scoped_session(
        scoped_session(
            sessionmaker(bind=engine),
            scopefunc=lambda: request_ctx._get_current_object(),
        )
    )
    _setup_translations()
    _config_var.set(MailConfig.from_env())

    if app.config.get("PROFILE", False):
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
    return app


def _ensure_schema_up_to_date(app: Flask, connection):
    state = determine_schema_state(connection)
    if not state.running_version:
        _msg = "No alembic_version found. Please import data or create the schema."
        app.logger.critical(_msg)
        exit(1)
    if state.running_version != state.desired_version:
        _msg = "Schema out of date (current: %s, needed: %s). Please upgrade."
        app.logger.critical(_msg, state.running_version, state.desired_version)
        exit(1)


def _setup_translations():
    def lookup_translation():
        ctx = request_ctx
        if ctx is None:
            return None
        translations = getattr(ctx, "pycroft_translations", None)
        if translations is None:
            translations = Translations()
            for module in (pycroft, web):
                # TODO this has a bug. The intention is to merge
                # `pycroft.translations` and `web.translations`,
                # but the `os.path.dirname(…)` result is nowhere used.
                os.path.dirname(module.__file__)
                dirname = os.path.join(ctx.app.root_path, "translations")
                translations.merge(Translations.load(dirname, [get_locale()]))
            ctx.pycroft_translations = translations
        return translations

    set_translation_lookup(lookup_translation)


def _setup_simple_profiling(app):
    @app.before_request
    def get_time():
        g.request_time = time.time()

    @app.teardown_request
    def time_response(exception=None):
        request_time = g.pop('request_time', None)

        if request_time:
            time_taken = time.time() - request_time
            if time_taken > 0.5:
                app.logger.warning(
                    "Response took %s seconds for request %s",
                    time_taken, request.full_path,
                )
