# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web
    ~~~~~~~~~~~~~~

    This package contains the web interface based on flask

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Flask, Blueprint, render_template, abort
from jinja2 import TemplateNotFound
import time


### Configurations
app = Flask(__name__)
userman = Blueprint('userman', __name__)
#initialization code
app.secret_key = str(time.time())
app.debug = True

@userman.route('/', defaults={'page': 'user'})
@userman.route('/<page>')
def show(page):
    try:
        return render_template('%s.html' % page)
    except TemplateNotFound:
        raise
        #abort(404)


app.register_blueprint(userman)
#http://127.0.0.1:5000/
app.run()
