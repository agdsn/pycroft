# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model._all
~~~~~~~~~~~~~~~~~~

Dummy module to get all the mapped stuff in one namespace.
This is necessary for things like sqlalchemy-schemadisplay.

:copyright: (c) 2011 by AG DSN.
"""

from .address import *
from .config import *
from .facilities import *
from .finance import *
from .host import *
from .logging import *
from .net import *
from .port import *
from .property import *
from .swdd import *
from .task import *
from .traffic import *
from .user import *
from .webstorage import *
from .nat import *

# hades is special: it calls `configure_mappers()` at import time.
# Therefore, importing it should happen as late as possible.
# Better would be not to do the query building at import time,
# but rather on-demand.
from .hades import *
