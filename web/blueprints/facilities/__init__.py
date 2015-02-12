# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.facilities
    ~~~~~~~~~~~~~~

    This module defines view functions for /facilities
    :copyright: (c) 2012 by AG DSN.
"""

from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, url_for
from flask.ext.login import current_user
from flask.json import jsonify
from pycroft import lib
from pycroft.helpers import facilities
from pycroft.lib.user import has_positive_balance, has_exceeded_traffic
from pycroft.model.session import session
from pycroft.model.facilities import Room, Dormitory
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.facilities.forms import RoomForm, DormitoryForm, \
    RoomLogEntry
from web.blueprints.access import BlueprintAccess
from web.template_filters import datetime_filter

bp = Blueprint('facilities', __name__, )
access = BlueprintAccess(bp, ['facilities_show'])
nav = BlueprintNavigation(bp, "Wohnheime", blueprint_access=access)


@bp.route('/')
@nav.navigate(u"Wohnheime")
# careful with permissions here, redirects!
def overview():
    dormitories_list = Dormitory.q.all()
    dormitories_list = facilities.sort_dormitories(dormitories_list)
    return render_template('facilities/overview.html',
        dormitories=dormitories_list)


@bp.route('/show/<dormitory_id>')
@access.require('facilities_show')
def dormitory_show(dormitory_id):
    dormitory = Dormitory.q.get(dormitory_id)
    rooms_list = dormitory.rooms
    return render_template('facilities/dormitory_show.html',
        page_title=u"Wohnheim " + dormitory.short_name, rooms=rooms_list)


@bp.route('/room/show/<room_id>', methods=['GET', 'POST'])
@access.require('facilities_show')
def room_show(room_id):
    room = Room.q.get(room_id)
    form = RoomLogEntry()

    if form.validate_on_submit():
        lib.logging.log_room_event(form.message.data, current_user, room)
        flash(u'Kommentar hinzugefügt', 'success')

    room_log_list = room.room_log_entries[::-1]

    return render_template('facilities/room_show.html',
        page_title=u"Raum " + str(room.dormitory.short_name) + u" " + \
                   str(room.level) + u"-" + str(room.number),
        room=room,
        room_log=room_log_list,
        form=form)


@bp.route('/room/logs/<room_id>')
@access.require('facilities_show')
def room_logs_json(room_id):
    return jsonify(items=map(
        lambda entry: {
            'created_at': datetime_filter(entry.created_at),
            'user': {
                'title': entry.author.name,
                'href': url_for("user.user_show", user_id=entry.author.id)
            },
            'message': entry.message
        },
        Room.q.get(room_id).room_log_entries[::-1]
    ))


# ToDo: Review this!
@bp.route('/levels/<int:dormitory_id>')
@access.require('facilities_show')
def dormitory_levels(dormitory_id):
    dormitory = Dormitory.q.get(dormitory_id)
    rooms_list = Room.q.filter_by(
        dormitory_id=dormitory_id).order_by(Room.level).distinct()
    levels_list = [room.level for room in rooms_list]
    levels_list = list(set(levels_list))

    return render_template('facilities/levels.html',
        levels=levels_list, dormitory_id=dormitory_id, dormitory=dormitory,
        page_title=u"Etagen Wohnheim {}".format(dormitory.short_name))


# ToDo: Review this!
@bp.route('/levels/<int:dormitory_id>/rooms/<int:level>')
@access.require('facilities_show')
def dormitory_level_rooms(dormitory_id, level):
    dormitory = Dormitory.q.get(dormitory_id)
    level_l0 = "{:02d}".format(level)

    #TODO depending on, whether a user is living in the room, the room is
    # a link to the user. If there is more then one user, the room is
    # duplicated
    return render_template(
        'facilities/rooms.html',
        level=level_l0,
        dormitory=dormitory,
        page_title=u"Zimmer der Etage {:d} des Wohnheims {}".format(
            level, dormitory.short_name
        )
    )


#todo think about a better place for this function
# it surely will be used elsewhere…
def user_btn_class(user):
    if not has_positive_balance(user):
        return "btn-warning"
    elif not user.has_property("internet"):
        return "btn-danger"
    elif has_exceeded_traffic(user):
        return "btn-info"
    else:
        return "btn-success"


@bp.route('/levels/<int:dormitory_id>/rooms/<int:level>/json')
@access.require('facilities_show')
def dormitory_level_rooms_json(dormitory_id, level):
    return jsonify(items=map(
        lambda room: {
            'room': {
                'href': url_for(".room_show", room_id=room.id),
                'title': "{:02d} - {}".format(level, room.number)
            },
            'inmates': map(
                lambda user: {
                    'href': url_for("user.user_show", user_id=user.id),
                    'title': user.name,
                    'btn_class': user_btn_class(user)
                },
                room.users
            )
        },
        Room.q.filter_by(
            dormitory_id=dormitory_id, level=level).order_by(Room.number)
    ))
