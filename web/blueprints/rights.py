# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.rights
    ~~~~~~~~~~~~~~

    This module defines view functions for /rights

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template
from web.blueprints import BlueprintNavigation

bp = Blueprint('rights', __name__, )
nav = BlueprintNavigation(bp, "Rechte")


@bp.route('/groups')
@nav.navigate(u"Gruppen")
def groups():
    return render_template('rights/base.html', page_title=u"Gruppen")


@bp.route('/rights')
@nav.navigate(u"Rechte")
def rights():
    return render_template('rights/base.html', page_title=u"Rechte")
