# -*- coding: utf-8 -*-
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
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from functools import partial
from itertools import chain

from bs_table_py.table import datetime_format, date_format
from flask import (
    Blueprint, Markup, abort, flash, jsonify, redirect, render_template,
    request, url_for, session as flask_session, make_response)
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import Text, distinct, and_
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import or_, func, cast
from wtforms.widgets import HTMLString

from pycroft import lib, config
from pycroft.helpers import utc
from pycroft.helpers.interval import closed, closedopen
from pycroft.helpers.net import mac_regex, ip_regex
from pycroft.lib.facilities import get_room
from pycroft.lib.logging import log_user_event
from pycroft.lib.membership import make_member_of, remove_member_of
from pycroft.lib.traffic import get_users_with_highest_traffic
from pycroft.lib.user import encode_type1_user_id, encode_type2_user_id, \
    traffic_history, generate_user_sheet, get_blocked_groups, \
    finish_member_request, send_confirmation_email, \
    delete_member_request, get_member_requests
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.finance import Split
from pycroft.model.host import Host, IP, Interface
from pycroft.model.user import User, Membership, PropertyGroup, Property
from web.blueprints.access import BlueprintAccess
from web.blueprints.helpers.exception import web_execute
from web.blueprints.helpers.form import refill_room_data
from web.blueprints.helpers.host import validate_unique_mac
from web.blueprints.helpers.user import get_user_or_404, get_pre_member_or_404
from web.blueprints.host.tables import HostTable
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.task.tables import TaskTable
from web.blueprints.user.forms import UserSearchForm, UserCreateForm, \
    UserLogEntry, UserAddGroupMembership, UserMoveForm, \
    UserEditForm, UserSuspendForm, UserMoveOutForm, \
    UserEditGroupMembership, \
    UserResetPasswordForm, UserMoveInForm, PreMemberEditForm, PreMemberDenyForm
from .log import formatted_user_hades_logs
from .tables import (LogTableExtended, LogTableSpecific, MembershipTable,
                     SearchTable, TrafficTopTable, RoomHistoryTable,
                     PreMemberTable)
from ..finance.tables import FinanceTable, FinanceTableSplitted
from ..helpers.log import format_user_log_entry, format_room_log_entry, \
    format_task_log_entry
from ...template_filters import date_filter, datetime_filter

bp = Blueprint('user', __name__)
access = BlueprintAccess(bp, required_properties=['user_show'])
nav = BlueprintNavigation(bp, "Nutzer", blueprint_access=access)


@bp.route('/')
@nav.navigate(u"Übersicht")
def overview():
    uquery = lambda: session.session.query(User)

    entries = [{"title": "Nutzer in Datenbank",
                "href": None,
                "number": uquery().count()},
               {"title": "Mitglieder",
                "href": None,
                "number": uquery().join(Membership).filter(
                                Membership.group == config.member_group,
                                Membership.active())
                           .count()},
               {"title": "Nicht bezahlt",
                "href": None,
                "number": uquery().join(User.account)
                           .join(Split)
                           .group_by(User.id)
                           .having(func.sum(Split.amount) > 0)
                           .count()},
               {"title": "Nicht bezahlt (Mitglieder)",
                "href": "#",
                "number": uquery().join(Membership).filter(
                                Membership.group == config.member_group,
                                Membership.active())
                           .join(User.account)
                           .join(Split)
                           .group_by(User.id)
                           .having(func.sum(Split.amount) > 0)
                           .count()}]
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
    user = User.q.get(user_id)
    if user is None:
        abort(404)

    return make_pdf_response(generate_user_sheet(True, False, user, plain_user_password="********",
                                                 generation_purpose='reprint'),
                             filename='user_sheet_plain_{}.pdf'.format(user_id))


@bp.route('/json/traffic-usage')
def json_users_highest_traffic():
    return jsonify(items=[{
        'id': user.id,
        'name': user.name,
        'traffic_for_days': user.traffic_for_days,
        'url': {
            'href': url_for('.user_show', user_id=user.id),
            'title': user.name
        }} for user in get_users_with_highest_traffic(7, 20)])


@bp.route('/json/search')
def json_search():
    user_id = request.args.get('id')
    name = request.args.get('name')
    login = request.args.get('login')
    mac = request.args.get('mac')
    ip_address = request.args.get('ip_address')
    property_group_id = request.args.get('property_group_id')
    building_id = request.args.get('building_id')
    query = request.args.get("query")
    result = User.q

    count_no_filter = result.count()

    if user_id is not None and user_id != "":
        try:
            result = result.filter(User.id == int(user_id))
        except ValueError:
            return abort(400)
    if name:
        result = result.filter(User.name.ilike("%{}%".format(name)))
    if login:
        result = result.filter(User.login.ilike("%{}%".format(login)))
    if mac:
        if not re.match(mac_regex, mac):
            return abort(400)

        result = result.join(User.hosts)\
                       .join(Host.interfaces)\
                       .filter(Interface.mac == mac)
    if ip_address:
        if not re.match(ip_regex, ip_address):
            return abort(400)

        result = result.join(User.hosts) \
                       .join(Host.ips) \
                       .filter(IP.address == ip_address)

    search_for_pg = property_group_id is not None and property_group_id != "" \
        and property_group_id != "__None"

    if search_for_pg:
        result = result.join(Membership)
        result = result.filter(or_(
                            Membership.ends_at.is_(None),
                            Membership.ends_at > func.current_timestamp())) \
                       .filter(or_(
                            Membership.begins_at.is_(None),
                            Membership.begins_at < func.current_timestamp()))

        try:
            if search_for_pg:
                pg_id = int(property_group_id)
                result = result.join(PropertyGroup, PropertyGroup.id == Membership.group_id) \
                                  .filter(PropertyGroup.id == pg_id)
        except ValueError:
            return abort(400)
    if building_id is not None and building_id != "" and building_id != "__None":
        try:
            result = result.join(User.room) \
                           .filter(Room.building_id == int(building_id))
        except ValueError:
            return abort(400)
    if query:
        query = query.strip()

        if re.match(mac_regex, query):
            result = result.join(User.hosts) \
                           .join(Host.interfaces) \
                           .filter(Interface.mac == query)
        elif re.match(ip_regex, query):
            result = result.join(User.hosts) \
                           .join(Host.ips) \
                           .filter(IP.address == query)
        else:
            result = result.filter(or_(
                func.lower(User.name).like(
                    func.lower(u"%{0}%".format(query))),
                func.lower(User.login).like(
                    func.lower(u"%{0}%".format(query))),
                cast(User.id, Text).like(u"{0}%".format(query))
            ))

    return jsonify(items=[{
        'id': found_user.id,
        'name': found_user.name,
        'url': {
            'href': url_for('.user_show', user_id=found_user.id),
            'title': found_user.name
        },
        'login': found_user.login,
        'room_id': found_user.room_id if found_user.room_id is not None else None
    } for found_user in (result.all() if result.count() < count_no_filter else [])])


def infoflags(user):
    user_status = lib.user.status(user)
    return [
        {'title': u"Mitglied", 'icon': "user", 'val': user_status.member},
        {'title': u"Netzwerkzugang", 'icon': "globe", 'val': user_status.network_access},
        {'title': u"WLAN-Zugang", 'icon': "wifi", 'val': user_status.wifi_access},
        {'title': u"Bezahlt", 'icon': "euro-sign", 'val': user_status.account_balanced},
        {'title': u"Verstoßfrei", 'icon': "exclamation-triangle", 'val': not user_status.violation},
        {'title': u"LDAP", 'icon': "cloud", 'val': user_status.ldap},
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
        flash(u'Kommentar hinzugefügt', 'success')

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
            flash(Markup(u'Es ist ein <a href="{}" target="_blank">Nutzerdatenblatt</a> verfügbar!'.format(
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
        tabs=[
            {
                'id': 'hosts',
                'name': 'Hosts & Interfaces',
                'badge': len(user.hosts)
            },
            {
                'id': 'tasks',
                'name': 'Aufgaben',
                'badge': len(user.tasks),
                'badge_color': '#d9534f' if len(user.tasks) > 0 else None
            },
            {
                'id': 'logs',
                'name': 'Logs',
                'badge': len(user.log_entries)
            },
            {
                'id': 'traffic',
                'name': 'Traffic',
            },
            {
                'id': 'finance',
                'name': 'Finanzen',
            },
            {
                'id': 'groups',
                'name': 'Gruppen',
                'badge': len(user.active_memberships())
            },
            {
                'id': 'room_history',
                'name': 'Wohnorte',
                'badge': len(user.room_history_entries)
            },
        ]
    )


@bp.route("/<int:user_id>/account")
def user_account(user_id):
    user = get_user_or_404(user_id)
    return redirect(url_for("finance.accounts_show",
                            account_id=user.account_id))


@bp.route("/<int:user_id>/logs")
@bp.route("/<int:user_id>/logs/<logtype>")
def user_show_logs_json(user_id, logtype="all"):
    user = get_user_or_404(user_id)

    log_sources = []  # list of iterators

    if logtype in ["user", "all"]:
        log_sources.append((format_user_log_entry(e) for e in user.log_entries))
    if logtype in ["room", "all"] and user.room:
        log_sources.append((format_room_log_entry(e) for e in user.room.log_entries))
    if logtype in ["tasks", "all"]:
        log_sources.append((format_task_log_entry(e) for e in user.task_log_entries))
    if logtype in ["hades", "all"]:
        log_sources.append(formatted_user_hades_logs(user))

    return jsonify(items=list(sorted(chain(*log_sources),
                                     key=operator.itemgetter('raw_created_at'),
                                     reverse=True)))


@bp.route("/<int:user_id>/groups")
@bp.route("/<int:user_id>/groups/<group_filter>")
def user_show_groups_json(user_id, group_filter="all"):
    memberships = Membership.q.filter(Membership.user_id == user_id)
    if group_filter == "active":
        memberships = memberships.filter(
            # it is important to use == here, "is" does NOT work
            or_(Membership.begins_at == None,
                Membership.begins_at <= session.utcnow())
        ).filter(
            # it is important to use == here, "is" does NOT work
            or_(Membership.ends_at == None,
                Membership.ends_at > session.utcnow())
        )

    group = aliased(PropertyGroup)
    p_granted = aliased(Property)
    p_denied = aliased(Property)
    memberships = (
        memberships
            .join(group)
            .outerjoin(p_granted, and_(p_granted.property_group_id == group.id,
                                       p_granted.granted == True))
            .add_column(func.array_agg(distinct(p_granted.name))
                        .label('granted'))

            .outerjoin(p_denied, and_(p_denied.property_group_id == group.id,
                                      p_denied.granted == False))
            .add_column(func.array_agg(distinct(p_denied.name))
                        .label('denied'))

            .group_by(Membership.id)
    )

    return jsonify(items=[{
            'group_name': membership.group.name,
            'begins_at': datetime_format(membership.begins_at,
                                         default='',
                                         formatter=datetime_filter),
            'ends_at': datetime_format(membership.ends_at, default='', formatter=datetime_filter),
            'grants': granted,
            'denies': denied,
            'active': membership.active(),
            'actions': [{'href': url_for(".edit_membership",
                                        user_id=user_id,
                                        membership_id=membership.id),
                        'title': 'Bearbeiten',
                        'icon': 'fa-edit'},
                        {'href': url_for(".end_membership",
                                         user_id=user_id,
                                         membership_id=membership.id),
                         'title': "Beenden",
                         'icon': 'fa-power-off'} if membership.active() else {}],
        } for membership, granted, denied in memberships.all()])


@bp.route('/<int:user_id>/add_membership', methods=['GET', 'Post'])
@access.require('groups_change_membership')
def add_membership(user_id):
    user = get_user_or_404(user_id)
    form = UserAddGroupMembership()

    if form.validate_on_submit():
        if form.begins_at.date.data:
            begins_at = datetime.combine(form.begins_at.date.data, utc.time_min())
        else:
            begins_at = session.utcnow()
        if not form.ends_at.unlimited.data:
            ends_at = datetime.combine(form.ends_at.date.data, utc.time_min())
        else:
            ends_at = None
        make_member_of(user, form.group.data, current_user,
                       closed(begins_at, ends_at))
        session.session.commit()
        flash(u'Nutzer wurde der Gruppe hinzugefügt.', 'success')

        return redirect(url_for(".user_show",
                                user_id=user_id,
                                _anchor='groups'))

    return render_template('user/add_membership.html',
        page_title=u"Neue Gruppenmitgliedschaft für Nutzer {}".format(user_id),
        user_id=user_id, form=form)


@bp.route('/<int:user_id>/end_membership/<int:membership_id>')
@access.require('groups_change_membership')
def end_membership(user_id, membership_id):
    user = get_user_or_404(user_id)
    membership = Membership.q.get(membership_id)

    if membership is None:
        flash(u"Gruppenmitgliedschaft mit ID {} existiert nicht!".format(membership.id), 'error')
        abort(404)

    if membership.user.id != user_id:
        flash(u"Gruppenmitgliedschaft {} gehört nicht zu Nutzer {}!".format(membership.id, user_id), 'error')
        return abort(404)

    remove_member_of(user, membership.group, current_user, closedopen(session.utcnow(), None))

    session.session.commit()
    flash(u'Mitgliedschaft in Gruppe beendet', 'success')
    return redirect(url_for(".user_show",
                            user_id=membership.user_id,
                            _anchor='groups'))


@bp.route('/<int:user_id>/traffic/json')
@bp.route('/<int:user_id>/traffic/json/<int:days>')
def json_trafficdata(user_id, days=7):
    """Generate a JSON file to use with traffic and credit graphs.

    :param user_id:
    :param days: optional amount of days to be included
    :return: JSON with traffic and credit data formatted according to the following schema
    {
        "type": "object",
        "properties": {
            "items": {
                "type": "object",
                "properties": {
                    "traffic": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "egress": { "type": "integer" },
                                "ingress": { "type": "integer" },
                                "timestamp": { "type": "string" }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    interval = timedelta(days=days)
    result = traffic_history(user_id, session.utcnow() - interval + timedelta(days=1), session.utcnow())

    return jsonify(
        items={
            'traffic': [e.__dict__ for e in result]
        }
    )


def validate_unique_name(form, field):
    if not form.force.data:
        try:
            room = Room.q.filter_by(number=form.room_number.data,
                                    level=form.level.data,
                                    building=form.building.data).one()

            if room is not None:
                users = User.q.filter_by(room_id=room.id).all()

                for user in users:
                    ratio = SequenceMatcher(None, field.data, user.name).ratio()

                    if ratio > 0.6:
                        return HTMLString("<div class=\"optional-error\">* " +
                                          u"Ein ähnlicher Benutzer existiert bereits in diesem Zimmer!" +
                                          "<br/>Nutzer: " +
                                          "<a target=\"_blank\" href=\"" +
                                          url_for("user.user_show", user_id=user.id) +
                                          "\">" + user.name + "</a></div>")
        except:
            pass

    return False


def validate_unique_email(form, field):
    if field.data:
        user = User.q.filter_by(email=field.data).first()
        if user is not None and not form.force.data:
            return HTMLString("<div class=\"optional-error\">* "
                              + "E-Mail bereits in Verwendung!<br/>Nutzer: " +
                              "<a target=\"_blank\" href=\"" +
                              url_for("user.user_show", user_id=user.id) +
                              "\">" + user.name + "</a></div>")


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate(u"Anlegen")
@access.require('user_change')
def create():
    form = UserCreateForm(property_groups=[config.member_group])

    if form.is_submitted():
        unique_name_error = validate_unique_name(form, form.name)
        unique_email_error = validate_unique_email(form, form.email)
        unique_mac_error = validate_unique_mac(form, form.mac)

    if form.validate_on_submit() and not (unique_name_error or
                                          unique_email_error or
                                          unique_mac_error):

        room: Room = get_room(building_id=form.building.data.id, level=form.level.data,
                        room_number=form.room_number.data)
        if not room:
            flash("Raum scheint nicht zu existieren…", 'error')
            return
        result, success = web_execute(
            lib.user.create_user,
            None,
            name=form.name.data,
            login=form.login.data,
            processor=current_user,
            email=form.email.data,
            birthdate=form.birthdate.data,
            groups=form.property_groups.data,
            address=room.address,
            send_confirm_mail=True,
        )

        if success:
            (new_user, plain_password) = result

            # We only have to check if building is present, as the presence
            # of the other fields depends on building
            if form.building.data is not None:
                _, success = web_execute(
                    lib.user.move_in,
                    None,
                    user=new_user,
                    building_id=form.building.data.id, level=form.level.data,
                    room_number=form.room_number.data,
                    mac=form.mac.data,
                    processor=current_user,
                    host_annex=form.annex.data,
                    begin_membership=False,
                )

            if success:
                wifi_password = False
                plain_wifi_password = ''
                if new_user.room.building.wifi_available is True:
                    # create wifi credentials
                    plain_wifi_password = lib.user.reset_wifi_password(new_user, processor=current_user)
                    wifi_password = True
                sheet = lib.user.store_user_sheet(True, wifi_password, user=new_user,
                                                  plain_user_password=plain_password,
                                                  plain_wifi_password=plain_wifi_password)
                session.session.commit()

                flask_session['user_sheet'] = sheet.id
                flash(Markup(u'Benutzer angelegt.'), 'success')

                return redirect(url_for('.user_show', user_id=new_user.id))

    if form.is_submitted():
        if unique_name_error:
            form.name.errors.append(unique_name_error)

        if unique_email_error:
            form.email.errors.append(unique_email_error)

        if unique_mac_error:
            form.mac.errors.append(unique_mac_error)

    return render_template('user/user_create.html', form=form)


@bp.route('/<int:user_id>/move', methods=['GET', 'POST'])
@access.require('user_change')
def move(user_id):
    user = get_user_or_404(user_id)
    form = UserMoveForm()

    refill_form_data = False
    if form.validate_on_submit():
        if user.room == Room.q.filter_by(
                number=form.room_number.data,
                level=form.level.data,
                building_id=form.building.data.id).one():
            flash(u"Nutzer muss in anderes Zimmer umgezogen werden!", "error")
            refill_form_data = True
        else:
            when = session.utcnow() if form.now.data else datetime.combine(form.when.data, utc.time_min())

            _, success = web_execute(lib.user.move, None,
                user=user,
                building_id=form.building.data.id,
                level=form.level.data,
                room_number=form.room_number.data,
                processor=current_user,
                when=when
            )

            if success:
                session.session.commit()

                if when > session.utcnow():
                    flash(u'Der Umzug wurde vorgemerkt.', 'success')
                else:
                    flash(u'Benutzer umgezogen', 'success')
                    sheet = lib.user.store_user_sheet(True, False, user=user,
                                                      plain_user_password='********',
                                                      generation_purpose='user moved')
                    session.session.commit()

                    flask_session['user_sheet'] = sheet.id

                return redirect(url_for('.user_show', user_id=user.id))

    if not form.is_submitted() or refill_form_data:
        if user.room is not None:
            refill_room_data(form, user.room)

    return render_template('user/user_move.html', user_id=user_id, form=form)


@bp.route('/<int:user_id>/edit_membership/<int:membership_id>', methods=['GET', 'POST'])
@access.require('groups_change_membership')
def edit_membership(user_id, membership_id):
    membership = Membership.q.get(membership_id)

    if membership is None:
        flash(u"Gruppenmitgliedschaft mit ID {} existiert nicht!".format(
        membership_id), 'error')
        abort(404)

    if membership.group.permission_level > current_user.permission_level:
        flash("Eine Bearbeitung von Gruppenmitgliedschaften für Gruppen mit "
              "höherem Berechtigungslevel ist nicht möglich.", 'error')
        abort(403)

    membership_data = {}
    if request.method == 'GET':
        membership_data = {
            "begins_at": None if membership.begins_at is None else membership.begins_at.date(),
            "ends_at": {"unlimited": membership.ends_at is None,
                        "date": membership.ends_at and membership.ends_at.date()}
        }

    form = UserEditGroupMembership(**membership_data)

    if form.validate_on_submit():
        membership.begins_at = datetime.combine(form.begins_at.data, utc.time_min())
        if form.ends_at.unlimited.data:
            membership.ends_at = None
        else:
            membership.ends_at = datetime.combine(form.ends_at.date.data, utc.time_min())

        message = (u"Edited the membership of group '{group}'. During: {during}"
                   .format(group=membership.group.name,
                           during=closed(membership.begins_at, membership.ends_at)))
        lib.logging.log_user_event(message, current_user, membership.user)
        session.session.commit()
        flash(u'Gruppenmitgliedschaft bearbeitet', 'success')
        return redirect(url_for('.user_show',
                                user_id=membership.user_id,
                                _anchor='groups'))

    return render_template('user/user_edit_membership.html',
                           page_title=(u"Mitgliedschaft {} für "
                                       u"{} bearbeiten".format(
                                            membership.group.name,
                                            membership.user.name)),
                           membership_id=membership_id,
                           user=membership.user,
                           form=form)


@bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@access.require('user_change')
def edit_user(user_id):
    user = get_user_or_404(user_id)
    form = UserEditForm()

    if not form.is_submitted():
        form.name.data = user.name
        form.email.data = user.email
        form.email_forwarded.data = user.email_forwarded
        form.birthdate.data = user.birthdate

    if form.validate_on_submit():
        edited_user = lib.user.edit_name(user, form.name.data, current_user)
        edited_user = lib.user.edit_email(edited_user, form.email.data,
                                          form.email_forwarded.data, current_user)
        edited_user = lib.user.edit_birthdate(edited_user, form.birthdate.data,
                                              current_user)
        session.session.commit()

        flash(u'Änderungen gespeichert', 'success')
        return redirect(url_for('.user_show', user_id=edited_user.id))

    return render_template('user/user_edit.html', user_id=user_id,
        form=form)


@bp.route('/search', methods=['GET', 'POST'])
@nav.navigate(u"Suchen")
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
    myUser = User.q.get(user_id)
    if form.validate_on_submit():
        plain_password = lib.user.reset_password(myUser, processor=current_user)

        sheet = lib.user.store_user_sheet(True, False, user=myUser,
                                          plain_user_password=plain_password,
                                          generation_purpose='password reset')
        session.session.commit()

        flask_session['user_sheet'] = sheet.id
        flash(Markup(u'Passwort erfolgreich zurückgesetzt.'),
              'success')
        return redirect(url_for('.user_show', user_id=user_id))
    return render_template('user/user_reset_password.html', form=form, user_id=user_id)


@bp.route('/<int:user_id>/reset_wifi_password', methods=['GET', 'POST'])
@access.require('user_change')
def reset_wifi_password(user_id):
    form = UserResetPasswordForm()
    myUser = User.q.get(user_id)
    if form.validate_on_submit():
        plain_password = lib.user.reset_wifi_password(myUser, processor=current_user)
        sheet = lib.user.store_user_sheet(False, True, user=myUser,
                                          plain_wifi_password=plain_password,
                                          generation_purpose='password reset')

        session.session.commit()

        flask_session['user_sheet'] = sheet.id
        flash(Markup(u'WIFI-Passwort erfolgreich zurückgesetzt.'),
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
            ends_at = datetime.combine(form.ends_at.date.data, utc.time_min())

        try:
            during = closedopen(session.utcnow(), ends_at)
            blocked_user = lib.user.block(
                user=myUser,
                reason=form.reason.data,
                processor=current_user,
                during=during,
                violation=form.violation.data)
            session.session.commit()
        except ValueError as e:
            flash(str(e), 'error')
        else:
            flash(u'Nutzer gesperrt.', 'success')
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
        flash(u'Nutzer entsperrt.', 'success')
        return redirect(url_for('.user_show', user_id=user_id))


@bp.route('/<int:user_id>/move_out', methods=['GET', 'POST'])
@access.require('user_change')
def move_out(user_id):
    form = UserMoveOutForm()
    user = get_user_or_404(user_id)

    if not user.room:
        flash("Nutzer {} ist aktuell nirgends eingezogen!".
              format(user_id), 'error')
        abort(404)

    if form.validate_on_submit():
        when = session.utcnow() if form.now.data else datetime.combine(
            form.when.data, utc.time_min())

        _, success = web_execute(lib.user.move_out, None,
            user=user,
            comment=form.comment.data,
            processor=current_user,
            when=session.utcnow() if form.now.data else datetime.combine(
             form.when.data, utc.time_min()),
            end_membership=form.end_membership.data
        )

        if success:
            session.session.commit()

            if when > session.utcnow():
                flash("Der Auszug wurde vorgemerkt.", "success")
            else:
                flash(u'Benutzer ausgezogen.', 'success')

            return redirect(url_for('.user_show', user_id=user.id))

    if not form.is_submitted():
        form.end_membership.data = True

    return render_template('user/user_move_out.html', form=form, user_id=user_id)


@bp.route('/<int:user_id>/move_in', methods=['GET', 'POST'])
@access.require('user_change')
def move_in(user_id):
    form = UserMoveInForm()
    user = get_user_or_404(user_id)

    if user.room is not None:
        flash("Nutzer {} ist nicht ausgezogen!".format(user_id), 'error')
        abort(404)

    if form.validate_on_submit():
        when = session.utcnow() if form.now.data else datetime.combine(
            form.when.data, utc.time_min())

        _, success = web_execute(lib.user.move_in, None,
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

        if success:
            session.session.commit()

            if when > session.utcnow():
                flash("Der Einzug wurde vorgemerkt.", 'success')
            else:
                flash("Benutzer eingezogen.", 'success')

            return redirect(url_for('.user_show', user_id=user_id))

    if not form.is_submitted():
        form.birthdate.data = user.birthdate
        form.begin_membership.data = True

    return render_template('user/user_move_in.html', form=form, user_id=user_id)


@bp.route('<int:user_id>/json/room-history')
def room_history_json(user_id):
    user = get_user_or_404(user_id)

    return jsonify(items=[{
        'begins_at': date_format(history_entry.begins_at, formatter=date_filter),
        'ends_at': date_format(history_entry.ends_at, formatter=date_filter),
        'room': {
            'href': url_for('facilities.room_show', room_id=history_entry.room_id),
            'title': history_entry.room.short_name
        }} for history_entry in user.room_history_entries])


@bp.route('member-requests')
@nav.navigate("Mitgliedschaftsanfragen")
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
        move_in_date=prm.move_in_date.date() if prm.move_in_date is not None else None,
    )

    if form.is_submitted():
        unique_name_error = validate_unique_name(form, form.name)
        unique_email_error = validate_unique_email(form, form.email)

    if form.validate_on_submit() and not (unique_name_error or unique_email_error):
        old_email = prm.email

        prm.name = form.name.data
        prm.login = form.login.data
        prm.email = form.email.data
        prm.move_in_date = form.move_in_date.data

        room = Room.q.filter_by(building=form.building.data, level=form.level.data,
                                number=form.room_number.data).first()

        prm.room = room

        if old_email != prm.email:
            send_confirmation_email(prm)

            flash("Es wurde eine neue Bestätigungsmail verschickt!", "warning")

        session.session.commit()

        flash("Änderungen wurden gespeichert.", "success")

    if form.is_submitted():
        if unique_name_error:
            form.name.errors.append(unique_name_error)

        if unique_email_error:
            form.email.errors.append(unique_email_error)

    return render_template("user/member_request_edit.html",
                           page_title="Mitgliedschaftsanfrage Bearbeiten",
                           form=form,
                           prm=prm)


@bp.route("member-request/<int:pre_member_id>/delete", methods=['GET', 'POST'])
@access.require('user_change')
def member_request_delete(pre_member_id: int):
    prm = get_pre_member_or_404(pre_member_id)

    form = PreMemberDenyForm()

    if form.validate_on_submit():
        delete_member_request(prm, form.reason.data, current_user)

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

    user, success = web_execute(finish_member_request, "Nutzer erfolgreich erstellt.", prm,
                                current_user)

    if success:
        session.session.commit()

        return redirect(url_for(".user_show", user_id=user.id))
    else:
        return redirect(url_for(".member_request_edit", pre_member_id=prm.id))


@bp.route('json/member-requests')
def member_requests_json():
    prms = get_manual_member_requests()

    return jsonify(items=[{
        'id': prm.id,
        'name': prm.name,
        'login': prm.login,
        'email': prm.email,
        'email_confirmed': prm.email_confirmed,
        'move_in_date': date_format(prm.move_in_date, formatter=date_filter),
        'actions': [{'href': url_for(".member_request_edit",
                                     pre_member_id=prm.id),
                     'title': 'Bearbeiten',
                     'icon': 'fa-edit',
                     'btn_class': 'btn-info btn-sm',
                     'new_tab': True},
                    {'href': url_for(".member_request_delete",
                                     pre_member_id=prm.id),
                     'title': 'Löschen',
                     'icon': 'fa-trash',
                     'btn_class': 'btn-danger btn-sm'},
                    ]
    } for prm in prms])
