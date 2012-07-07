# -*- coding: utf-8 -*-
"""
pycroft.model._all
~~~~~~~~~~~~~~

Dummy module to get all the mapped stuff in one namespace.
This is necessary for things like sqlalchemy-schemadisplay.

:copyright: (c) 2011 by AG DSN.
"""

from pycroft.model.base import *
from pycroft.model.dormitory import *
from pycroft.model.hosts import *
from pycroft.model.logging import *
from pycroft.model.session import *
# ToDo Fix the finance mapping stuff
#from pycroft.model.finance import *
from pycroft.model.user import *
from pycroft.model.properties import *
from pycroft.model.accounting import *
from pycroft.model.ports import *

