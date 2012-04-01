# -*- coding: utf-8 -*-
"""
    web.blueprints.rights
    ~~~~~~~~~~~~~~

    This module defines view functions for /rights

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template

bp = Blueprint('rights', __name__, )


@bp.route('/groups')
def groups():
    return render_template('rights/rights_base.html', page_title = u"Gruppen")


@bp.route('/rights')
def rights():
    return render_template('rights/rights_base.html', page_title = u"Rechte")


