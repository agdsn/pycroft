# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.user
    ~~~~~~~~~~~~~~

    This module defines view functions for /user

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, flash, redirect, url_for
from pycroft.model import user, session
from pycroft.model.user import User
from web.blueprints import BlueprintNavigation
from web.blueprints.user.forms import UserCreateForm

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
        page_title=u"Nutzer anzeigen: " + user_id,
        user=user_list)


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate("Anlegen")
def create():
    form = UserCreateForm()
    if form.validate_on_submit():
        myUser = user.User(login=form.login.data,
            name=form.name.data, registration_date=form.registration_date.data,
            room_id=form.room_id.data)
        session.session.add(myUser)
        session.session.commit()
        flash('Benutzer angelegt', 'success')
        return redirect(url_for('.overview'))
    return render_template('user/user_create.html',
        page_title=u"Neuer Nutzer", form=form)


@bp.route('/search')
@nav.navigate("Suchen")
def search():
    return render_template('user/base.html', page_title=u"Nutzer Suchen")
