# -*- coding: utf-8 -*-
"""
    web
    ~~~~~~~~~~~~~~

    This package contains the web interface based on flask

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Flask
import time


### Configurations
app = Flask(__name__)
#initialization code
app.secret_key = "eiNohfaefaig5Iek6oshai0eijuph4ohla6Eo1vi5bahnaeh3Bah7ohy1einuaxu"

from blueprints import finance, infrastructure, rights, user