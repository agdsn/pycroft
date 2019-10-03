import os

from itertools import chain, repeat

import time

from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError

from pycroft.model import create_engine


def try_create_connection(connection_string, wait_for_db, logger) -> Connection:
    engine = create_engine(connection_string)
    if wait_for_db == 0:
        max_wait = float('inf')
    else:
        max_wait = time.clock_gettime(time.CLOCK_MONOTONIC) + wait_for_db
    for timeout in chain([1, 2, 5, 10, 30], repeat(60)):
        try:
            return engine.connect()
        except OperationalError:
            # Important: Use %r to print the URL, passwords are hidden by the
            # __repr__ of sqlalchemy.engine.URL
            logger.warn("Could not connect to database %r", engine.url)
            timeout = min(timeout,
                          max_wait - time.clock_gettime(time.CLOCK_MONOTONIC))
            if timeout > 0:
                logger.info("Waiting for %d seconds", timeout)
                time.sleep(timeout)
            else:
                raise


def get_connection_string():
    try:
        connection_string = os.environ['PYCROFT_DB_URI']
    except KeyError:
        raise RuntimeError("Environment variable PYCROFT_DB_URI must be "
                           "set to an SQLAlchemy connection string.")
    return connection_string
