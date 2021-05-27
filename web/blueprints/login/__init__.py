# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.login
    ~~~~~~~~~~~~~~

    This module defines view functions to log in and out

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import (
    AnonymousUserMixin, LoginManager, current_user, login_required, login_user,
    logout_user)

from pycroft.model.user import User
from web.blueprints.login.forms import LoginForm

bp = Blueprint('login', __name__, )


class AnonymousUser(AnonymousUserMixin):
    #: See `pycroft.model.user.BaseUser.current_properties_set`
    current_properties_set = frozenset()


login_manager = LoginManager()
login_manager.anonymous_user = AnonymousUser
login_manager.login_view = "login.login"
login_manager.login_message = u"Bitte melden Sie sich an, um diese Seite zu benutzen!"


@login_manager.user_loader
def load_user(userid):
    return User.get(userid)


@bp.route("/login", methods=("GET", "POST"))
def login():
    if current_user is not None and current_user.is_authenticated:
        flash(u'Sie sind bereits als "{}" angemeldet!'.format(current_user.name), "warning")
        return redirect(url_for('user.overview'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.verify_and_get(form.login.data, form.password.data)
        if user is not None:
            login_user(user)
            flash(u"Erfolgreich angemeldet.", "success")
            return redirect(request.args.get("next") or url_for("user.overview"))
        flash(u"Benutzername und/oder Passwort falsch", "error")
    return render_template("login/login.html", form=form, next=request.args.get("next"))


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash(u"Sie sind jetzt abgemeldet!", "info")
    return redirect(url_for(".login"))
