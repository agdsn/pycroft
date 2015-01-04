#!/usr/bin/env python2
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import argparse
import os

from flask import _request_ctx_stack
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from pycroft.model.session import set_scoped_session


def server_run(args):
    from web import make_app

    app = make_app()
    try:
        connection_string = os.environ['PYCROFT_DB_URI']
    except KeyError:
        raise RuntimeError("Environment variable PYCROFT_DB_URI must be "
                           "set to an SQLAlchemy connection string.")
    engine = create_engine(connection_string, echo=False)
    set_scoped_session(scoped_session(sessionmaker(bind=engine),
                               scopefunc=lambda: _request_ctx_stack.top))
    app.config.from_pyfile('flask.cfg')
    app.debug = args.debug

    app.run(debug=args.debug, port=args.port,
            host="0.0.0.0" if args.exposed else None)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pycroft launcher")
    parser.add_argument("--debug", action="store_true",
                        help="run in debug mode")
    parser.add_argument("--exposed", action="store_true",
                        help="expose server on network")
    parser.add_argument("-p","--port", action="store",
                        help="port to run Pycroft on", type=int, default=5000)

    server_run(parser.parse_args())
