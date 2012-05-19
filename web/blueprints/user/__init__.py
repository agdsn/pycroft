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
from pycroft.model import user, hosts, ports, dormitory, logging
from pycroft.model.session import session
from pycroft.model.user import User
from pycroft.helpers import user_helper, dormitory_helper
from web.blueprints import BlueprintNavigation
from web.blueprints.user.forms import UserSearchForm, UserCreateForm,\
    hostCreateForm, userLogEntry
import datetime

bp = Blueprint('user', __name__, )
nav = BlueprintNavigation(bp, "Nutzer")


@bp.route('/')
@nav.navigate(u"Übersicht")
def overview():
    dormitories_list = dormitory.Dormitory.q.all()
    dormitories_list = dormitory_helper.sort_dormitories(dormitories_list)
    return render_template('user/overview.html',
        dormitories=dormitories_list)


@bp.route('/show/<user_id>', methods=['GET', 'POST'])
def user_show(user_id):
    user = User.q.get(user_id)
    countLogEntries = logging.LogEntry.q.count()
    user_log_list = user.user_log_entries
    form = userLogEntry()
    if form.validate_on_submit():
        newUserLogEntry = logging.UserLogEntry(message=form.message.data,
            timestamp=datetime.datetime.now(),
            author_id=3, user_id=user_id)
        session.add(newUserLogEntry)
        session.commit()
        flash('Kommentar hinzugefügt', 'success')
        user_log_list = user.user_log_entries
        return render_template('user/user_show.html',
            page_title=u"Nutzer anzeigen neu",
            user=user, user_logs=user_log_list,
            form=form)

    return render_template('user/user_show.html',
        page_title=u"Nutzer anzeigen",
        user=user, user_logs=user_log_list, form=form, count=countLogEntries)


@bp.route('/dormitory/<dormitory_id>')
def dormitory_floors(dormitory_id):
    floors_list = []
    for floor in session.query(dormitory.Room.level).filter_by(
        dormitory_id=dormitory_id).distinct().order_by(
        dormitory.Room.level).all():
        floors_list.append(floor.level)
    return render_template('user/floors.html',
        floors=floors_list, dormitory_id=dormitory_id,
        page_title=u"Etagen Wohnheim " + session.query(
            dormitory.Dormitory).filter_by(id=dormitory_id).first().short_name)


@bp.route('/dormitory/<dormitory_id>/level/<level>')
def dormitory_level_rooms(dormitory_id, level):
    rooms_list = []
    for room in session.query(dormitory.Room.number).filter_by(
        dormitory_id=dormitory_id, level=level).order_by(
        dormitory.Room.number).all():
        rooms_list.append(room.number)
    return render_template('user/rooms.html',
        rooms=rooms_list,
        page_title=u"Zimmer der Etage " + level + u" des Wohnheim " + session.query(
            dormitory.Dormitory).filter_by(id=dormitory_id).first().short_name)


@bp.route('/json/levels', defaults={"dormitory_id": 0})
@bp.route('/json/levels/<int:dormitory_id>')
def json_levels(dormitory_id):
    if not request.is_xhr:
        abort(404)
    levels = session.query(
        dormitory.Room.level.label('level')).filter_by(
        dormitory_id=dormitory_id).order_by(dormitory.Room.level).distinct()
    return jsonify(dict(levels=[entry.level for entry in levels]))


@bp.route('/json/rooms', defaults={"dormitory_id": 0, "level": 0})
@bp.route('/json/rooms/<int:dormitory_id>/<int:level>')
def json_rooms(dormitory_id, level):
    if not request.is_xhr:
        abort(404)
    rooms = session.query(
        dormitory.Room.number.label("room_num")).filter_by(
        dormitory_id=dormitory_id, level=level).order_by(
        dormitory.Room.number).distinct()
    return jsonify(dict(rooms=[entry.room_num for entry in rooms]))


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate("Anlegen")
def create():
    form = UserCreateForm()
    if form.validate_on_submit():
        dorm = form.dormitory_id.data

        try:
            #ToDo: Ugly, but ... Someone can convert this is a proper property of Dormitory
            #ToDo: Also possibly slow and untested
            subnets = session.query(
                dormitory.Subnet
            ).join(
                dormitory.Subnet.vlans
            ).join(
                dormitory.VLan.dormitories
            ).filter(
                dormitory.Dormitory.id == dorm.id
            ).all()

            ip_address = user_helper.getFreeIP(subnets)
        except user_helper.SubnetFullException, error:
            flash('Subnetz voll', 'error')
            return render_template('user/user_create.html',
                page_title=u"Neuer Nutzer", form=form)

        hostname = user_helper.generateHostname(ip_address, form.host.data)

        room = dormitory.Room.q.filter_by(number=form.room_number.data,
            level=form.level.data,
            dormitory_id=dorm.id).one()

        #ToDo: Which port to choose if room has more than one?
        patch_port = room.patch_ports[0]

        myUser = user.User(login=form.login.data,
            name=form.name.data,
            room=room,
            registration_date=datetime.datetime.now())
        session.add(myUser)

        myHost = hosts.Host(hostname=hostname,
            user=myUser,
            room=room)
        session.add(myHost)

        myNetDevice = hosts.NetDevice(ipv4=ip_address,
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
    hostResult = hosts.Host.q
    if form.validate_on_submit():
        myHost = hosts.Host(hostname=form.name.data)
        session.add(myHost)
        session.commit()
        flash('Host angelegt', 'success')
        return render_template('user/host_create.html', form=form,
            results=hostResult.all())
    return render_template('user/host_create.html', form=form,
        results=hostResult.all())
