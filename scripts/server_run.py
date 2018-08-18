#!/usr/bin/env python3
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import argparse
import os
import time

from itertools import chain, repeat

from babel.support import Translations
from flask import _request_ctx_stack, g, request
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.contrib.profiler import ProfilerMiddleware

import pycroft
from pycroft.helpers.i18n import set_translation_lookup, get_locale
from pycroft.model import create_engine
from pycroft.model.session import set_scoped_session
import web
from scripts.schema import AlembicHelper, SchemaStrategist
from web import make_app


def server_run(args):
    app = make_app(args.debug)

    try:
        connection_string = os.environ['PYCROFT_DB_URI']
    except KeyError:
        raise RuntimeError("Environment variable PYCROFT_DB_URI must be "
                           "set to an SQLAlchemy connection string.")

    engine = create_engine(connection_string)
    if args.wait_for_database == 0:
        max_wait = float('inf')
    else:
        max_wait = time.clock_gettime(time.CLOCK_MONOTONIC) + args.wait_for_database
    for timeout in chain([1, 2, 5, 10, 30], repeat(60)):
        try:
            connection = engine.connect()
            break
        except OperationalError:
            # Important: Use %r to print the URL, passwords are hidden by the
            # __repr__ of sqlalchemy.engine.URL
            app.logger.warn("Could not connect to database %r", engine.url)
            timeout = min(timeout,
                          max_wait - time.clock_gettime(time.CLOCK_MONOTONIC))
            if timeout > 0:
                app.logger.info("Waiting for %d seconds", timeout)
                time.sleep(timeout)
            else:
                raise
    state = AlembicHelper(connection)
    strategy = SchemaStrategist(state).determine_schema_strategy()
    strategy()

    print("If you're running in a docker setup, the port may differ"
          " from what is given below."
          " It is probably http://0.0.0.0:5001")

    @app.before_request
    def get_time():
        g.request_time = time.time()

    @app.teardown_request
    def time_response(exception=None):
        time_taken = time.time() - g.request_time
        if time_taken > 0.5:
            app.logger.warn(
                "Response took {duration} seconds for request {path}".format(
                    path=request.full_path, duration=time_taken))

    engine = create_engine(connection_string, echo=args.profile)
    set_scoped_session(scoped_session(sessionmaker(bind=engine),
                                      scopefunc=lambda: _request_ctx_stack.top))

    def lookup_translation():
        ctx = _request_ctx_stack.top
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
    app.run(debug=args.debug, port=args.port, host=args.host, threaded=True)


def main():
    parser = argparse.ArgumentParser(description="Pycroft launcher")
    parser.add_argument("--debug", action="store_true",
                        help="run in debug mode")
    parser.add_argument("--profile", action="store_true",
                        help="profile and log sql queries")
    parser.add_argument("--exposed", action="store_const", const='0.0.0.0',
                        dest='host', help="expose server on network")
    parser.add_argument("-p", "--port", action="store",
                        help="port to run Pycroft on", type=int, default=5000)
    parser.add_argument("-w", "--wait-for-database", type=int, default=30,
                        help="Maximum time to wait for database to become "
                             "available. Use 0 to wait forever.")

    server_run(parser.parse_args())


if __name__ == "__main__":
    main()
