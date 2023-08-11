# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.facilities
    ~~~~~~~~~~~~~~

    This module defines view functions for /facilities
    :copyright: (c) 2012 by AG DSN.
"""
from collections import defaultdict
import typing as t

from flask import (
    Blueprint,
    flash,
    render_template,
    url_for,
    redirect,
    request,
    abort,
)
from flask.typing import ResponseReturnValue
from flask_login import current_user
from flask_wtf import FlaskForm as Form
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy.sql import and_, select, exists

import pycroft.lib.facilities
from pycroft import lib
from pycroft.exc import PycroftException
from pycroft.helpers.i18n import gettext
from pycroft.lib.host import sort_ports
from pycroft.lib.address import get_or_create_address
from pycroft.lib.facilities import (
    get_overcrowded_rooms,
    create_room,
    edit_room,
    RoomAlreadyExistsException,
    suggest_room_address_data,
)
from pycroft.lib.infrastructure import create_patch_port, edit_patch_port, \
    delete_patch_port, \
    PatchPortAlreadyExistsException
from pycroft.model import session
from pycroft.model.facilities import Room, Site, Building
from pycroft.model.port import PatchPort
from pycroft.model.property import CurrentProperty
from pycroft.model.user import User
from web.blueprints.access import BlueprintAccess
from web.blueprints.facilities.forms import (
    RoomLogEntry,
    PatchPortForm,
    CreateRoomForm,
    EditRoomForm,
    CreateAddressForm,
)
from web.blueprints.helpers.log import format_room_log_entry
from web.blueprints.helpers.user import user_button
from web.blueprints.navigation import BlueprintNavigation
from web.table.table import TableResponse, LinkColResponse, BtnColResponse
from .address import get_address_entity, address_entity_search_query
from .tables import (
    BuildingLevelRoomTable,
    RoomLogTable,
    SiteTable,
    RoomOvercrowdedTable,
    PatchPortTable,
    SiteRow,
    BuildingLevelRoomRow,
    PatchPortRow,
    RoomOvercrowdedRow,
)
from ..helpers.exception import abort_on_error, ErrorHandlerMap
from ..helpers.log_tables import LogTableRow

bp = Blueprint('facilities', __name__)
access = BlueprintAccess(bp, required_properties=['facilities_show'])
nav = BlueprintNavigation(bp, "Wohnheime", icon='fa-building', blueprint_access=access)

@bp.route('/')
def root() -> ResponseReturnValue:
    return redirect(url_for(".overview"))

@nav.navigate("Wohnheime", icon='fa-building')
@bp.route('/sites/')
def overview() -> ResponseReturnValue:
    return render_template(
        'facilities/site_overview.html',
        site_table=SiteTable(data_url=url_for('.overview_json')),
    )

@bp.route('/sites/json')
def overview_json() -> ResponseReturnValue:
    return TableResponse[SiteRow](
        items=[
            SiteRow(
                site=LinkColResponse(
                    title=site.name,
                    href=url_for("facilities.site_show", site_id=site.id),
                ),
                buildings=[
                    BtnColResponse(
                        href=url_for(
                            "facilities.building_levels",
                            building_shortname=building.short_name,
                        ),
                        title=building.street_and_number,
                    )
                    for building in pycroft.lib.facilities.sort_buildings(
                        site.buildings
                    )
                ],
            )
            for site in Site.q.order_by(Site.name).all()
        ]
    ).model_dump()


@bp.route('/site/<int:site_id>')
def site_show(site_id: int) -> ResponseReturnValue:
    site = session.session.get(Site, site_id)
    if not site:
        flash("Site existiert nicht!", "error")
        abort(404)

    buildings_list = pycroft.lib.facilities.sort_buildings(site.buildings)
    return render_template('facilities/site_show.html',
        buildings=buildings_list,
        page_title=site.name)


def determine_building_or_404(
    id: int | None = None,
    shortname: str | None = None,
) -> Building:
    building = pycroft.lib.facilities.determine_building(id=id, shortname=shortname)
    if building is None:
        flash("Gebäude existiert nicht!", "error")
        abort(404)
    return building


@bp.route("/building/<int:building_id>/")
@bp.route("/building/<building_shortname>/")
def building_show(
    building_id: int | None = None, building_shortname: str | None = None
) -> ResponseReturnValue:
    building = determine_building_or_404(id=building_id, shortname=building_shortname)
    rooms_list = building.rooms
    return render_template('facilities/building_show.html',
        page_title="Wohnheim " + building.short_name, rooms=rooms_list)


# ToDo: Review this!
@bp.route("/building/<int:building_id>/levels/")
@bp.route("/building/<building_shortname>/levels/")
def building_levels(
    building_id: int | None = None, building_shortname: str | None = None
) -> ResponseReturnValue:
    building = determine_building_or_404(id=building_id, shortname=building_shortname)
    levels_list = list({room.level for room in building.rooms})

    return render_template(
        'facilities/levels.html',
        levels=levels_list, building=building,
        page_title=f"Etagen Wohnheim {building.short_name}",
        suggested_address=suggest_room_address_data(building),
   )


@bp.route('/room/create', methods=['GET', 'POST'])
@access.require('facilities_change')
def room_create() -> ResponseReturnValue:
    building_id: int | None = request.args.get("building_id", type=int)
    building = None
    if building_id:
        building = determine_building_or_404(id=building_id)

    form = CreateRoomForm(building=building)

    def default_response() -> ResponseReturnValue:
        return render_template(
            "generic_form.html",
            page_title="Raum erstellen",
            form_args={"form": form, "cancel_to": url_for(".overview")},
        )

    if not form.is_submitted():
        form.set_address_fields(suggest_room_address_data(building))
        return default_response()

    if not form.validate():
        return default_response()

    sess = session.session

    _handlers: ErrorHandlerMap = {
        RoomAlreadyExistsException: lambda _: form.number.errors.append(
            "Ein Raum mit diesem Namen existiert bereits in dieser Etage!"
        )
    }
    with abort_on_error(default_response, _handlers), sess.begin_nested():
        address = get_or_create_address(**form.address_kwargs)
        room = create_room(
            form.building.data,
            form.level.data,
            form.number.data,
            address=address,
            processor=current_user,
            inhabitable=form.inhabitable.data,
        )
    sess.commit()

    flash(f"Der Raum {room.short_name} wurde erfolgreich erstellt.", "success")
    return redirect(url_for(".room_show", room_id=room.id))


@bp.route('/room/<int:room_id>/create', methods=['GET', 'POST'])
@access.require('facilities_change')
def room_edit(room_id: int) -> ResponseReturnValue:
    room = get_room_or_404(room_id)

    form = EditRoomForm(building=room.building.short_name,
                        level=room.level,
                        number=room.number,
                        inhabitable=room.inhabitable,
                        vo_suchname=room.swdd_vo_suchname)

    def default_response() -> ResponseReturnValue:
        if users := room.users_sharing_address:
            flash(
                gettext(
                    "Dieser Raum hat {} bewohner ({}), die die Adresse des Raums teilen."
                    " Ihre Adresse wird beim Ändern automatisch angepasst."
                ).format(len(users), ", ".join(u.name for u in users)),
                "info",
            )

        return render_template(
            "generic_form.html",
            page_title="Raum bearbeiten",
            form_args={
                "form": form,
                "cancel_to": url_for(".room_show", room_id=room.id),
            },
        )

    if not form.is_submitted():
        form.set_address_fields(room.address)
        return default_response()

    if not form.validate():
        return default_response()

    sess = session.session

    _handlers: ErrorHandlerMap = {
        RoomAlreadyExistsException: lambda _: form.number.errors.append(
            "Ein Raum mit diesem Namen existiert bereits in dieser Etage!"
        )
    }
    with abort_on_error(default_response, _handlers), sess.begin_nested():
        address = get_or_create_address(**form.address_kwargs)
        edit_room(
            room,
            form.number.data,
            form.inhabitable.data,
            form.vo_suchname.data,
            address=address,
            processor=current_user,
        )

    flash(f"Der Raum {room.short_name} wurde erfolgreich bearbeitet.", "success")
    return redirect(url_for(".room_show", room_id=room.id))


# ToDo: Review this!
@bp.route("/building/<int:building_id>/level/<int:level>/rooms/")
@bp.route("/building/<building_shortname>/level/<int:level>/rooms/")
def building_level_rooms(
    level: int,
    building_id: int | None = None,
    building_shortname: str | None = None,
) -> ResponseReturnValue:
    building = determine_building_or_404(id=building_id, shortname=building_shortname)
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


@bp.route("/building/<int:building_id>/level/<int:level>/rooms/json")
@bp.route("/building/<building_shortname>/level/<int:level>/rooms/json")
def building_level_rooms_json(
    level: int,
    building_id: int | None = None,
    building_shortname: str | None = None,
) -> ResponseReturnValue:
    building = determine_building_or_404(id=building_id, shortname=building_shortname)

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

    # TODO remove mypy suppression below if moved to `select`
    rooms_users_q = (session.session.query(Room, user)
                     .options(joinedload(user.current_properties))
                     .filter(and_(Room.building == building, Room.level == level))
                     .outerjoin(user, user_join_condition))

    level_inhabitants: dict[Room, list[User]] = defaultdict(lambda: [])
    for room, user in rooms_users_q.all():
        if user is not None:
            level_inhabitants[room].append(t.cast(User, user))
        else:
            # Ensure room is in level_inhabitants
            level_inhabitants[room]

    return TableResponse[BuildingLevelRoomRow](
        items=[
            BuildingLevelRoomRow(
                room=LinkColResponse(
                    href=url_for(".room_show", room_id=room.id),
                    title=f"{level:02d} - {room.number}",
                ),
                inhabitants=[user_button(i) for i in inhabitants],
            )
            for room, inhabitants in level_inhabitants.items()
        ]
    ).model_dump()


def get_switch_room_or_redirect(switch_room_id: int) -> Room:
    switch_room = session.session.get(Room, switch_room_id)
    if switch_room is None:
        flash(f"Raum mit ID {switch_room_id} nicht gefunden!", "error")
        abort(redirect(url_for(".overview")))
    if not switch_room.is_switch_room:
        flash("Dieser Raum ist kein Switchraum!", "error")
        abort(redirect(url_for(".room_show", room_id=switch_room_id)))
    return switch_room


@bp.route('/room/<int:switch_room_id>/patch-port/create', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def patch_port_create(switch_room_id: int) -> ResponseReturnValue:
    switch_room = get_switch_room_or_redirect(switch_room_id)

    form = PatchPortForm(switch_room=switch_room.short_name,
                         building=switch_room.building,
                         level=switch_room.level)

    def default_response() -> ResponseReturnValue:
        form_args = {
            "form": form,
            "cancel_to": url_for(
                ".room_show", room_id=switch_room_id, _anchor="patchpanel"
            ),
        }
        return render_template(
            "generic_form.html", page_title="Patch-Port erstellen", form_args=form_args
        )

    if not form.validate_on_submit():
        return default_response()

    room = Room.q.filter_by(
        building=form.building.data, level=form.level.data, number=form.room_number.data
    ).one()
    sess = session.session
    _handlers: ErrorHandlerMap = {
        PatchPortAlreadyExistsException: lambda _: form.name.errors.append(
            "Ein Patch-Port mit dieser Bezeichnung existiert bereits in diesem Zimmer."
        )
    }
    with abort_on_error(default_response, _handlers), sess.begin_nested():
        patch_port = create_patch_port(form.name.data, room, switch_room, current_user)
    sess.commit()

    flash(
        f"Der Patch-Port {patch_port.name} zum Zimmer {patch_port.room.short_name} "
        "wurde erfolgreich erstellt.",
        "success",
    )
    return redirect(url_for(".room_show", room_id=switch_room_id, _anchor="patchpanel"))


def get_patch_port_or_redirect(
    patch_port_id: int, in_switch_room: Room | None = None
) -> PatchPort:
    patch_port = session.session.get(PatchPort, patch_port_id)
    if patch_port is None:
        flash(f"Patch-Port mit ID {patch_port_id} nicht gefunden!", "error")
        abort(redirect(url_for(".overview")))
    if in_switch_room and patch_port.switch_room != in_switch_room:
        flash("Patch-Port ist nicht im Switchraum!", "error")
        abort(redirect(url_for(".room_show", room_id=in_switch_room.id)))
    return patch_port


@bp.route('/room/<int:switch_room_id>/patch-port/<int:patch_port_id>/edit', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def patch_port_edit(switch_room_id: int, patch_port_id: int) -> ResponseReturnValue:
    switch_room = get_switch_room_or_redirect(switch_room_id)
    patch_port = get_patch_port_or_redirect(patch_port_id, in_switch_room=switch_room)
    form = PatchPortForm(switch_room=switch_room.short_name,
                         name=patch_port.name,
                         building=patch_port.room.building,
                         level=patch_port.room.level,
                         room_number=patch_port.room.number)

    def default_response() -> ResponseReturnValue:
        form_args = {
            "form": form,
            "cancel_to": url_for(
                ".room_show", room_id=switch_room_id, _anchor="patchpanel"
            ),
        }
        return render_template(
            "generic_form.html",
            page_title="Patch-Port bearbeiten",
            form_args=form_args,
        )

    if not form.validate_on_submit():
        return default_response()

    room = Room.q.filter_by(
        building=form.building.data, level=form.level.data, number=form.room_number.data
    ).one()
    sess = session.session
    _handlers: ErrorHandlerMap = {
        PatchPortAlreadyExistsException: lambda _: form.name.errors.append(
            "Ein Patch-Port mit dieser Bezeichnung existiert bereits in diesem Switchraum."
        )
    }
    with abort_on_error(default_response, _handlers), sess.begin_nested():
        edit_patch_port(patch_port, form.name.data, room, current_user)
    sess.commit()

    flash("Der Patch-Port wurde erfolgreich bearbeitet.", "success")
    return redirect(url_for(".room_show", room_id=switch_room_id, _anchor="patchpanel"))


@bp.route('/room/<int:switch_room_id>/patch-port/<int:patch_port_id>/delete', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def patch_port_delete(switch_room_id: int, patch_port_id: int) -> ResponseReturnValue:
    switch_room = get_switch_room_or_redirect(switch_room_id)
    patch_port = get_patch_port_or_redirect(patch_port_id, in_switch_room=switch_room)

    form = Form()

    def default_response() -> ResponseReturnValue:
        form_args = {
            "form": form,
            "cancel_to": url_for(
                ".room_show", room_id=switch_room_id, _anchor="patchpanel"
            ),
            "submit_text": "Löschen",
            "actions_offset": 0,
        }
        return render_template(
            "generic_form.html", page_title="Patch-Port löschen", form_args=form_args
        )

    if not form.validate_on_submit():
        return default_response()

    with abort_on_error(default_response), session.session.begin_nested():
        delete_patch_port(patch_port, current_user)
    session.session.commit()

    flash("Der Patch-Port wurde erfolgreich gelöscht.", "success")
    return redirect(url_for(".room_show", room_id=switch_room_id, _anchor="patchpanel"))



def get_room_or_404(room_id: int) -> Room:
    room = session.session.get(Room, room_id)
    if room is None:
        flash(f"Raum mit id {room_id} existiert nicht", "error")
        abort(404)
    return room



@bp.route('/room/<int:room_id>', methods=['GET', 'POST'])
def room_show(room_id: int) -> ResponseReturnValue:
    room = get_room_or_404(room_id)
    form = RoomLogEntry()

    if form.validate_on_submit():
        lib.logging.log_room_event(form.message.data, current_user, room)
        flash('Kommentar hinzugefügt', 'success')
        session.session.commit()

    room_log_table = RoomLogTable(
        data_url=url_for(".room_logs_json", room_id=room.id))

    patch_port_table = PatchPortTable(data_url=url_for(".room_patchpanel_json", room_id=room.id),
                                      room_id=room_id)

    return render_template(
        "facilities/room_show.html",
        page_title=f"Raum {room.short_name}",
        room=room,
        ports=room.patch_ports,
        user_buttons=[user_button(user).model_dump() for user in room.users],
        user_histories=[
            (
                user_button(room_history_entry.user).model_dump(),
                room_history_entry.active_during.begin,
                room_history_entry.active_during.end,
            )
            for room_history_entry in room.room_history_entries
        ],
        room_log_table=room_log_table,
        patch_port_table=patch_port_table,
        form=form,
    )


@bp.route('/room/<int:room_id>/logs/json')
def room_logs_json(room_id: int) -> ResponseReturnValue:
    room = get_room_or_404(room_id)
    return TableResponse[LogTableRow](
        items=[format_room_log_entry(entry) for entry in reversed(room.log_entries)]
    ).model_dump()


@bp.route('/room/<int:room_id>/patchpanel/json')
def room_patchpanel_json(room_id: int) -> ResponseReturnValue:
    room = get_room_or_404(room_id)
    if not room.is_switch_room:
        abort(400)

    patch_ports = PatchPort.q.filter_by(switch_room=room).all()
    patch_ports = sort_ports(patch_ports)

    return TableResponse[PatchPortRow](
        items=[
            PatchPortRow(
                name=port.name,
                room=LinkColResponse(
                    href=url_for(".room_show", room_id=port.room.id),
                    title=port.room.short_name,
                ),
                switch_port=LinkColResponse(
                    href=url_for(
                        "infrastructure.switch_show",
                        switch_id=port.switch_port.switch.host_id,
                    ),
                    title=f"{port.switch_port.switch.host.name}/{port.switch_port.name}",
                )
                if port.switch_port
                else None,
                edit_link=BtnColResponse(
                    href=url_for(
                        ".patch_port_edit",
                        switch_room_id=room.id,
                        patch_port_id=port.id,
                    ),
                    title="Bearbeiten",
                    icon="fa-edit",
                    # TODO decide on a convention here
                    btn_class="btn-link",
                ),
                delete_link=BtnColResponse(
                    href=url_for(
                        ".patch_port_delete",
                        switch_room_id=room.id,
                        patch_port_id=port.id,
                    ),
                    title="Löschen",
                    icon="fa-trash",
                    btn_class="btn-link",
                ),
            )
            for port in patch_ports
        ]
    ).model_dump()


@bp.route('/json/levels')
@access.require('facilities_show')
def json_levels() -> ResponseReturnValue:
    """Endpoint for the room <select> field"""
    building_id = request.args.get("building", 0, type=int)
    levels = (
        session.session.query(Room.level.label("level"))
        .filter_by(building_id=building_id)
        .order_by(Room.level)
        .distinct()
    )
    return {"items": [entry.level for entry in levels]}


@bp.route('/json/rooms')
@access.require('facilities_show')
def json_rooms() -> ResponseReturnValue:
    """Endpoint for the room <select> field"""
    building_id = request.args.get("building", 0, type=int)
    level = request.args.get("level", 0, type=int)
    rooms = (
        session.session.query(Room.number.label("room_num"))
        .filter_by(building_id=building_id, level=level)
        .order_by(Room.number)
        .distinct()
    )
    return {"items": [entry.room_num for entry in rooms]}


@bp.route('/overcrowded', defaults={'building_id': None})
@bp.route('/overcrowded/<int:building_id>')
@nav.navigate("Mehrfachbelegungen", icon='fa-people-arrows')
def overcrowded(building_id: int) -> ResponseReturnValue:
    page_title = "Mehrfachbelegungen"
    if building_id:
        building = determine_building_or_404(id=building_id)
        page_title = f"Mehrfachbelegungen {building.short_name}"

    return render_template(
        "facilities/room_overcrowded.html",
        page_title=page_title,
        room_table=RoomOvercrowdedTable(
            data_url=url_for('.overcrowded_json', building_id=building_id)),
    )

@bp.route('/overcrowded/json', defaults={'building_id': None})
@bp.route('/overcrowded/<int:building_id>/json')
def overcrowded_json(building_id: int) -> ResponseReturnValue:
    return TableResponse[RoomOvercrowdedRow](
        items=[
            RoomOvercrowdedRow(
                room=LinkColResponse(
                    title="{} / {:02d} / {}".format(
                        inhabitants[0].room.building.short_name,
                        inhabitants[0].room.level,
                        inhabitants[0].room.number,
                    ),
                    href=url_for(
                        "facilities.room_show", room_id=inhabitants[0].room.id
                    ),
                ),
                inhabitants=[user_button(user) for user in inhabitants],
            )
            for inhabitants in get_overcrowded_rooms(building_id).values()
        ]
    ).model_dump()


@bp.route('address/<string:type>')
def addresses(type: str) -> ResponseReturnValue:
    try:
        entity = get_address_entity(type)
    except ValueError as e:
        return {"errors": [e.args[0]]}, 404

    query: str = request.args.get('query', '').replace('%', '%%')
    limit: int = request.args.get('limit', 10, type=int)

    address_q = address_entity_search_query(query, entity, session.session, limit)

    return {"items": [str(row[0]) for row in address_q.all()]}
