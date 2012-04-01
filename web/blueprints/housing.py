# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.infrastructure
    ~~~~~~~~~~~~~~

    This module defines view functions for /infrastructure

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template

bp = Blueprint('housing', __name__, )


@bp.route('/')
@bp.route('/rooms')
def rooms():
    return render_template('housing/housing_base.html', page_title = u"Räume")


@bp.route('/dormitories')
def dormitories():
    return render_template('housing/housing_base.html', page_title = u"Wohnheime")

