# -*- coding: utf-8 -*-
"""
    web.blueprints.infrastructure
    ~~~~~~~~~~~~~~

    This module defines view functions for /infrastructure

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template

bp = Blueprint('infrastructure', __name__, )


@bp.route('/')
@bp.route('/rooms')
def rooms():
    return render_template('test.html', page_title = u"Räume", subnav = 'nav/infrastructure.html')


@bp.route('/subnets')
def subnets():
    return render_template('test.html', page_title = u"Subnetze", subnav = 'nav/infrastructure.html')


@bp.route('/switches')
def switches():
    return render_template('test.html', page_title = u"Switches", subnav = 'nav/infrastructure.html')


@bp.route('/vlans')
def vlans():
    return render_template('test.html', page_title = u"VLans", subnav = 'nav/infrastructure.html')


@bp.route('/dormitories')
def dormitories():
    return render_template('test.html', page_title = u"Wohnheime", subnav = 'nav/infrastructure.html')


