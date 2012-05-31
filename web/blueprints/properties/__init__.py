# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.properties
    ~~~~~~~~~~~~~~

    This module defines view functions for /properties

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template
from web.blueprints.navigation import BlueprintNavigation

bp = Blueprint('properties', __name__, )
nav = BlueprintNavigation(bp, "Eigenschaften")


@bp.route('/groups')
@nav.navigate(u"Gruppen")
def groups():
    return render_template('properties/base.html')


@bp.route('/properties')
@nav.navigate(u"Eigenschaften")
def rights():
    return render_template('properties/base.html')
