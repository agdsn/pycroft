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
from pycroft.model import user, session, hosts, ports, dormitory
from pycroft.model.user import User
from pycroft.helpers.user_helper import UserHelper as helpers
from web.blueprints import BlueprintNavigation
from web.blueprints.user.forms import UserSearchForm, UserCreateForm, hostCreateForm
import datetime

bp = Blueprint('user', __name__, )
nav = BlueprintNavigation(bp, "Nutzer")


def sort_key(dormitory):
    key = 0
    power = 1
    for char in reversed(dormitory.number.lower()):
        key += ord(char) * pow(10, power)
        power += power

    return key


@bp.route('/')
@nav.navigate(u"Übersicht")
def overview():
    dormitories_list = dormitory.Dormitory.q.all()
    dormitories_list = sorted(dormitories_list,
        key=lambda dormitory: sort_key(dormitory))

    return render_template('user/overview.html',
        dormitories=dormitories_list)


@bp.route('/show/<user_id>')
def user_show(user_id):
    user_list = user.User.q.filter(User.id == user_id).all()
    return render_template('user/user_show.html',
        page_title=u"Nutzer anzeigen",
        user=user_list)


@bp.route('/dormitory/<dormitory_id>')
def dormitory_floors(dormitory_id):
    floors_list = []
    for floor in session.session.query(dormitory.Room.level).filter_by(
        dormitory_id=dormitory_id).distinct().all():
        floors_list.append(floor.level)
    return render_template('user/floors.html',
        floors=floors_list, page_title=u"Etagen Wohnheim XY")


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate("Anlegen")
def create():
    form = UserCreateForm()
    if form.validate_on_submit():
        dormitory_id = form.dormitory_id.data.id

        try:
            subnets = session.session.query(dormitory.Subnet.address).filter_by(
                id=dormitory_id).join(
                (dormitory.VLan, dormitory.Dormitory.vlans)).join(
                (dormitory.Subnet, dormitory.VLan.subnets)).distinct().all()
            subnet_list = []
            for subnet in subnets:
                subnet_list.append(subnet.address)
            ip_address = helpers.getFreeIP(subnet_list)
        except helpers.SubnetFullException, error:
            flash('Subnetz voll', 'error')
            return render_template('user/user_create.html',
                page_title=u"Neuer Nutzer", form=form)

        hostname = helpers.generateHostname(ip_address, form.host.data)
        
        level = int(form.room_number.data[:2])
        number = form.room_number.data[-2:]
        room_id = session.session.query(dormitory.Room).filter_by(number=number,
            level=level,dormitory_id=dormitory_id).first().id

        patchport_id = session.session.query(ports.PatchPort).filter_by(
            room_id=room_id).first().id

        myUser = user.User(login=form.login.data,
            name=form.name.data, room_id=room_id,
            registration_date=datetime.datetime.now())
        session.session.add(myUser)
        session.session.commit()

        myHost = hosts.Host(hostname=hostname, user_id=myUser.id,
            room_id=room_id)
        session.session.add(myHost)
        session.session.commit()

        myNetDevice = hosts.NetDevice(ipv4=ip_address, mac=form.mac.data,
            host_id=myHost.id, patch_port_id=patchport_id)
        session.session.add(myNetDevice)
        session.session.commit()

        flash('Benutzer angelegt', 'success')
        return redirect(url_for('.user_show', user_id = myUser.id))
    return render_template('user/user_create.html',
        page_title=u"Neuer Nutzer", form=form)


@bp.route('/search', methods=['GET', 'POST'])
@nav.navigate("Suchen")
def search():
    form = UserSearchForm()
    if form.validate_on_submit():
        userResult = user.User.q
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
        session.session.add(myHost)
        session.session.commit()
        flash('Host angelegt', 'success')
        return render_template('user/host_create.html', form=form,
            results=hostResult.all())
    return render_template('user/host_create.html', form=form,
        results=hostResult.all())
