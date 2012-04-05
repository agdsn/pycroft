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
from web.blueprints import BlueprintNavigation

bp = Blueprint('infrastructure', __name__, )
nav = BlueprintNavigation(bp, "Infrastruktur")


@bp.route('/subnets')
@nav.navigate(u"Subnetze")
def subnets():
    return render_template('infrastructure/infrastructure_base.html', page_title = u"Subnetze")


@bp.route('/switches')
@nav.navigate(u"Switche")
def switches():
    return render_template('infrastructure/infrastructure_base.html', page_title = u"Switches")


@bp.route('/vlans')
@nav.navigate(u"Vlans")
def vlans():
    return render_template('infrastructure/infrastructure_base.html', page_title = u"VLans")



