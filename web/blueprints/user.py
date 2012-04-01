# -*- coding: utf-8 -*-
"""
    web.blueprints.user
    ~~~~~~~~~~~~~~

    This module defines view functions for /user

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, flash

bp = Blueprint('user', __name__, )


@bp.route('/')
def overview():
    return render_template('user/user_base.html', page_title = u"Übersicht")


@bp.route('/new')
def create():
    flash("Test1", "info")
    flash("Test2", "warning")
    flash("Test3", "error")
    flash("Test4", "success")
    return render_template('user/user_base.html', page_title = u"Neuer Nutzer")


@bp.route('/search')
def search():
    return render_template('user/user_base.html', page_title = u"Nutzer Suchen")


