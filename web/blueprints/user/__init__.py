# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.user
    ~~~~~~~~~~~~~~

    This module defines view functions for /user

    :copyright: (c) 2012 by AG DSN.
"""
import operator
import re
import typing as t
from datetime import timedelta
from functools import partial
from itertools import chain
from typing import TypeVar, Callable, cast

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    session as flask_session,
    make_response,
)
from flask_login import current_user
from markupsafe import Markup

import pycroft.lib.search
import pycroft.lib.stats
from pycroft import lib, config
from pycroft.exc import PycroftException
from pycroft.helpers import utc
from pycroft.helpers.i18n import gettext, deferred_gettext
from pycroft.helpers.interval import closed, closedopen, starting_from
from pycroft.helpers.net import ip_regex, mac_regex
from pycroft.lib.facilities import get_room
from pycroft.lib.logging import log_user_event
from pycroft.lib.membership import make_member_of, remove_member_of
from pycroft.lib.traffic import get_users_with_highest_traffic
from pycroft.lib.user import encode_type1_user_id, encode_type2_user_id, \
    traffic_history, generate_user_sheet, get_blocked_groups, \
    finish_member_request, send_confirmation_email, \
    delete_member_request, get_member_requests, \
    get_possible_existing_users_for_pre_member, \
    send_member_request_merged_email, can_target, edit_address
from pycroft.lib.user_deletion import get_archivable_members
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.swdd import Tenancy
from pycroft.model.user import User, Membership, BaseUser, RoomHistoryEntry
from web.blueprints.access import BlueprintAccess
from web.blueprints.helpers.exception import handle_errors
from web.blueprints.helpers.form import refill_room_data
from web.blueprints.helpers.user import get_user_or_404, get_pre_member_or_404
from web.blueprints.host.tables import HostTable
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.task.tables import TaskTable
from web.blueprints.user.forms import (
    UserSearchForm,
    UserCreateForm,
    UserLogEntry,
    UserAddGroupMembership,
    UserMoveForm,
    UserEditForm,
    UserSuspendForm,
    UserMoveOutForm,
    UserEditGroupMembership,
    UserResetPasswordForm,
    UserMoveInForm,
    PreMemberEditForm,
    PreMemberDenyForm,
    PreMemberMergeForm,
    PreMemberMergeConfirmForm,
    UserEditAddressForm,
    NonResidentUserCreateForm,
    GroupMailForm,
)
from web.table.table import (
    TableResponse,
    LinkColResponse,
    datetime_format_pydantic,
    BtnColResponse,
    date_format_pydantic,
)
from .log import formatted_user_hades_logs
from .tables import (
    MembershipTable,
    SearchTable,
    TrafficTopTable,
    RoomHistoryTable,
    PreMemberTable,
    TenancyTable,
    ArchivableMembersTable,
    TrafficTopRow,
    UserSearchRow,
    MembershipRow,
    TenancyRow,
    RoomHistoryRow,
    PreMemberRow,
    TextWithBooleanColResponse,
    ArchivableMemberRow,
)
from ..helpers.log_tables import (
    LogTableExtended,
    LogTableSpecific,
    LogType,
    LogTableRow,
)
from ..finance.tables import FinanceTable, FinanceTableSplitted
from ..helpers.log import format_user_log_entry, format_room_log_entry, \
    format_task_log_entry
from ...template_filters import date_filter, datetime_filter

bp = Blueprint('user', __name__)
access = BlueprintAccess(bp, required_properties=['user_show'])
nav = BlueprintNavigation(bp, "Nutzer", icon='fa-user', blueprint_access=access)


@bp.route('/')
@nav.navigate("Übersicht", weight=1)
def overview():
    stats = pycroft.lib.stats.overview_stats()
    entries = [{"title": "Mitgliedschaftsanfragen",
                "href": url_for('.member_requests'),
                "number": stats.member_requests},
               {"title": "Nutzer in Datenbank",
                "href": None,
                "number": stats.users_in_db},
               {"title": "Mitglieder",
                "href": None,
                "number": stats.members},
               {"title": "Nicht bezahlt",
                "href": None,
                "number": stats.not_paid_all},
               {"title": "Nicht bezahlt (Mitglieder)",
                "href": None,
                "number": stats.not_paid_members}]
    return render_template("user/user_overview.html", entries=entries,
                           traffic_top_table=TrafficTopTable(
                                data_url=url_for("user.json_users_highest_traffic"),
                                table_args={'data-page-size': 10,
                                            'data-search': 'false'},
                           ))


def make_pdf_response(pdf_data, filename, inline=True):
    """Turn pdf data into a response with appropriate headers.

    Content-Type: application/pdf
    Content-Disposition: (inline|attachment); filename="<filename>"
    """
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    disposition = "{}; filename={}".format('inline' if inline else 'attachment',
                                           filename)
    response.headers['Content-Disposition'] = disposition
    return response


@bp.route('/user_sheet')
def user_sheet():
    """Deliver the datasheet stored in the session"""
    try:
        sheet_id = flask_session['user_sheet']
    except KeyError:
        flash("No user sheet referenced in your session", 'warning')
        abort(404)
    pdf_data = lib.user.get_user_sheet(sheet_id)
    if not pdf_data:
        flash("The referenced user sheet does not exist."
              " Perhaps it has already expired?", 'error')
        abort(404)

    return make_pdf_response(pdf_data, filename='user_sheet.pdf')


@bp.route('/<int:user_id>/datasheet')
def static_datasheet(user_id):
    """Deliver an on-the-fly datasheet without the password.

    Useful for testing the layout itself.
    """
    user = User.get(user_id)
    if user is None:
        abort(404)

    return make_pdf_response(generate_user_sheet(True, False, user, plain_user_password="********",
                                                 generation_purpose='reprint'),
                             filename=f'user_sheet_plain_{user_id}.pdf')


@bp.route('/json/traffic-usage')
def json_users_highest_traffic():
    return TableResponse[TrafficTopRow](
        items=[
            TrafficTopRow(
                id=user.id,
                name=user.name,
                traffic_for_days=user.traffic_for_days,
                url=LinkColResponse(
                    href=url_for(".user_show", user_id=user.id), title=user.name
                ),
            )
            for user in get_users_with_highest_traffic(7, 20)
        ]
    ).model_dump()


T = TypeVar('T')
def coalesce_none(value: T | None, *none_values: T) -> T | None:
    return None if any(value == n for n in none_values) else value


U = TypeVar('U')
def and_then(val: T | None, map: Callable[[T], U]) -> U | None:
    return map(val) if val is not None else None


@bp.route('/json/search')
def json_search():
    g = request.args.get
    try:
        user_id = and_then(coalesce_none(g('id'), ""), int)
        name = g('name')
        login = g('login')
        mac = g('mac')
        ip_address = g('ip_address')
        property_group_id = and_then(coalesce_none(g('property_group_id'), "", "__None"), int)
        building_id = and_then(coalesce_none(g('building_id'), "", "__None"), int)
        email = g('email')
        person_id = and_then(coalesce_none(g('person_id'), ""), int)
        query = g("query")
    except (TypeError, ValueError):
        return abort(400)
    ip_invalid = ip_address and not re.match(ip_regex, ip_address)
    mac_invalid = mac and not re.match(mac_regex, mac)
    if ip_invalid or mac_invalid:
        return abort(400)

    search_query = lib.search.user_search_query(
        user_id, name, login, mac, ip_address, property_group_id, building_id, email, person_id,
        query
    )

    return TableResponse[UserSearchRow](
        items=[
            UserSearchRow(
                id=found_user.id,
                name=found_user.name,
                url=LinkColResponse(
                    href=url_for(".user_show", user_id=found_user.id),
                    title=found_user.name,
                ),
                login=found_user.login,
                room_id=found_user.room_id if found_user.room_id is not None else None,
            )
            for found_user in (
                search_query.all() if search_query.count() < User.q.count() else []
            )
        ]
    ).model_dump()


def infoflags(user):
    user_status = lib.user.status(user)
    return [
        {'title': "Mitglied", 'icon': "user", 'val': user_status.member},
        {'title': "LAN-Zugang", 'icon': "network-wired", 'val': user_status.network_access},
        {'title': "WLAN-Zugang", 'icon': "wifi", 'val': user_status.wifi_access},
        {'title': "Bezahlt", 'icon': "euro-sign", 'val': user_status.account_balanced},
        {'title': "Verstoßfrei", 'icon': "exclamation-triangle", 'val': not user_status.violation},
        {'title': "LDAP", 'icon': "cloud", 'val': user_status.ldap},
    ]


@bp.route('/<int:user_id>/', methods=['GET', 'POST'])
def user_show(user_id):
    user = get_user_or_404(user_id)
    room = user.room
    form = UserLogEntry()

    if form.validate_on_submit():
        lib.logging.log_user_event(form.message.data,
                                   author=current_user,
                                   user=user)
        session.session.commit()
        flash('Kommentar hinzugefügt', 'success')

    balance = user.account.balance
    _log_endpoint = partial(url_for, ".user_show_logs_json", user_id=user.id)
    _membership_endpoint = partial(url_for, ".user_show_groups_json", user_id=user.id)
    _finance_table_kwargs = {
        'data_url': url_for("finance.accounts_show_json", account_id=user.account_id),
        'user_id': user.id,
        'table_args': {'data-page-size': 5},
        'inverted': True,
        'saldo': balance,
    }

    is_blocked = False

    for group in get_blocked_groups():
        if user.member_of(group):
            is_blocked = True

    user_not_there = not user.member_of(config.member_group)

    try:
        if flask_session['user_sheet'] and lib.user.get_user_sheet(flask_session['user_sheet']):
            flash(Markup('Es ist ein <a href="{}" target="_blank">Nutzerdatenblatt</a> verfügbar!'.format(
                url_for('.user_sheet'))
            ))
    except KeyError:
        pass

    return render_template(
        'user/user_show.html',
        # Q: Can ports of a room point to different access switches?
        user=user,
        user_not_there=user_not_there,
        user_id_new=encode_type2_user_id(user.id),
        user_id_old=encode_type1_user_id(user.id),
        balance=-balance,
        hosts_rooms={host.room for host in user.hosts},
        log_table_all=LogTableExtended(data_url=_log_endpoint()),
        log_table_user=LogTableSpecific(data_url=_log_endpoint(logtype="user")),
        log_table_room=LogTableSpecific(data_url=_log_endpoint(logtype="room")),
        log_table_hades=LogTableSpecific(data_url=_log_endpoint(logtype="hades")),
        log_table_tasks=LogTableSpecific(data_url=_log_endpoint(logtype="tasks")),
        membership_table_all=MembershipTable(
            user_id=user.id,
            data_url=_membership_endpoint(),
        ),
        membership_table_active=MembershipTable(
            user_id=user.id,
            data_url=_membership_endpoint(group_filter="active"),
        ),
        host_table=HostTable(data_url=url_for("host.user_hosts_json", user_id=user.id),
                             user_id=user.id),
        task_table=TaskTable(data_url=url_for("task.json_tasks_for_user", user_id=user.id),
                             hidden_columns=['user']),
        finance_table_regular=FinanceTable(**_finance_table_kwargs),
        finance_table_splitted=FinanceTableSplitted(**_finance_table_kwargs),
        room=room,
        form=form,
        flags=infoflags(user),
        json_url=url_for("finance.accounts_show_json",
                         account_id=user.account_id),
        is_blocked=is_blocked,
        granted_properties=sorted(p.property_name for p in user.current_properties),
        revoked_properties=sorted(
            p.property_name
            for p in set(user.current_properties_maybe_denied) -set(user.current_properties)
        ),
        room_history_table=RoomHistoryTable(
            data_url=url_for(".room_history_json", user_id=user.id)
        ),
        tenancy_table=TenancyTable(
            data_url=url_for(".tenancies_json", user_id=user.id)
        ),
        tabs=[
            {
                'id': 'hosts',
                'icon': 'fa-laptop',
                'name': 'Hosts',
                'badge': len(user.hosts)
            },
            {
                'id': 'tasks',
                'icon': 'fa-clipboard-check',
                'name': 'Tasks',
                'badge': len(user.tasks),
                'badge_color': '#d9534f' if len(user.tasks) > 0 else None
            },
            {
                'id': 'logs',
                'icon': 'fa-list-ul',
                'name': 'Logs',
                'badge': len(user.log_entries)
            },
            {
                'id': 'traffic',
                'icon': 'fa-chart-area',
                'name': 'Traffic',
            },
            {
                'id': 'finance',
                'icon': 'fa-euro-sign',
                'name': 'Finanzen',
            },
            {
                'id': 'groups',
                'icon': 'fa-users-cog',
                'name': 'Gruppen',
                'badge': len(user.active_memberships())
            },
            {
                'id': 'room_history',
                'icon': 'fa-history',
                'name': 'Wohnorte',
                'badge': len(user.room_history_entries)
            },
            {
                'id': 'tenancies',
                'icon': 'fa-file-signature',
                'name': 'Mietverträge',
                'badge': len(user.tenancies),
                'disabled': len(user.tenancies) == 0,
            },
        ]
    )


@bp.route("/<int:user_id>/account")
def user_account(user_id):
    user = get_user_or_404(user_id)
    return redirect(url_for("finance.accounts_show",
                            account_id=user.account_id))


def _iter_user_logs(user: User, logtype: LogType) -> t.Iterator[LogTableRow]:
    if logtype in ["user", "all"]:
        yield from (format_user_log_entry(e) for e in user.log_entries)
    if logtype in ["room", "all"] and user.room:
        yield from (format_room_log_entry(e) for e in user.room.log_entries)
    if logtype in ["tasks", "all"]:
        yield from (format_task_log_entry(e) for e in user.task_log_entries)
    if logtype in ["hades", "all"]:
        yield from formatted_user_hades_logs(user)


@bp.route("/<int:user_id>/logs")
@bp.route("/<int:user_id>/logs/<logtype>")
def user_show_logs_json(user_id, logtype="all"):
    user = get_user_or_404(user_id)

    logs = _iter_user_logs(user, logtype)

    def sort_key(l: LogTableRow) -> int | None:
        return l.created_at.timestamp

    return TableResponse[LogTableRow](
        items=sorted(logs, key=sort_key, reverse=True)
    ).model_dump()


@bp.route("/<int:user_id>/groups")
@bp.route("/<int:user_id>/groups/<group_filter>")
def user_show_groups_json(user_id, group_filter="all"):
    active_groups_only = group_filter == "active"
    memberships: list[tuple[Membership, list[str], list[str]]] = \
        lib.membership.user_memberships_query(user_id, active_groups_only)

    return TableResponse[MembershipRow](
        items=[
            MembershipRow(
                group_name=membership.group.name,
                begins_at=datetime_format_pydantic(
                    membership.active_during.begin,
                    default="",
                    formatter=datetime_filter,
                ),
                ends_at=datetime_format_pydantic(
                    membership.active_during.end, default="", formatter=datetime_filter
                ),
                grants=granted,
                denies=denied,
                active=(active := (session.utcnow() in membership.active_during)),
                actions=[
                    BtnColResponse(
                        href=url_for(
                            ".edit_membership",
                            user_id=user_id,
                            membership_id=membership.id,
                        ),
                        title="Bearbeiten",
                        icon="fa-edit",
                        btn_class="btn-link",
                    ),
                    BtnColResponse(
                        href=url_for(
                            ".end_membership",
                            user_id=user_id,
                            membership_id=membership.id,
                        ),
                        title="Beenden",
                        icon="fa-power-off",
                        btn_class="btn-link",
                    )
                    if active
                    else {},
                ],
            )
            for membership, granted, denied in memberships
        ]
    ).model_dump()


@bp.route('/<int:user_id>/add_membership', methods=['GET', 'Post'])
@access.require('groups_change_membership')
def add_membership(user_id):
    user = get_user_or_404(user_id)
    form = UserAddGroupMembership()

    if form.validate_on_submit():
        if form.begins_at.date.data:
            begins_at = utc.with_min_time(form.begins_at.date.data)
        else:
            begins_at = session.utcnow()
        if not form.ends_at.unlimited.data:
            ends_at = utc.with_min_time(form.ends_at.date.data)
        else:
            ends_at = None

        try:
            make_member_of(user, form.group.data, current_user,
                       closed(begins_at, ends_at))
        except PermissionError:
            session.session.rollback()
            flash("Du hast keine Berechtigung, diese Mitgliedschaft hinzuzufügen.", 'error')
            return abort(403)

        session.session.commit()
        flash('Nutzer wurde der Gruppe hinzugefügt.', 'success')

        return redirect(url_for(".user_show",
                                user_id=user_id,
                                _anchor='groups'))

    return render_template('user/add_membership.html',
        page_title=f"Neue Gruppenmitgliedschaft für Nutzer {user_id}",
        user_id=user_id, form=form)


@bp.route('/<int:user_id>/end_membership/<int:membership_id>')
@access.require('groups_change_membership')
def end_membership(user_id, membership_id):
    user = get_user_or_404(user_id)
    membership = Membership.get(membership_id)

    if membership is None:
        flash(f"Gruppenmitgliedschaft mit ID {membership_id} existiert nicht!", 'error')
        abort(404)

    if membership.user.id != user_id:
        flash(f"Gruppenmitgliedschaft {membership.id} gehört nicht zu Nutzer {user_id}!", 'error')
        return abort(404)

    try:
        remove_member_of(user, membership.group, current_user, starting_from(session.utcnow()))
    except PermissionError:
        session.session.rollback()
        flash("Du hast keine Berechtigung, diese Mitgliedschaft zu beenden.", 'error')
        return abort(403)


    session.session.commit()
    flash('Mitgliedschaft in Gruppe beendet', 'success')
    return redirect(url_for(".user_show",
                            user_id=membership.user_id,
                            _anchor='groups'))


@bp.route('/<int:user_id>/traffic/json')
@bp.route('/<int:user_id>/traffic/json/<int:days>')
def json_trafficdata(user_id, days=7):
    """Generate a JSON file to use with traffic and credit graphs.

    :param user_id:
    :param days: optional amount of days to be included
    :return:
    """
    interval = timedelta(days=days)
    utcnow = session.utcnow()
    return [
        e.__dict__
        for e in traffic_history(user_id, utcnow - interval + timedelta(days=1), utcnow)
    ]


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate("Anlegen (Extern/IBR)", weight=4, icon="fa-plus-square")
# TODO: Namen aendern
@access.require('user_change')
def create():
    form = UserCreateForm(property_groups=[config.member_group])

    def default_response():
        # TODO we should do this across the `web` package.  See #417
        return render_template('user/user_create.html', form=form), 400 \
            if form.is_submitted() else 200

    if not form.validate_on_submit():
        return default_response()
    room: Room = get_room(building_id=form.building.data.id, level=form.level.data,
                          room_number=form.room_number.data)
    if not room:
        flash("Raum scheint nicht zu existieren…", 'error')
        return default_response()

    try:
        with handle_errors(session.session):
            new_user, plain_password = lib.user.create_user(
                name=form.name.data,
                login=form.login.data,
                processor=current_user,
                email=form.email.data,
                birthdate=form.birthdate.data,
                groups=form.property_groups.data,
                address=room.address,
                send_confirm_mail=True,
            )
            lib.user.move_in(
                user=new_user,
                building_id=form.building.data.id, level=form.level.data,
                room_number=form.room_number.data,
                mac=form.mac.data,
                processor=current_user,
                host_annex=form.annex.data,
                # memberships have already been initiated by `create_user`
                # (`form.property_groups`)
                begin_membership=False,
            )
            plain_wifi_password = lib.user.maybe_setup_wifi(
                new_user,
                processor=current_user
            )
            sheet = lib.user.store_user_sheet(
                True, wifi=(plain_wifi_password is not None),
                user=new_user,
                plain_user_password=plain_password,
                plain_wifi_password=plain_wifi_password or ''
            )
            session.session.commit()
    except PycroftException:
        return default_response()

    flask_session['user_sheet'] = sheet.id
    flash(Markup('Benutzer angelegt.'), 'success')
    return redirect(url_for('.user_show', user_id=new_user.id))


@bp.route('/create_non_resident', methods=['GET', 'POST'])
@nav.navigate("Anlegen (freie Adresseingabe)", weight=5, icon="far fa-plus-square")
# TODO: Namen aendern
@access.require('user_change')
def create_non_resident():
    form = NonResidentUserCreateForm(property_groups=[config.member_group])

    def default_response():
        # TODO we should do this across the `web` package.  See #417
        return render_template('user/user_create.html', form=form), 400 \
            if form.is_submitted() else 200

    if not form.validate_on_submit():
        return default_response()
    try:
        with handle_errors(session.session):
            address = lib.user.get_or_create_address(**form.address_kwargs)
            new_user, plain_password = lib.user.create_user(
                name=form.name.data,
                login=form.login.data,
                processor=current_user,
                email=form.email.data,
                birthdate=form.birthdate.data,
                groups=form.property_groups.data,
                address=address,
                send_confirm_mail=True,
            )
            plain_wifi_password = lib.user.maybe_setup_wifi(new_user, processor=current_user)
            sheet = lib.user.store_user_sheet(
                True,
                wifi=(plain_wifi_password is not None),
                user=new_user,
                plain_user_password=plain_password,
                plain_wifi_password=plain_wifi_password or ''
            )
            session.session.commit()
    except PycroftException:
        return default_response()

    flask_session['user_sheet'] = sheet.id
    flash(Markup('Benutzer angelegt.'), 'success')
    return redirect(url_for('.user_show', user_id=new_user.id))


@bp.route('/<int:user_id>/move', methods=['GET', 'POST'])
@access.require('user_change')
def move(user_id):
    user = get_user_or_404(user_id)
    form = UserMoveForm()

    def default_response(refill_form_data=False):
        if not form.is_submitted() or refill_form_data:
            if user.room is not None:
                refill_room_data(form, user.room)
        return render_template('user/user_move.html', user_id=user_id, form=form)

    if not form.validate_on_submit():
        return default_response()

    selected_room = Room.q.filter_by(
        number=form.room_number.data,
        level=form.level.data,
        building_id=form.building.data.id
    ).one()
    if user.room == selected_room:
        flash("Nutzer muss in anderes Zimmer umgezogen werden!", "error")
        return default_response(refill_form_data=True)

    when = form.get_execution_time(now=session.utcnow())

    try:
        with handle_errors(session.session):
            lib.user.move(
                user=user,
                building_id=form.building.data.id,
                level=form.level.data,
                room_number=form.room_number.data,
                processor=current_user,
                comment=form.comment.data,
                when=when
            )
            session.session.commit()
            if when > session.utcnow():
                flash('Der Umzug wurde vorgemerkt.', 'success')
                return redirect(url_for('.user_show', user_id=user.id))
            flash('Benutzer umgezogen', 'success')

            sheet = lib.user.store_user_sheet(True, False, user=user,
                                              plain_user_password='********',
                                              generation_purpose='user moved')
            session.session.commit()
            flask_session['user_sheet'] = sheet.id
            return redirect(url_for('.user_show', user_id=user.id))
    except PycroftException:
        return default_response()


@bp.route('/<int:user_id>/edit_membership/<int:membership_id>', methods=['GET', 'POST'])
@access.require('groups_change_membership')
def edit_membership(user_id, membership_id):
    membership: Membership = Membership.get(membership_id)

    if membership is None:
        flash("Gruppenmitgliedschaft mit ID {} existiert nicht!".format(
        membership_id), 'error')
        abort(404)

    if membership.group.permission_level > current_user.permission_level:
        flash("Eine Bearbeitung von Gruppenmitgliedschaften für Gruppen mit "
              "höherem Berechtigungslevel ist nicht möglich.", 'error')
        abort(403)

    membership_data = {}
    if request.method == 'GET':
        membership_data = {
            "begins_at": (beg := membership.active_during.begin) and beg.date(),
            "ends_at": {"unlimited": membership.active_during.end is None,
                        "date": (end := membership.active_during.end) and end.date()}
        }

    form = UserEditGroupMembership(**membership_data)

    if form.validate_on_submit():
        membership.active_during = closedopen(
            utc.with_min_time(form.begins_at.data),
            None if form.ends_at.unlimited.data else utc.with_min_time(form.ends_at.date.data),
        )

        message = deferred_gettext("Edited the membership of group '{group}'. During: {during}")\
            .format(group=membership.group.name, during=membership.active_during)\
            .to_json()
        lib.logging.log_user_event(message, current_user, membership.user)
        session.session.commit()
        flash('Gruppenmitgliedschaft bearbeitet', 'success')
        return redirect(url_for('.user_show',
                                user_id=membership.user_id,
                                _anchor='groups'))

    return render_template('user/user_edit_membership.html',
                           page_title=("Mitgliedschaft {} für "
                                       "{} bearbeiten".format(
                                            membership.group.name,
                                            membership.user.name)),
                           membership_id=membership_id,
                           user=membership.user,
                           form=form)


@bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@access.require('user_change')
def edit_user(user_id):
    user = get_user_or_404(user_id)
    form = UserEditForm(obj=user, person_id=user.swdd_person_id)

    if form.validate_on_submit():
        success = True

        edited_user = lib.user.edit_name(user, form.name.data, current_user)
        try:
            edited_user = lib.user.edit_email(edited_user, form.email.data,
                                          form.email_forwarded.data, current_user)
        except PermissionError:
            flash(gettext("Keine Berechtigung die Email dieses Nutzers zu ändern."))
            session.session.rollback()
            return abort(403)
        edited_user = lib.user.edit_birthdate(edited_user, form.birthdate.data,
                                              current_user)

        if edited_user.swdd_person_id != form.person_id.data:
            if form.person_id.data is not None and \
               User.q.filter_by(swdd_person_id=form.person_id.data).filter(User.id != user.id).first():
                form.person_id.errors.append("Diese Debitorennummer wird bereits verwendet!")
                success = False
            else:
                edited_user = lib.user.edit_person_id(edited_user, form.person_id.data,
                                                      current_user)

        if edited_user.swdd_person_id is not None:
            if not Tenancy.q.filter_by(person_id=edited_user.swdd_person_id).first():
                flash("Zu der angegebenen Debitorennummer konnten keine Mietverträge gefunden "
                      "werden!", "warning")

        if success:
            session.session.commit()

            flash('Änderungen gespeichert', 'success')
            return redirect(url_for('.user_show', user_id=edited_user.id))

    return render_template('user/user_edit.html', user_id=user_id,
        form=form)

@bp.route('/<int:user_id>/edit_address', methods=['GET', 'POST'])
@access.require('user_change')
def edit_user_address(user_id: int):
    user = get_user_or_404(user_id)
    form = UserEditAddressForm()
    user_show_url = url_for('.user_show', user_id=user.id)
    if form.validate_on_submit():
        edit_address(
            user=user,
            processor=current_user,
            street=form.address_street.data,
            number=form.address_number.data,
            addition=form.address_addition.data,
            zip_code=form.address_zip_code.data,
            city=form.address_city.data,
            state=form.address_state.data,
            country=form.address_country.data,
        )
        session.session.commit()
        return redirect(user_show_url)

    if not form.is_submitted():
        form.set_defaults_from_adress(user.address)

    if user.room and not user.has_custom_address:
        flash(gettext("Nutzer wohnt bereits im Raum {}."
                      " Über dieses Formular wird die offizielle Adresse des Nutzers geändert,"
                      " ohne ihn um- oder auszuziehen.")
              .format(user.room.short_name),
              'warning')

    form_args = {
        'form': form,
        'cancel_to': user_show_url,
        # 'submit_text': 'Zusammenführen',
        'form_render_mode': 'basic',
        'field_render_mode': 'basic',
    }
    return render_template(
        'generic_form.html',
        page_title="Adresse bearbeiten", form_args=form_args
    )


@bp.route('/search', methods=['GET', 'POST'])
@nav.navigate("Suchen", weight=3, icon="fa-search")
def search():
    form = UserSearchForm()

    return render_template(
        'user/user_search.html',
        form=form,
        search_table=SearchTable(data_url=url_for(".json_search"))
    )


@bp.route('/<int:user_id>/reset_password', methods=['GET', 'POST'])
@access.require('user_change')
def reset_password(user_id):
    form = UserResetPasswordForm()
    my_user = get_user_or_404(user_id)

    if not can_target(my_user, current_user):
        flash(gettext("Keine Berechtigung das Passwort dieses Nutzers zu ändern."))
        return abort(403)

    if form.validate_on_submit():
        try:
            plain_password = lib.user.reset_password(my_user, processor=current_user)
        except PermissionError:
            flash(gettext("Keine Berechtigung das Passwort dieses Nutzers zu ändern."))
            session.session.rollback()
            return abort(403)

        sheet = lib.user.store_user_sheet(True, False, user=my_user,
                                          plain_user_password=plain_password,
                                          generation_purpose='password reset')
        session.session.commit()

        flask_session['user_sheet'] = sheet.id
        flash(Markup('Passwort erfolgreich zurückgesetzt.'),
              'success')
        return redirect(url_for('.user_show', user_id=user_id))
    return render_template('user/user_reset_password.html', form=form, user_id=user_id)


@bp.route('/<int:user_id>/reset_wifi_password', methods=['GET', 'POST'])
@access.require('user_change')
def reset_wifi_password(user_id):
    form = UserResetPasswordForm()
    myUser = User.get(user_id)
    if form.validate_on_submit():
        plain_password = lib.user.reset_wifi_password(myUser, processor=current_user)
        sheet = lib.user.store_user_sheet(False, True, user=myUser,
                                          plain_wifi_password=plain_password,
                                          generation_purpose='password reset')

        session.session.commit()

        flask_session['user_sheet'] = sheet.id
        flash(Markup('WiFi-Passwort erfolgreich zurückgesetzt.'),
              'success')
        return redirect(url_for('.user_show', user_id=user_id))
    return render_template('user/user_reset_wifi_password.html', form=form, user_id=user_id)


@bp.route('/<int:user_id>/block', methods=['GET', 'POST'])
@access.require('user_change')
def block(user_id):
    form = UserSuspendForm()
    myUser = get_user_or_404(user_id)
    if form.validate_on_submit():
        if form.ends_at.unlimited.data:
            ends_at = None
        else:
            ends_at = utc.with_min_time(form.ends_at.date.data, )

        try:
            during = closedopen(session.utcnow(), ends_at)
            lib.user.block(
                user=myUser,
                reason=form.reason.data,
                processor=current_user,
                during=during,
                violation=form.violation.data)
            session.session.commit()
        except ValueError as e:
            flash(str(e), 'error')
        else:
            flash('Nutzer gesperrt.', 'success')
            return redirect(url_for('.user_show', user_id=user_id))
    return render_template('user/user_block.html', form=form, user_id=user_id)


@bp.route('/<int:user_id>/unblock', methods=['GET', 'POST'])
@access.require('user_change')
def unblock(user_id):
    user = get_user_or_404(user_id)

    try:
        lib.user.unblock(
            user=user,
            processor=current_user)
        session.session.commit()
    except ValueError as e:
        flash(str(e), 'error')
    else:
        flash('Nutzer entsperrt.', 'success')
        return redirect(url_for('.user_show', user_id=user_id))


@bp.route('/<int:user_id>/move_out', methods=['GET', 'POST'])
@access.require('user_change')
def move_out(user_id):
    form = UserMoveOutForm()
    user = get_user_or_404(user_id)

    def default_response():
        return render_template('user/user_move_out.html', form=form, user_id=user_id), \
            400 if form.is_submitted() else 200

    if not user.room:
        flash(f"Nutzer {user_id} ist aktuell nirgends eingezogen!", 'error')
        abort(404)
    if not form.is_submitted():
        form.end_membership.data = True
        return default_response()
    if not form.validate():
        return default_response()

    when = session.utcnow() if form.now.data else utc.with_min_time(form.when.data)
    try:
        with handle_errors(session.session):
            lib.user.move_out(
                user=user,
                comment=form.comment.data,
                processor=current_user,
                when=session.utcnow() if form.now.data else utc.with_min_time(form.when.data),
                end_membership=form.end_membership.data
            )
            session.session.commit()
    except PycroftException:
        return default_response()

    if when > session.utcnow():
        flash("Der Auszug wurde vorgemerkt.", "success")
    else:
        flash('Benutzer ausgezogen.', 'success')
    return redirect(url_for('.user_show', user_id=user.id))


@bp.route('/<int:user_id>/move_in', methods=['GET', 'POST'])
@access.require('user_change')
def move_in(user_id):
    form = UserMoveInForm()
    user = get_user_or_404(user_id)

    def default_response():
        return render_template('user/user_move_in.html', form=form, user_id=user_id), \
               400 if form.is_submitted() else 200

    if user.room is not None:
        flash(f"Nutzer {user_id} ist nicht ausgezogen!", 'error')
        abort(404)

    if not form.is_submitted():
        form.birthdate.data = user.birthdate
        form.begin_membership.data = True
        return default_response()

    if not form.validate():
        return default_response()

    when = session.utcnow() if form.now.data else utc.with_min_time(form.when.data)
    try:
        with handle_errors(session.session):
            lib.user.move_in(
                user=user,
                building_id=form.building.data.id,
                level=form.level.data,
                room_number=form.room_number.data,
                mac=form.mac.data,
                birthdate=form.birthdate.data,
                begin_membership=form.begin_membership.data,
                processor=current_user,
                when=when,
            )
            session.session.commit()
    except PycroftException:
        return default_response()

    if when > session.utcnow():
        flash("Der Einzug wurde vorgemerkt.", 'success')
    else:
        flash("Benutzer eingezogen.", 'success')
    return redirect(url_for('.user_show', user_id=user_id))


@bp.route('<int:user_id>/json/room-history')
def room_history_json(user_id):
    user = get_user_or_404(user_id)
    return TableResponse[RoomHistoryRow](
        items=[
            RoomHistoryRow(
                begins_at=date_format_pydantic(
                    history_entry.active_during.begin, formatter=date_filter
                ),
                ends_at=date_format_pydantic(
                    history_entry.active_during.end, formatter=date_filter
                ),
                room=T.room.value(
                    href=url_for("facilities.room_show", room_id=history_entry.room_id),
                    title=history_entry.room.short_name,
                ),
            )
            for history_entry in cast(list[RoomHistoryEntry], user.room_history_entries)
        ]
    ).model_dump()


@bp.route('<int:user_id>/json/tenancies')
def tenancies_json(user_id):
    user = get_user_or_404(user_id)
    return TableResponse[TenancyRow](
        items=[
            TenancyRow(
                begins_at=date_format_pydantic(
                    tenancy.mietbeginn, formatter=date_filter
                ),
                ends_at=date_format_pydantic(tenancy.mietende, formatter=date_filter),
                room=LinkColResponse(
                    href=url_for("facilities.room_show", room_id=tenancy.room.id)
                    if tenancy.room
                    else "#",
                    title=tenancy.room.short_name
                    if tenancy.room
                    else tenancy.vo_suchname,
                ),
                status=tenancy.status.name,
            )
            for tenancy in user.tenancies
        ]
    ).model_dump()


@bp.route('member-requests')
@nav.navigate("Mitgliedschaftsanfragen", weight=2, icon="fa-user-clock")
def member_requests():
    return render_template("user/member_requests.html",
                           page_title="Mitgliedschaftsanfragen",
                           pre_member_table=PreMemberTable(
                               data_url=url_for('.member_requests_json')
                           ))


@bp.route("member-request/<int:pre_member_id>/edit", methods=['GET', 'POST'])
def member_request_edit(pre_member_id: int):
    prm = get_pre_member_or_404(pre_member_id)

    form = PreMemberEditForm(
        name=prm.name,
        login=prm.login,
        building=prm.room.building if prm.room else None,
        level=prm.room.level if prm.room else None,
        room_number=prm.room.number if prm.room else None,
        email=prm.email,
        move_in_date=prm.move_in_date,
        birthdate=prm.birthdate,
        person_id=prm.swdd_person_id,
    )

    if form.validate_on_submit():
        old_email = prm.email

        prm.name = form.name.data
        prm.login = form.login.data
        prm.email = form.email.data
        prm.move_in_date = form.move_in_date.data
        prm.birthdate = form.birthdate.data

        if prm.swdd_person_id != form.person_id.data:
            if form.person_id.data is None:
                prm.swdd_person_id = form.person_id.data
            else:
                tenancy = Tenancy.q.filter_by(person_id=form.person_id.data).first()

                if tenancy is not None:
                    prm.swdd_person_id = form.person_id.data
                else:
                    form.person_id.errors.append("Zu der angegebenen Debitorennummer konnten keine Verträge gefunden werden!",)

        room = Room.q.filter_by(building=form.building.data, level=form.level.data,
                                number=form.room_number.data).first()

        prm.room = room

        session.session.commit()

        if old_email != prm.email:
            send_confirmation_email(prm)

            flash("Es wurde eine neue Bestätigungsmail verschickt!", "warning")

            session.session.commit()

        flash("Änderungen wurden gespeichert.", "success")

    return render_template("user/member_request_edit.html",
                           page_title="Mitgliedschaftsanfrage Bearbeiten",
                           form=form,
                           prm=prm,
                           is_adult=prm.is_adult)


@bp.route("member-request/<int:pre_member_id>/delete", methods=['GET', 'POST'])
@access.require('user_change')
def member_request_delete(pre_member_id: int):
    prm = get_pre_member_or_404(pre_member_id)

    form = PreMemberDenyForm()

    if form.validate_on_submit():
        delete_member_request(prm, form.reason.data, current_user,
                              inform_user=form.inform_user.data)

        session.session.commit()

        flash("Mitgliedschaftsanfrage gelöscht.", "success")

        return redirect(url_for(".member_requests"))

    form_args = {
        'form': form,
        'cancel_to': url_for('.member_requests'),
        'submit_text': 'Ablehnen'
    }

    return render_template('generic_form.html',
                           page_title="Mitgliedschaftsanfrage löschen/ablehnen",
                           form_args=form_args,
                           form=form)


@bp.route("member-request/<int:pre_member_id>/finish")
@access.require('user_change')
def member_request_finish(pre_member_id: int):
    prm = get_pre_member_or_404(pre_member_id)
    try:
        with handle_errors(session.session):
            user = finish_member_request(prm, processor=current_user, ignore_similar_name=True)
            session.session.commit()
    except PycroftException:
        return redirect(url_for(".member_request_edit", pre_member_id=prm.id))

    flash("Nutzer erfolgreich erstellt.", 'success')
    return redirect(url_for(".user_show", user_id=user.id))


@bp.route("member-request/<int:pre_member_id>/merge", methods=['GET', 'POST'])
@access.require('user_change')
def member_request_merge(pre_member_id: int):
    prm = get_pre_member_or_404(pre_member_id)

    form = PreMemberMergeForm()

    possible_users = get_possible_existing_users_for_pre_member(prm)

    if form.validate_on_submit():
        return redirect(url_for(".member_request_merge_confirm",
                                pre_member_id=pre_member_id,
                                user_id=form.user_id.data))

    return render_template("user/member_request_merge.html",
                           page_title="Mitgliedschaftsanfrage zusammenführen",
                           form=form,
                           prm=prm,
                           possible_users=possible_users)


@bp.route("member-request/<int:pre_member_id>/merge/<int:user_id>", methods=['GET', 'POST'])
@access.require('user_change')
def member_request_merge_confirm(pre_member_id: int, user_id: int):
    prm = get_pre_member_or_404(pre_member_id)
    user = get_user_or_404(user_id)

    form = PreMemberMergeConfirmForm()

    form.merge_name.label.text = f"Name: {user.name} ➡ {prm.name}"
    form.merge_email.label.text = f"E-Mail: {user.email} ➡ {prm.email}"
    form.merge_person_id.label.text = f"Debitorennummer: {user.swdd_person_id} ➡ {prm.swdd_person_id}"
    form.merge_birthdate.label.text = f"Geburtsdatum: {user.birthdate} ➡ {prm.birthdate}"

    if prm.room is None or prm.room == user.room:
        form.merge_room.render_kw = {'disabled': True}
    else:
        form.merge_room.label.text = "Zimmer: {} ➡ {} am {}".format(
            user.room.short_name if user.room else None,
            prm.room.short_name if prm.room else None,
            prm.move_in_date.isoformat() if prm.move_in_date is not None else "Sofort")

    if form.validate_on_submit():
        lib.user.merge_member_request(user, prm, form.merge_name.data, form.merge_email.data,
                                      form.merge_person_id.data, form.merge_room.data,
                                      form.merge_password.data, form.merge_birthdate.data,
                                      processor=current_user)

        session.session.commit()

        send_member_request_merged_email(prm, user, form.merge_password.data)

        return redirect(url_for(".user_show", user_id=user.id))

    form_args = {
        'form': form,
        'cancel_to': url_for('.member_request_edit', pre_member_id=prm.id),
        'submit_text': 'Zusammenführen',
        'form_render_mode': 'basic',
        'field_render_mode': 'basic',
    }

    return render_template("generic_form.html",
                           page_title="Mitgliedschaftsanfrage zusammenführen",
                           form_args=form_args)


@bp.route('json/member-requests')
def member_requests_json():
    prms = get_member_requests()

    return TableResponse[PreMemberRow](
        items=[
            PreMemberRow(
                prm_id=encode_type2_user_id(prm.id),
                name=TextWithBooleanColResponse(
                    text=prm.name,
                    bool=prm.swdd_person_id is not None,
                    icon_true="fas fa-address-card",
                    icon_false="far fa-address-card",
                ),
                login=prm.login,
                email=TextWithBooleanColResponse(
                    text=prm.email, bool=prm.email_confirmed
                ),
                move_in_date=date_format_pydantic(
                    prm.move_in_date, formatter=date_filter
                ),
                action_required=prm.room is not None
                and prm.email_confirmed
                and prm.is_adult,
                actions=[
                    T.actions.single_value(
                        href=url_for(".member_request_edit", pre_member_id=prm.id),
                        title="Bearbeiten",
                        icon="fa-edit",
                        btn_class="btn-info btn-sm",
                        new_tab=True,
                    ),
                    T.actions.single_value(
                        href=url_for(".member_request_delete", pre_member_id=prm.id),
                        title="Löschen",
                        icon="fa-trash",
                        btn_class="btn-danger btn-sm",
                    ),
                ],
            )
            for prm in prms
        ]
    ).model_dump()


@bp.route('/resend-confirmation-mail')
def resend_confirmation_mail():
    user_id = request.args.get('user_id', type=int)
    is_prm = request.args.get('is_prm', type=bool, default=False)

    user: BaseUser

    if is_prm:
        user = get_pre_member_or_404(user_id)
        return_url = url_for(".member_request_edit", pre_member_id=user.id)
    else:
        user = get_user_or_404(user_id)
        return_url = url_for(".user_show", user_id=user.id)

    if user.email_confirmed:
        flash("E-Mail-Adresse bereits bestätigt!", "error")
        return redirect(return_url)
    else:
        send_confirmation_email(user)

        flash("Bestätigungsmail erneut versendet.", "success")

        session.session.commit()

        return redirect(return_url)


@nav.navigate('Archivierbar', weight=6, icon='fa-archive')
@bp.route('/archivable_users')
def archivable_users():
    table = ArchivableMembersTable(data_url=url_for('.archivable_users_json'))
    return render_template('user/archivable_users.html', table=table)


@bp.route('/archivable_users_table')
def archivable_users_json():
    return TableResponse[ArchivableMemberRow](
        items=[
            ArchivableMemberRow(
                id=info.User.id,
                user=LinkColResponse(
                    title=info.User.name,
                    href=url_for("user.user_show", user_id=info.User.id),
                ),
                room_shortname=info.User.room
                and LinkColResponse(
                    title=info.User.room.short_name,
                    href=url_for("facilities.room_show", room_id=info.User.room.id),
                ),
                current_properties=" ".join(
                    ("~" if p.denied else "") + p.property_name
                    for p in info.User.current_properties_maybe_denied
                ),
                num_hosts=len(info.User.hosts),
                end_of_membership=date_format_pydantic(info.mem_end.date()),
            )
            for info in get_archivable_members(session.session)
        ]
    ).model_dump()


@nav.navigate('Rundmail', weight=10, icon='fa-envelope')
@bp.route('/groupmail', methods=['GET', 'POST'])
@access.require('mail_group')
def mail_group():
    form = GroupMailForm()

    form_args = {
        'form': form,
        'cancel_to': url_for('.overview'),
        'submit_text': 'Absenden',
        'form_render_mode': 'basic',
        'field_render_mode': 'basic',
    }

    if form.validate_on_submit():
        lib.user.group_send_mail(
            group=form.group.data,
            subject=form.subject.data,
            body_plain=form.body_plain.data,
        )

        flash("Rundmail versendet!", "success")
        return redirect(url_for(".mail_group"))

    return render_template("generic_form.html",
                           page_title="Rundmail an Gruppe",
                           form_args=form_args)
