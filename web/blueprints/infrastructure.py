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

bp = Blueprint('bp_infrastructure', __name__, )


@bp.route('/infrastructure')
@bp.route('/infrastructure/rooms')
def rooms():
    return render_template('test.html', page_title = u"Räume", subnav = 'nav/infrastructure.html')


@bp.route('/infrastructure/subnets')
def subnets():
    return render_template('test.html', page_title = u"Subnetze", subnav = 'nav/infrastructure.html')


@bp.route('/infrastructure/switches')
def switches():
    return render_template('test.html', page_title = u"Switches", subnav = 'nav/infrastructure.html')


@bp.route('/infrastructure/vlans')
def vlans():
    return render_template('test.html', page_title = u"VLans", subnav = 'nav/infrastructure.html')


@bp.route('/infrastructure/dormitories')
def dormitories():
    return render_template('test.html', page_title = u"Wohnheime", subnav = 'nav/infrastructure.html')


