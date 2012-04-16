# -*- coding: utf-8 -*-
"""
    web.blueprints.user
    ~~~~~~~~~~~~~~

    This module defines view functions for /user

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, flash
from web.blueprints import BlueprintNavigation

bp = Blueprint('user', __name__, )
nav = BlueprintNavigation(bp, "Nutzer")


@bp.route('/')
@nav.navigate(u"Übersicht")
def overview():
    return render_template('user/base.html', page_title=u"Übersicht")


@bp.route('/create')
@nav.navigate("Anlegen")
def create():
    flash("Test1", "info")
    flash("Test2", "warning")
    flash("Test3", "error")
    flash("Test4", "success")
    return render_template('user/base.html', page_title=u"Neuer Nutzer")


@bp.route('/search')
@nav.navigate("Suchen")
def search():
    return render_template('user/base.html', page_title=u"Nutzer Suchen")
