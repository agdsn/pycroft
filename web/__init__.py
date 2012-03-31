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
app.secret_key = str(time.time())

from blueprints import finance, infrastructure, rights, user