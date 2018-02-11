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

from flask import (Blueprint, flash, jsonify, render_template, url_for,
                   redirect, request)
from flask_login import current_user

from pycroft import lib, config
from pycroft.helpers import facilities
from pycroft.lib.user import status_query
from pycroft.model import session
from pycroft.model.facilities import Room, Site
from pycroft.model.user import User
from web.blueprints.access import BlueprintAccess
from web.blueprints.facilities.forms import (
    RoomForm, BuildingForm, RoomLogEntry)
from web.blueprints.helpers.user import user_button
from web.blueprints.navigation import BlueprintNavigation
from web.template_filters import datetime_filter

bp = Blueprint('facilities', __name__)
access = BlueprintAccess(bp, required_properties=['facilities_show'])
nav = BlueprintNavigation(bp, "Wohnheime", blueprint_access=access)

@bp.route('/')
def root():
    return redirect(url_for(".overview"))

@nav.navigate(u"Wohnheime")
@bp.route('/sites/')
def overview():
    return render_template('facilities/site_overview.html')

@bp.route('/sites/json')
def overview_json():
    return jsonify(items=[{
            'site': {
                'title': site.name,
                'href': url_for("facilities.site_show", site_id=site.id)
            },
            'buildings': [{
                    'href': url_for("facilities.building_levels", building_shortname=building.short_name),
                    'title': building.street+" "+building.number
                } for building in facilities.sort_buildings(site.buildings)]
        } for site in Site.q.all()])


@bp.route('/sites/<int:site_id>')
def site_show(site_id):
    site = Site.q.get(site_id)
    buildings_list = facilities.sort_buildings(site.buildings)
    return render_template('facilities/site_show.html',
        buildings=buildings_list,
        page_title=site.name)


@bp.route('/buildings/<int:building_id>/')
@bp.route('/buildings/<building_shortname>/')
def building_show(building_id=None, building_shortname=None):
    building = facilities.determine_building(id=building_id, shortname=building_shortname)
    rooms_list = building.rooms
    return render_template('facilities/building_show.html',
        page_title=u"Wohnheim " + building.short_name, rooms=rooms_list)


# ToDo: Review this!
@bp.route('/buildings/<int:building_id>/levels/')
@bp.route('/buildings/<building_shortname>/levels/')
def building_levels(building_id=None, building_shortname=None):
    building = facilities.determine_building(id=building_id, shortname=building_shortname)
    rooms_list = building.rooms
    levels_list = [room.level for room in rooms_list]
    levels_list = list(set(levels_list))

    return render_template('facilities/levels.html',
        levels=levels_list, building=building,
        page_title=u"Etagen Wohnheim {}".format(building.short_name))


# ToDo: Review this!
@bp.route('/buildings/<int:building_id>/levels/<int:level>/rooms/')
@bp.route('/buildings/<building_shortname>/levels/<int:level>/rooms/')
def building_level_rooms(level, building_id=None, building_shortname=None):
    building = facilities.determine_building(building_shortname, building_id)
    level_l0 = "{:02d}".format(level)

    #TODO depending on, whether a user is living in the room, the room is
    # a link to the user. If there is more then one user, the room is
    # duplicated
    return render_template(
        'facilities/rooms.html',
        level=level_l0,
        building=building,
        page_title=u"Zimmer der Etage {:d} des Wohnheims {}".format(
            level, building.short_name
        )
    )


@bp.route('/buildings/<int:building_id>/levels/<int:level>/rooms/json')
@bp.route('/buildings/<building_shortname>/levels/<int:level>/rooms/json')
def building_level_rooms_json(level, building_id=None, building_shortname=None):
    building = facilities.determine_building(id=building_id, shortname=building_shortname)
    all_users = bool(request.args.get('all_users', 0, type=int))

    rooms = session.session.query(Room).filter(
        Room.building==building, Room.level==level
    ).order_by(Room.number).all()

    status_q = status_query().join(Room).filter(
        Room.building == building, Room.level == level,
        # `True` acts idempotently on `filter()`
        True if all_users else User.member_of(config.member_group),
    )

    statuses = {r.id: [] for r in rooms}
    for row in status_q.all():
        statuses[row.User.room_id].append(row)


    return jsonify(items=[{
            'room': {
                'href': url_for(".room_show", room_id=room.id),
                'title': "{:02d} - {}".format(level, room.number)
            },
            'inhabitants': [user_button(s.User, s) for s in statuses[room.id]]
        } for room in rooms])


@bp.route('/rooms/<int:room_id>', methods=['GET', 'POST'])
def room_show(room_id):
    room = Room.q.get(room_id)
    form = RoomLogEntry()

    if form.validate_on_submit():
        lib.logging.log_room_event(form.message.data, current_user, room)
        flash(u'Kommentar hinzugefügt', 'success')
        session.session.commit()

    room_log_list = reversed(room.log_entries)

    return render_template('facilities/room_show.html',
        page_title=u"Raum " + str(room.building.short_name) + u" " + \
                   str(room.level) + u"-" + str(room.number),
        room=room,
        ports=room.patch_ports,
        room_log=room_log_list,
        user_buttons=list(map(user_button, room.users)),
        form=form)


@bp.route('/rooms/<int:room_id>/logs/json')
def room_logs_json(room_id):
    return jsonify(items=[{
            'created_at': datetime_filter(entry.created_at),
            'user': {
                'title': entry.author.name,
                'href': url_for("user.user_show", user_id=entry.author.id)
            },
            'message': entry.message
        } for entry in reversed(Room.q.get(room_id).log_entries)])


@bp.route('/json/levels')
@access.require('facilities_show')
def json_levels():
    building_id = request.args.get('building', 0, type=int)
    levels = session.session.query(Room.level.label('level')).filter_by(
        building_id=building_id).order_by(Room.level).distinct()
    return jsonify(dict(items=[entry.level for entry in levels]))


@bp.route('/json/rooms')
@access.require('facilities_show')
def json_rooms():
    building_id = request.args.get('building', 0, type=int)
    level = request.args.get('level', 0, type=int)
    rooms = session.session.query(
        Room.number.label("room_num")).filter_by(
        building_id=building_id, level=level).order_by(
        Room.number).distinct()
    return jsonify(dict(items=[entry.room_num for entry in rooms]))
