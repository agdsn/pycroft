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

from flask import Blueprint, render_template, flash, redirect, url_for,\
    request, jsonify, abort
# this is necessary
from pycroft.helpers.host_helper import getFreeIP
from pycroft.model import ports
from pycroft.model.dormitory import Dormitory, Room, Subnet, VLan
from pycroft.model.hosts import Host, NetDevice
from pycroft.model.logging import UserLogEntry
from pycroft.model.session import session
from pycroft.model.user import User
from pycroft.helpers import user_helper, dormitory_helper, host_helper
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.user.forms import UserSearchForm, UserCreateForm,\
    hostCreateForm, userLogEntry
from datetime import datetime

bp = Blueprint('user', __name__, )
nav = BlueprintNavigation(bp, "Nutzer")


@bp.route('/')
@nav.navigate(u"Übersicht")
def overview():
    dormitories_list = Dormitory.q.all()
    dormitories_list = dormitory_helper.sort_dormitories(dormitories_list)
    return render_template('user/overview.html',
        dormitories=dormitories_list)


@bp.route('/show/<user_id>', methods=['GET', 'POST'])
def user_show(user_id):
    user = User.q.get(user_id)
    form = userLogEntry()
    if form.validate_on_submit():
        #TODO determine author_id from user session
        newUserLogEntry = UserLogEntry(message=form.message.data,
            timestamp=datetime.now(),
            author_id=user_id, user_id=user_id)
        session.add(newUserLogEntry)
        session.commit()
        flash('Kommentar hinzugefügt', 'success')

    user_log_list = user.user_log_entries

    return render_template('user/user_show.html',
        page_title=u"Nutzer anzeigen",
        user=user, user_logs=user_log_list, form=form)


@bp.route('/dormitory/<dormitory_id>')
def dormitory_levels(dormitory_id):
    dormitory = Dormitory.q.get(dormitory_id)
    rooms_list = session.query(Room.level.label('level')).filter_by(
        dormitory_id=dormitory_id).order_by(Room.level).distinct()
    levels_list = [room.level for room in rooms_list]

    return render_template('user/levels.html',
        levels=levels_list, dormitory_id=dormitory_id,
        page_title=u"Etagen Wohnheim " + dormitory.short_name)


@bp.route('/dormitory/<dormitory_id>/level/<level>')
def dormitory_level_rooms(dormitory_id, level):
    dormitory = Dormitory.q.get(dormitory_id)
    rooms_list = session.query(Room.number.label('number')).filter_by(
        dormitory_id=dormitory_id, level=level).order_by(Room.number)
    rooms_list = [room.number for room in rooms_list]

    if int(level) < 10:
        level_l0 = u"0"+level
    else:
        level_l0 = level

    #TODO depending on, whether a user is living in the room, the room is
    # a link to the user. If there is more then one user, the room is
    # duplicated
    return render_template('user/rooms.html', rooms=rooms_list, level=level_l0,
        page_title=u"Zimmer der Etage " + level + u" des Wohnheims " +
                   dormitory.short_name)


@bp.route('/json/levels', defaults={"dormitory_id": 0})
@bp.route('/json/levels/<int:dormitory_id>')
def json_levels(dormitory_id):
    if not request.is_xhr:
        abort(404)
    levels = session.query(Room.level.label('level')).filter_by(
        dormitory_id=dormitory_id).order_by(Room.level).distinct()
    return jsonify(dict(levels=[entry.level for entry in levels]))


@bp.route('/json/rooms', defaults={"dormitory_id": 0, "level": 0})
@bp.route('/json/rooms/<int:dormitory_id>/<int:level>')
def json_rooms(dormitory_id, level):
    if not request.is_xhr:
        abort(404)
    rooms = session.query(
        Room.number.label("room_num")).filter_by(
        dormitory_id=dormitory_id, level=level).order_by(
        Room.number).distinct()
    return jsonify(dict(rooms=[entry.room_num for entry in rooms]))


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate("Anlegen")
def create():
    form = UserCreateForm()
    if form.validate_on_submit():
        dorm = form.dormitory_id.data

        try:
            #ToDo: Ugly, but ... Someone can convert this is
            #      a proper property of Dormitory
            #ToDo: Also possibly slow and untested
            subnets = session.query(
                Subnet
            ).join(
                Subnet.vlans
            ).join(
                VLan.dormitories
            ).filter(
                Dormitory.id == dorm.id
            ).all()

            ip_address = host_helper.getFreeIP(subnets)
        except host_helper.SubnetFullException, error:
            flash('Subnetz voll', 'error')
            return render_template('user/user_create.html',
                page_title=u"Neuer Nutzer", form=form)

        hostname = host_helper.generateHostname(ip_address, form.host.data)

        room = Room.q.filter_by(number=form.room_number.data,
            level=form.level.data, dormitory_id=dorm.id).one()

        #ToDo: Which port to choose if room has more than one?
        patch_port = room.patch_ports[0]

        myUser = User(login=form.login.data,
            name=form.name.data,
            room=room,
            registration_date=datetime.now())
        session.add(myUser)

        myHost = Host(hostname=hostname,
            user=myUser,
            room=room)
        session.add(myHost)

        myNetDevice = NetDevice(ipv4=ip_address,
            mac=form.mac.data,
            host=myHost,
            patch_port=patch_port)
        session.add(myNetDevice)
        session.commit()
        flash('Benutzer angelegt', 'success')
        return redirect(url_for('.user_show', user_id=myUser.id))

    return render_template('user/user_create.html',
        page_title=u"Neuer Nutzer", form=form)


@bp.route('/search', methods=['GET', 'POST'])
@nav.navigate("Suchen")
def search():
    form = UserSearchForm()
    if form.validate_on_submit():
        userResult = User.q
        if len(form.userid.data):
            userResult = userResult.filter(User.id == form.userid.data)
        if len(form.name.data):
            userResult = userResult.filter(User.name.like('%' + form.name\
            .data + '%'))
        if len(form.login.data):
            userResult = userResult.filter(User.login == form.login.data)
        if not len(userResult.all()):
            flash('Benutzer nicht gefunden', 'error')
        return render_template('user/user_search.html',
            page_title=u"Suchergebnis",
            results=userResult.all(), form=form)
    return render_template('user/user_search.html', form=form)


@bp.route('/host_create', methods=['GET', 'POST'])
@nav.navigate("Host erstellen")
def host_create():
    form = hostCreateForm()
    hostResult = Host.q.all()
    if form.validate_on_submit():
        myHost = Host(hostname=form.name.data)
        session.add(myHost)
        session.commit()
        flash('Host angelegt', 'success')
        return render_template('user/host_create.html', form=form,
            results=hostResult)
    return render_template('user/host_create.html', form=form,
        results=hostResult)
