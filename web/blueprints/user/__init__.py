# -*- coding: utf-8 -*-
"""
    web.blueprints.user
    ~~~~~~~~~~~~~~

    This module defines view functions for /user

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, flash
from pycroft.model import user, session
from pycroft.model.user import User
from web.blueprints import BlueprintNavigation

bp = Blueprint('user', __name__, )
nav = BlueprintNavigation(bp, "Nutzer")


@bp.route('/')
@nav.navigate(u"Übersicht")
def overview():
    user_list = user.User.q.all()
    return render_template('user/user_list.html',
                           page_title=u"Nutzerübersicht", users=user_list)


@bp.route('/show/<user_id>')
def user_show(user_id):
    user_list = user.User.q.filter(User.id == user_id).all()
    return render_template('user/user_show.html',
                           page_title=u"Nutzer anzeigen: "+user_id,
                           user=user_list)


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
