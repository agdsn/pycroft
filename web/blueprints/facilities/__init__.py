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
from operator import and_

from collections import defaultdict
from flask import (Blueprint, flash, jsonify, render_template, url_for,
                   redirect, request, abort)
from flask_login import current_user
from flask_wtf import FlaskForm as Form
from sqlalchemy.sql import and_, select, exists
from sqlalchemy.orm import joinedload, aliased

from pycroft import lib, config
from pycroft.helpers import facilities
from pycroft.helpers.i18n import gettext
from pycroft.helpers.net import sort_ports
from pycroft.lib.address import get_or_create_address
from pycroft.lib.facilities import get_overcrowded_rooms, create_room, edit_room, \
    RoomAlreadyExistsException, suggest_room_address_data
from pycroft.lib.infrastructure import create_patch_port, edit_patch_port, delete_patch_port, \
    PatchPortAlreadyExistsException
from pycroft.model import session
from pycroft.model.facilities import Room, Site, Building
from pycroft.model.port import PatchPort
from pycroft.model.property import CurrentProperty
from pycroft.model.user import User
from web.blueprints.access import BlueprintAccess
from web.blueprints.facilities.forms import (
    RoomLogEntry, PatchPortForm, CreateRoomForm, EditRoomForm)
from web.blueprints.helpers.log import format_room_log_entry
from web.blueprints.helpers.user import user_button
from web.blueprints.navigation import BlueprintNavigation
from .address import get_address_entity, address_entity_search_query
from .tables import (BuildingLevelRoomTable, RoomLogTable, SiteTable,
                     RoomOvercrowdedTable, PatchPortTable)

bp = Blueprint('facilities', __name__)
access = BlueprintAccess(bp, required_properties=['facilities_show'])
nav = BlueprintNavigation(bp, "Wohnheime", blueprint_access=access)

@bp.route('/')
def root():
    return redirect(url_for(".overview"))

@nav.navigate(u"Wohnheime")
@bp.route('/sites/')
def overview():
    return render_template(
        'facilities/site_overview.html',
        site_table=SiteTable(data_url=url_for('.overview_json')),
    )

@bp.route('/sites/json')
def overview_json():
    T = SiteTable
    return jsonify(items=[{
            'site': T.site.value(
                title=site.name,
                href=url_for("facilities.site_show", site_id=site.id)
            ),
            'buildings': [T.buildings.single_value(
                href=url_for("facilities.building_levels",
                             building_shortname=building.short_name),
                title=building.street_and_number
            ) for building in facilities.sort_buildings(site.buildings)]
        } for site in Site.q.order_by(Site.name).all()])


@bp.route('/site/<int:site_id>')
def site_show(site_id):
    site = Site.get(site_id)
    buildings_list = facilities.sort_buildings(site.buildings)
    return render_template('facilities/site_show.html',
        buildings=buildings_list,
        page_title=site.name)


@bp.route('/building/<int:building_id>/')
@bp.route('/building/<building_shortname>/')
def building_show(building_id=None, building_shortname=None):
    building = facilities.determine_building(id=building_id, shortname=building_shortname)

    if building is None:
        flash(u"Gebäude existiert nicht!", 'error')
        abort(404)

    rooms_list = building.rooms
    return render_template('facilities/building_show.html',
        page_title=u"Wohnheim " + building.short_name, rooms=rooms_list)


# ToDo: Review this!
@bp.route('/building/<int:building_id>/levels/')
@bp.route('/building/<building_shortname>/levels/')
def building_levels(building_id=None, building_shortname=None):
    building = facilities.determine_building(id=building_id, shortname=building_shortname)

    if building is None:
        flash(u"Gebäude existiert nicht!", 'error')
        abort(404)

    rooms_list = building.rooms
    levels_list = [room.level for room in rooms_list]
    levels_list = list(set(levels_list))

    return render_template(
        'facilities/levels.html',
        levels=levels_list, building=building,
        page_title=f"Etagen Wohnheim {building.short_name}",
        suggested_address=suggest_room_address_data(building),
   )


@bp.route('/room/create', methods=['GET', 'POST'])
@access.require('facilities_change')
def room_create():
    building_id = request.args.get("building_id")

    building = None

    if building_id:
        building = Building.get(building_id)

        if not building:
            flash(f"Gebäude mit ID {building_id} nicht gefunden!", "error")
            return redirect(url_for('.overview'))

    form = CreateRoomForm(building=building)

    if form.validate_on_submit():
        try:
            address = get_or_create_address(**form.address_kwargs)
            room = create_room(form.building.data, form.level.data, form.number.data,
                               address=address,
                               processor=current_user, inhabitable=form.inhabitable.data)

            session.session.commit()

            flash(f"Der Raum {room.short_name} wurde erfolgreich erstellt.", "success")

            return redirect(url_for('.room_show', room_id=room.id))
        except RoomAlreadyExistsException:
            form.number.errors.append("Ein Raum mit diesem Namen existiert bereits in dieser Etage!")
            session.session.rollback()

    form_args = {
        'form': form,
        'cancel_to': url_for('.overview')
    }

    suggestion = suggest_room_address_data(building)
    if suggestion and not form.is_submitted():
        form.address_street.data = suggestion.street
        form.address_number.data = suggestion.number
        form.address_zip_code.data = suggestion.zip_code
        form.address_city.data = suggestion.city
        form.address_state.data = suggestion.state
        form.address_country.data = suggestion.country

    return render_template('generic_form.html',
                           page_title="Raum erstellen",
                           form_args=form_args)


@bp.route('/room/<int:room_id>/create', methods=['GET', 'POST'])
@access.require('facilities_change')
def room_edit(room_id):
    room = Room.get(room_id)

    if not room:
        flash(f"Raum mit ID {room_id} nicht gefunden!", "error")
        return redirect(url_for('.overview'))

    form = EditRoomForm(building=room.building.short_name,
                        level=room.level,
                        number=room.number,
                        inhabitable=room.inhabitable,
                        vo_suchname=room.swdd_vo_suchname)

    if form.validate_on_submit():
        try:
            with session.session.no_autoflush:
                address = get_or_create_address(**form.address_kwargs)
                edit_room(room, form.number.data, form.inhabitable.data, form.vo_suchname.data,
                          address=address, processor=current_user)

            session.session.commit()

            flash(f"Der Raum {room.short_name} wurde erfolgreich bearbeitet.",
                  "success")

            return redirect(url_for('.room_show', room_id=room.id))
        except RoomAlreadyExistsException:
            form.number.errors.append("Ein Raum mit diesem Namen existiert bereits in dieser Etage!")

    old_addr = room.address
    if not form.is_submitted():
        form.address_street.data = old_addr.street
        form.address_number.data = old_addr.number
        form.address_addition.data = old_addr.addition
        form.address_zip_code.data = old_addr.zip_code
        form.address_city.data = old_addr.city
        form.address_state.data = old_addr.state
        form.address_country.data = old_addr.country

    if room.users_sharing_address:
        flash(gettext("Dieser Raum hat {} bewohner ({}), die die Adresse des Raums teilen."
                      " Ihre Adresse wird beim Ändern automatisch angepasst.")
              .format(len(room.users_sharing_address),
                      ', '.join(u.name for u in room.users_sharing_address)),
              'info')

    form_args = {
        'form': form,
        'cancel_to': url_for('.room_show', room_id=room.id)
    }

    return render_template('generic_form.html',
                           page_title="Raum bearbeiten",
                           form_args=form_args)


# ToDo: Review this!
@bp.route('/building/<int:building_id>/level/<int:level>/rooms/')
@bp.route('/building/<building_shortname>/level/<int:level>/rooms/')
def building_level_rooms(level, building_id=None, building_shortname=None):
    building = facilities.determine_building(building_shortname, building_id)

    if building is None:
        flash(u"Gebäude existiert nicht!", 'error')
        abort(404)

    level_l0 = f"{level:02d}"

    room_table = BuildingLevelRoomTable(
        data_url=url_for('.building_level_rooms_json',
                         building_shortname=building.short_name, level=level))
    return render_template(
        'facilities/rooms.html',
        level=level_l0,
        building=building,
        page_title=f"Zimmer der Etage {level:d} des Wohnheims {building.short_name}",
        room_table=room_table,
    )


@bp.route('/building/<int:building_id>/level/<int:level>/rooms/json')
@bp.route('/building/<building_shortname>/level/<int:level>/rooms/json')
def building_level_rooms_json(level, building_id=None, building_shortname=None):
    building = facilities.determine_building(id=building_id, shortname=building_shortname)

    if building is None:
        flash(u"Gebäude existiert nicht!", 'error')
        abort(404)

    all_users = bool(request.args.get('all_users', 0, type=int))
    # We need to alias User, otherwise sqlalchemy selects User.id as user_id,
    # which collides with the joined-loaded user.current_properties.user_id.
    user = aliased(User)

    user_join_condition = user.room_id == Room.id
    if not all_users:
        user_join_condition = and_(
            user_join_condition,
            exists(select(CurrentProperty).where(
                and_(CurrentProperty.user_id == user.id,
                     CurrentProperty.property_name == 'network_access')))
        )

    rooms_users_q = (session.session.query(Room, user)
                     .options(joinedload(user.current_properties))
                     .filter(and_(Room.building == building, Room.level == level))
                     .outerjoin(user, user_join_condition))

    level_inhabitants = defaultdict(lambda: [])
    for room, user in rooms_users_q.all():
        if user is not None:
            level_inhabitants[room].append(user)
        else:
            # Ensure room is in level_inhabitants
            level_inhabitants[room]

    T = BuildingLevelRoomTable
    return jsonify(items=[{
            'room': T.room.value(
                href=url_for(".room_show", room_id=room.id),
                title=f"{level:02d} - {room.number}"
            ),
            'inhabitants': [user_button(i) for i in inhabitants]
        } for room, inhabitants in level_inhabitants.items()])


@bp.route('/room/<int:switch_room_id>/patch-port/create', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def patch_port_create(switch_room_id):
    switch_room = Room.get(switch_room_id)

    if not switch_room:
        flash(f"Raum mit ID {switch_room_id} nicht gefunden!", "error")
        return redirect(url_for('.overview'))

    if not switch_room.is_switch_room:
        flash("Dieser Raum ist kein Switchraum!", "error")
        return redirect(url_for('.room_show', room_id=switch_room_id))

    form = PatchPortForm(switch_room=switch_room.short_name,
                         building=switch_room.building,
                         level=switch_room.level)

    if form.validate_on_submit():
        room = Room.q.filter_by(building=form.building.data,
                                level=form.level.data,
                                number=form.room_number.data).one()
        try:
            patch_port = create_patch_port(form.name.data, room, switch_room, current_user)

            session.session.commit()

            flash(
                f"Der Patch-Port {patch_port.name} zum Zimmer {patch_port.room.short_name} wurde erfolgreich erstellt.",
                  "success")

            return redirect(url_for('.room_show', room_id=switch_room_id, _anchor="patchpanel"))
        except PatchPortAlreadyExistsException:
            session.session.rollback()

            form.name.errors.append("Ein Patch-Port mit dieser Bezeichnung existiert bereits in diesem Switchraum.")

    form_args = {
        'form': form,
        'cancel_to': url_for('.room_show', room_id=switch_room_id, _anchor="patchpanel")
    }

    return render_template('generic_form.html',
                           page_title="Patch-Port erstellen",
                           form_args=form_args)


@bp.route('/room/<int:switch_room_id>/patch-port/<int:patch_port_id>/edit', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def patch_port_edit(switch_room_id, patch_port_id):
    switch_room = Room.get(switch_room_id)
    patch_port = PatchPort.get(patch_port_id)

    if not switch_room:
        flash(f"Raum mit ID {switch_room_id} nicht gefunden!", "error")
        return redirect(url_for('.overview'))

    if not switch_room.is_switch_room:
        flash("Dieser Raum ist kein Switchraum!", "error")
        return redirect(url_for('.room_show', room_id=switch_room_id))

    if not patch_port:
        flash(f"Patch-Port mit ID {patch_port_id} nicht gefunden!", "error")
        return redirect(url_for('.room_show', room_id=switch_room_id))

    if not patch_port.switch_room == switch_room:
        flash(f"Patch-Port ist nicht im Switchraum!", "error")
        return redirect(url_for('.room_show', room_id=switch_room_id))

    form = PatchPortForm(switch_room=switch_room.short_name,
                         name=patch_port.name,
                         building=patch_port.room.building,
                         level=patch_port.room.level,
                         room_number=patch_port.room.number)

    if form.validate_on_submit():
        room = Room.q.filter_by(building=form.building.data,
                                level=form.level.data,
                                number=form.room_number.data).one()

        try:
            edit_patch_port(patch_port, form.name.data, room,current_user)

            session.session.commit()

            flash("Der Patch-Port wurde erfolgreich bearbeitet.", "success")

            return redirect(url_for('.room_show', room_id=switch_room_id, _anchor="patchpanel"))
        except PatchPortAlreadyExistsException:
            session.session.rollback()

            form.name.errors.append("Ein Patch-Port mit dieser Bezeichnung existiert bereits in diesem Switchraum.")

    form_args = {
        'form': form,
        'cancel_to': url_for('.room_show', room_id=switch_room_id, _anchor="patchpanel")
    }

    return render_template('generic_form.html',
                           page_title="Patch-Port bearbeiten",
                           form_args=form_args)


@bp.route('/room/<int:switch_room_id>/patch-port/<int:patch_port_id>/delete', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def patch_port_delete(switch_room_id, patch_port_id):
    switch_room = Room.get(switch_room_id)
    patch_port = PatchPort.get(patch_port_id)

    if not switch_room:
        flash(f"Raum mit ID {switch_room_id} nicht gefunden!", "error")
        return redirect(url_for('.overview'))

    if not switch_room.is_switch_room:
        flash("Dieser Raum ist kein Switchraum!", "error")
        return redirect(url_for('.room_show', room_id=switch_room_id))

    if not patch_port:
        flash(f"Patch-Port mit ID {patch_port_id} nicht gefunden!", "error")
        return redirect(url_for('.room_show', room_id=switch_room_id))

    if not patch_port.switch_room == switch_room:
        flash(f"Patch-Port ist nicht im Switchraum!", "error")
        return redirect(url_for('.room_show', room_id=switch_room_id))

    form = Form()

    if form.validate_on_submit():
        delete_patch_port(patch_port, current_user)

        session.session.commit()

        flash("Der Patch-Port wurde erfolgreich gelöscht.", "success")

        return redirect(url_for('.room_show', room_id=switch_room_id, _anchor="patchpanel"))

    form_args = {
        'form': form,
        'cancel_to': url_for('.room_show', room_id=switch_room_id, _anchor="patchpanel"),
        'submit_text': 'Löschen',
        'actions_offset': 0
    }

    return render_template('generic_form.html',
                           page_title="Patch-Port löschen",
                           form_args=form_args)


@bp.route('/room/<int:room_id>', methods=['GET', 'POST'])
def room_show(room_id):
    room = Room.get(room_id)

    if room is None:
        flash(u"Zimmer existiert nicht!", 'error')
        abort(404)

    form = RoomLogEntry()

    if form.validate_on_submit():
        lib.logging.log_room_event(form.message.data, current_user, room)
        flash(u'Kommentar hinzugefügt', 'success')
        session.session.commit()

    room_log_table = RoomLogTable(
        data_url=url_for(".room_logs_json", room_id=room.id))

    patch_port_table = PatchPortTable(data_url=url_for(".room_patchpanel_json", room_id=room.id),
                                      room_id=room_id)

    return render_template('facilities/room_show.html',
                           page_title=f"Raum {room.short_name}",
                           room=room,
                           ports=room.patch_ports,
                           user_buttons=list(map(user_button, room.users)),
                           room_log_table=room_log_table,
                           patch_port_table=patch_port_table,
                           form=form, )


@bp.route('/room/<int:room_id>/logs/json')
def room_logs_json(room_id):
    return jsonify(items=[format_room_log_entry(entry) for entry in
                          reversed(Room.get(room_id).log_entries)])


@bp.route('/room/<int:room_id>/patchpanel/json')
def room_patchpanel_json(room_id):
    room = Room.get(room_id)

    if not room:
        abort(404)

    if not room.is_switch_room:
        abort(400)

    patch_ports = PatchPort.q.filter_by(switch_room=room).all()
    patch_ports = sort_ports(patch_ports)
    T = PatchPortTable

    return jsonify(items=[{
        "name": port.name,
        "room": T.room.value(
            href=url_for(".room_show", room_id=port.room.id),
            title=port.room.short_name
        ),
        "switch_port": T.switch_port.value(
            href=url_for("infrastructure.switch_show",
                         switch_id=port.switch_port.switch.host_id),
            title=f"{port.switch_port.switch.host.name}/{port.switch_port.name}"
        ) if port.switch_port else None,
        'edit_link': T.edit_link.value(
            hef=url_for(".patch_port_edit", switch_room_id=room.id, patch_port_id=port.id),
            title="Bearbeiten",
            icon='fa-edit',
            # TODO decide on a convention here
            btn_class='btn-link',
        ),
        'delete_link': T.delete_link.value(
            href=url_for(".patch_port_delete", switch_room_id=room.id, patch_port_id=port.id),
            title="Löschen",
            icon='fa-trash',
            btn_class='btn-link'
        ),
    } for port in patch_ports])


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


@bp.route('/overcrowded', defaults={'building_id': None})
@bp.route('/overcrowded/<int:building_id>')
@nav.navigate(u"Mehrfachbelegungen")
def overcrowded(building_id):
    page_title = "Mehrfachbelegungen"
    if building_id:
        building = facilities.determine_building(id=building_id)
        if building is None:
            flash(u"Gebäude existiert nicht!", 'error')
            abort(404)
        page_title = f"Mehrfachbelegungen {building.short_name}"

    return render_template(
        "facilities/room_overcrowded.html",
        page_title=page_title,
        room_table=RoomOvercrowdedTable(
            data_url=url_for('.overcrowded_json', building_id=building_id)),
    )

@bp.route('/overcrowded/json', defaults={'building_id': None})
@bp.route('/overcrowded/<int:building_id>/json')
def overcrowded_json(building_id):
    rooms = get_overcrowded_rooms(building_id)
    T = RoomOvercrowdedTable

    return jsonify(items=[{
        'room': T.room.value(
            title='{} / {:02d} / {}'.format(
                inhabitants[0].room.building.short_name,
                inhabitants[0].room.level, inhabitants[0].room.number),
            href=url_for("facilities.room_show",
                         room_id=inhabitants[0].room.id)
        ),
        'inhabitants': [user_button(user) for user in inhabitants]
    } for inhabitants in rooms.values()])


@bp.route('address/<string:type>')
def addresses(type):
    try:
        entity = get_address_entity(type)
    except ValueError as e:
        return jsonify(errors=[e.args[0]]), 404

    query: str = request.args.get('query', '').replace('%', '%%')
    limit: int = request.args.get('limit', 10, type=int)

    address_q = address_entity_search_query(query, entity, session.session, limit)

    return jsonify(items=[str(row[0]) for row in address_q.all()])
