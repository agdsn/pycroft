# -*- coding: utf-8 -*-
"""
    web.blueprints.user
    ~~~~~~~~~~~~~~

    This module defines view functions for /user

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template

bp = Blueprint('bp_user', __name__, )


@bp.route('/')
@bp.route('/user')
def overview():
    return render_template('test.html', page_title = u"Übersicht", subnav = 'nav/user.html')


@bp.route('/user/new')
def new():
    return render_template('test.html', page_title = u"Neuer Nutzer", subnav = 'nav/user.html')


@bp.route('/user/search')
def search():
    return render_template('test.html', page_title = u"Nutzer Suchen", subnav = 'nav/user.html')


