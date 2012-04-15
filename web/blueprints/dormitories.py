# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.dormitories
    ~~~~~~~~~~~~~~

    This module defines view functions for /dormitories
    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flaskext.wtf import Form, TextField, validators, BooleanField, SubmitField
from pycroft.model import dormitory, session
from pycroft.model.dormitory import Room, Dormitory
from web.blueprints import BlueprintNavigation

bp = Blueprint('dormitories', __name__, )
nav = BlueprintNavigation(bp, "Wohnheime")


@bp.route('/')
@nav.navigate(u"Wohnheime")
def dormitories():
    dormitories_list = dormitory.Dormitory.q.all()
    return render_template('dormitories/dormitories_list.html',
        page_title=u"Wohnheime", dormitories=dormitories_list)

@bp.route('/show/<dormitory_short_name>')
def dormitory_show(dormitory_short_name):
    rooms_list = dormitory.Room.q.join(Dormitory).filter(Dormitory.short_name == dormitory_short_name).all()
    return render_template('dormitories/dormitory_show.html',
        page_title=u"Wohnheim "+dormitory_short_name, rooms=rooms_list)


class DormitoryForm(Form):
    short_name = TextField(u"Kürzel")
    number = TextField(u"Nummer")
    street = TextField(u"Straße", validators=[validators.Length(min=5)])


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate(u"Neues Wohnheim")
def dormitory_create():
    form = DormitoryForm()
    if form.validate_on_submit():
        myDormitory = dormitory.Dormitory(short_name=form.short_name.data,
            street=form.street.data, number=form.number.data)
        session.session.add(myDormitory)
        session.session.commit()
        flash('Wohnheim angelegt', 'success')
        return redirect(url_for('.dormitories'))
    return render_template('dormitories/dormitory_create.html',
                           page_title=u"Neues Wohnheim", form=form)

@bp.route('/room/delete/<room_id>')
def room_delete(room_id):
    dormitory.Room.q.filter(Room.id == room_id).delete(synchronize_session='fetch')
    session.session.commit()
    return redirect(url_for('.dormitories'))

@bp.route('/room/show/<room_id>')
def room_show(room_id):
    room_list = dormitory.Room.q.filter(Room.id == room_id).all()
    return render_template('dormitories/room_show.html',
        page_title=u"Raum "+room_id, room=room_list)

class RoomForm(Form):
    number = TextField(u"Nummer")
    level = TextField(u"Etage")
    inhabitable = BooleanField(u"Bewohnbar")
    dormitory_id = TextField(u'Wohnheim')

@bp.route('/room/create', methods=['GET', 'POST'])
@nav.navigate(u"Neuer Raum")
def room_create():
    form = RoomForm()
    if form.validate_on_submit():
        myRoom = dormitory.Room(number=form.number.data, level=form.level.data, inhabitable=form.inhabitable.data, dormitory_id=form.dormitory_id.data)
        session.session.add(myRoom)
        session.session.commit()
        flash('Raum angelegt', 'success')
        return redirect(url_for('.room_show', room_id=myRoom.id))
    return render_template('dormitories/dormitory_create.html',page_title=u"Neuer Raum", form=form)
