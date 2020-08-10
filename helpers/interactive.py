#!/usr/bin/env python3
"""
Usage
~~~~~

This python module can be used to quickly initialize an interactive python
session like this:

```python
from helpers.interactive import *
```

This automatically imports all ORM classes plus the `config` object,
and initializes the session.

"""
import logging
import os

from flask import _request_ctx_stack
from sqlalchemy.orm import scoped_session, sessionmaker

from pycroft.model.session import set_scoped_session
from scripts.connection import try_create_connection, get_connection_string

connection_string = get_connection_string()

conn, engine = try_create_connection(connection_string,
                                     5,
                                     logger=logging.getLogger("interactive"),
                                     echo=True)


def setup():
    # TODO: don't set a scoped session, just a regular one
    set_scoped_session(scoped_session(sessionmaker(bind=engine),
                                      scopefunc=lambda: _request_ctx_stack.top))


setup()
