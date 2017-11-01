# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web
    ~~~~~~~~~~~~~~

    This package contains the web interface based on flask

    :copyright: (c) 2012 by AG DSN.
"""
from flask import Flask, redirect, url_for, request, flash, render_template, current_app
from flask_login import current_user
from flask_babel import Babel
from jinja2 import StrictUndefined
from werkzeug.datastructures import ImmutableDict
from pycroft.helpers.i18n import gettext
from pycroft.model import session
from .app import make_app, PycroftFlask
from .blueprints import (
    finance, infrastructure, properties, user, facilities, login)
from .blueprints.login import login_manager
from .form import widgets
