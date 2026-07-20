# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.login
    ~~~~~~~~~~~~~~

    This module defines view functions to log in and out

    :copyright: (c) 2012 by AG DSN.
"""

import typing as t

from authlib.integrations.base_client import OAuthError
from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc6749 import OAuth2Token
from flask import Blueprint, render_template, flash, redirect, url_for, request, g, current_app
from flask.typing import ResponseValue
from flask_login import (
    AnonymousUserMixin, LoginManager, current_user, login_required, login_user,
    logout_user)

from pycroft.model.session import session
from pycroft.model.user import User

bp = Blueprint('login', __name__, )


class AnonymousUser(AnonymousUserMixin):
    #: See `pycroft.model.user.BaseUser.current_properties_set`
    current_properties_set: t.Container[str] = frozenset()


oauth = OAuth()

login_manager = LoginManager()
login_manager.anonymous_user = AnonymousUser
login_manager.login_view = "login.login"
login_manager.login_message = "Bitte melden Sie sich an, um diese Seite zu benutzen!"


@login_manager.user_loader
def load_user(userid: int) -> User | None:
    return session.get(User, userid)


@bp.route("/login", methods=("GET", "POST"))
def login() -> ResponseValue:
    if current_user is not None and current_user.is_authenticated:
        flash(f'Sie sind bereits als "{current_user.name}" angemeldet!', "warning")
        return redirect(url_for('user.overview'))
    if not current_app.config["OIDC_ENABLED"]:
        profile = current_app.config["OIDC_TESTING_PROFILE"]
    else:
        try:
            token: OAuth2Token = oauth.oidc.authorize_access_token()
        except OAuthError:
            return render_template("login/login.html")
        profile = oauth.oidc.userinfo(token=token)
    username = profile.get("pycroft_login", profile.get("preferred_username", None))
    groups = profile.get("groups", [])
    user = User.get(username, session)
    required_group = current_app.config["OIDC_REQUIRED_GROUP"]
    if (
        profile is not None
        and username is not None
        and user is not None
        and (required_group is None or required_group in groups)
    ):
        login_user(user)
        flash("Erfolgreich angemeldet.", "success")
        return redirect(request.args.get("next") or url_for("user.overview"))
    flash("Anmeldung fehlgeschlagen.", "error")
    return redirect(url_for("login.login"))


@bp.route("/openid-connect")
def openid_connect() -> ResponseValue:
    redirect_uri = current_app.config["OIDC_REDIRECT_URI"]
    if not redirect_uri:
        redirect_uri = url_for("login.login", _external=True)
    return t.cast(ResponseValue, oauth.oidc.authorize_redirect(redirect_uri))


@bp.route("/logout")
@login_required
def logout() -> ResponseValue:
    logout_user()
    flash("Sie sind jetzt abgemeldet!", "info")
    return redirect(url_for(".login"))
