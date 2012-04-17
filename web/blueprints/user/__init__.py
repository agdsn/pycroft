# -*- coding: utf-8 -*-
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
from web.blueprints.user.forms import UserSearchForm, UserCreateForm

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


@bp.route('/search', methods=['GET', 'POST'])
@nav.navigate("Suchen")
def search():
    form = UserSearchForm()
    if form.validate_on_submit():
        # Check: with_entities
        #userResult = user.User.q.with_entities()
        userResult_id = user.User.q.filter(User.id.like(form.userid.data))\
        .all()
        userResult_name = user.User.q.filter(User.name.like('%' + form.name\
        .data + '%')).all()
        userResult_login = user.User.q.filter(User.login.like(form.login
        .data)).all()
        return render_template('user/user_search.html',
                               page_title=u"Nutzer Suchergebnis",
                               result_id=userResult_id,
                               result_name=userResult_name,
                               result_login=userResult_login,
                               form=form)
    return render_template('user/user_search.html',
                           page_title=u"Nutzer Suchen", form=form)
