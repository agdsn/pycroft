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
import os

from flask import _request_ctx_stack
from sqlalchemy.orm import scoped_session, sessionmaker

from pycroft.model import create_engine
from pycroft.model.session import set_scoped_session
from pycroft.model._all import *
from pycroft import config


connection_string = os.environ['PYCROFT_DB_URI']

engine = create_engine(connection_string, echo=True)
#DeferredReflection.prepare(engine)


def setup():
    # TODO: don't set a scoped session, just a regular one
    set_scoped_session(scoped_session(sessionmaker(bind=engine),
                                      scopefunc=lambda: _request_ctx_stack.top))


setup()
