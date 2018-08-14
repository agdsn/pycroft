#!/usr/bin/env python3
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import os

from flask import _request_ctx_stack, g, request
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from pycroft.model import session
from pycroft.model.session import set_scoped_session
from scripts.schema import AlembicHelper, SchemaStrategist
from pycroft.lib import traffic


def main():
    try:
        connection_string = os.environ['PYCROFT_DB_URI']
    except KeyError:
        raise RuntimeError("Environment variable PYCROFT_DB_URI must be "
                           "set to an SQLAlchemy connection string.")

    engine = create_engine(connection_string)
    connection = engine.connect()
    state = AlembicHelper(connection)
    if not SchemaStrategist(state).is_up_to_date:
        print("Schema is not up to date!")
        return

    set_scoped_session(scoped_session(sessionmaker(bind=engine),
                                      scopefunc=lambda: _request_ctx_stack.top))

    print("Starting synchronization of exceeded traffic limits.")
    traffic.sync_exceeded_traffic_limits()
    session.session.commit()
    print("Finished synchronization.")


if __name__ == "__main__":
    main()
