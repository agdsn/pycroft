# -*- coding: utf-8 -*-
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
    return render_template('rights/base.html')


@bp.route('/rights')
@nav.navigate(u"Rechte")
def rights():
    return render_template('rights/base.html')
