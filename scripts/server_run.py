#!/usr/bin/env python3
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import argparse
import logging
import os
import sys
import time
from collections.abc import Callable

from babel.support import Translations
from flask import g, request
from flask.globals import request_ctx
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.middleware.profiler import ProfilerMiddleware

import pycroft
import web
from pycroft.helpers.i18n import set_translation_lookup, get_locale
from pycroft.model.session import set_scoped_session
from scripts.connection import try_create_connection, get_connection_string
from scripts.schema import AlembicHelper, SchemaStrategist
from web import make_app, PycroftFlask

default_handler = logging.StreamHandler(sys.stdout)
default_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
)


def prepare_server(args) -> tuple[PycroftFlask, Callable]:
    """returns both the prepared app and a callback executing `app.run`"""
    if args.echo:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
    app = make_app(args.debug)

    logging.getLogger('pycroft').addHandler(default_handler)

    wait_for_db: bool = args.wait_for_database

    connection_string = get_connection_string()
    connection, engine = try_create_connection(connection_string, wait_for_db, app.logger,
                                               reflections=False)

    state = AlembicHelper(connection)
    if args.force_schema_create:
        strategy = SchemaStrategist(state).create_then_stamp
    else:
        strategy = SchemaStrategist(state).determine_schema_strategy()
    strategy()

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

    connection, engine = try_create_connection(connection_string, wait_for_db, app.logger,
                                               args.profile)

    set_scoped_session(
        scoped_session(
            sessionmaker(bind=engine),
            scopefunc=lambda: request_ctx._get_current_object(),
        )
    )

    def lookup_translation():
        ctx = request_ctx
        if ctx is None:
            return None
        translations = getattr(ctx, 'pycroft_translations', None)
        if translations is None:
            translations = Translations()
            for module in (pycroft, web):
                os.path.dirname(module.__file__)
                dirname = os.path.join(ctx.app.root_path, 'translations')
                translations.merge(Translations.load(dirname, [get_locale()]))
            ctx.pycroft_translations = translations
        return translations

    set_translation_lookup(lookup_translation)
    app.config.from_pyfile('flask.cfg')
    if args.profile:
        app.config['PROFILE'] = True
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
    return app, lambda: app.run(
        debug=args.debug,
        port=args.port,
        host=args.host,
        threaded=True,
        exclude_patterns=["**/lib/python3*"],
    )


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pycroft launcher")
    parser.add_argument("--debug", action="store_true",
                        help="run in debug mode")
    parser.add_argument("--echo", action="store_true",
                        help="log sqlalchemy actions")
    parser.add_argument("--profile", action="store_true",
                        help="profile and log sql queries")
    parser.add_argument("--exposed", action="store_const", const='0.0.0.0',
                        dest='host', help="expose server on network")
    parser.add_argument("-p", "--port", action="store",
                        help="port to run Pycroft on", type=int, default=5000)
    parser.add_argument("-w", "--wait-for-database", type=int, default=30,
                        help="Maximum time to wait for database to become "
                             "available. Use 0 to wait forever.")
    parser.add_argument("--force-schema-create", action='store_true')
    return parser


app, run_callable = prepare_server(create_parser().parse_args())

if __name__ == "__main__":
    run_callable()
