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
from itertools import chain
from functools import partial
from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request,
    url_for)
import operator
from sqlalchemy import Text, and_

from pycroft import lib, config
from pycroft.helpers.interval import closed, closedopen
from pycroft.lib.finance import get_typed_splits
from pycroft.lib.net import SubnetFullException, MacExistsException
from pycroft.lib.host import change_mac as lib_change_mac
from pycroft.lib.user import make_member_of, encode_type1_user_id, encode_type2_user_id
from pycroft.model import functions, session
from pycroft.model.traffic import TrafficVolume, TrafficCredit, TrafficBalance
from pycroft.model.facilities import Room
from pycroft.model.host import Host, UserInterface, IP, Interface
from pycroft.model.user import User, Membership, PropertyGroup, TrafficGroup
from pycroft.model.finance import Split
from pycroft.model.types import InvalidMACAddressException
from sqlalchemy.sql.expression import or_, func, cast
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.user.forms import UserSearchForm, UserCreateForm,\
    HostCreateForm, UserLogEntry, UserAddGroupMembership, UserMoveForm,\
    UserEditNameForm, UserEditEMailForm, UserSuspendForm, UserMoveOutForm, \
    InterfaceChangeMacForm, UserEditGroupMembership, UserSelectGroupForm, \
    UserMoveBackInForm
from web.blueprints.access import BlueprintAccess
from web.blueprints.helpers.api import json_agg
from datetime import datetime, timedelta, time
from flask_login import current_user
from web.template_filters import (
    datetime_filter, host_cname_filter, host_name_filter)
from ..helpers.log import format_user_log_entry, format_room_log_entry, \
    format_hades_log_entry
from .log import formatted_user_hades_logs
from .tables import LogTableExtended, LogTableSpecific, MembershipTable, HostTable
from ..finance.tables import FinanceTable, FinanceTableSplitted

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
    return render_template("user/user_overview.html", entries=entries)


@bp.route('/json/search')
def json_search():
    query = request.args['query']
    results = session.session.query(User.id, User.login, User.name).filter(or_(
        func.lower(User.name).like(func.lower(u"%{0}%".format(query))),
        func.lower(User.login).like(func.lower(u"%{0}%".format(query))),
        cast(User.id, Text).like(u"{0}%".format(query))
    )).all()
    users = [{"id": user_id, "login": login, "name": name}
             for user_id, login, name in results]
    return jsonify(users=users)


def infoflags(user):
    user_status = lib.user.status(user)
    return [
        {'title': u"Netzwerkzugang", 'val': user_status.network_access},
        {'title': u"Traffic übrig", 'val': not user_status.traffic_exceeded},
        {'title': u"Bezahlt", 'val': user_status.account_balanced},
        {'title': u"Verstoßfrei", 'val': not user_status.violation},
        {'title': u"Mailkonto", 'val': user_status.ldap},
    ]

def get_user_or_404(user_id):
    user = User.q.get(user_id)
    if user is None:
        flash(u"Nutzer mit ID {} existiert nicht!".format(user_id,), 'error')
        abort(404)
    return user


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
    is_blocked = user.member_of(config.violation_group)
    user_not_there = not user.member_of(config.member_group)

    return render_template(
        'user/user_show.html',
        # Q: Can ports of a room point to different access switches?
        user=user,
        user_not_there=user_not_there,
        user_id_new=encode_type2_user_id(user.id),
        user_id_old=encode_type1_user_id(user.id),
        balance=balance,
        hosts_rooms={host.room for host in user.user_hosts},
        log_table_all=LogTableExtended(data_url=_log_endpoint()),
        log_table_user=LogTableSpecific(data_url=_log_endpoint(logtype="user")),
        log_table_room=LogTableSpecific(data_url=_log_endpoint(logtype="room")),
        log_table_hades=LogTableSpecific(data_url=_log_endpoint(logtype="hades")),
        membership_table_all=MembershipTable(
            user_id=user.id,
            data_url=_membership_endpoint(),
        ),
        membership_table_active=MembershipTable(
            user_id=user.id,
            data_url=_membership_endpoint(group_filter="active"),
        ),
        host_table=HostTable(data_url=url_for(".user_show_hosts_json", user_id=user.id)),
        finance_table_regular=FinanceTable(**_finance_table_kwargs),
        finance_table_splitted=FinanceTableSplitted(**_finance_table_kwargs),
        room=room,
        form=form,
        flags=infoflags(user),
        json_url=url_for("finance.accounts_show_json",
                         account_id=user.account_id),
        traffic_json_url=url_for('.json_trafficdata', user_id=user_id),
        is_blocked = is_blocked
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
    if logtype in ["hades", "all"]:
        log_sources.append(formatted_user_hades_logs(user))

    return jsonify(items=list(sorted(chain(*log_sources),
                                     key=operator.itemgetter('raw_created_at'),
                                     reverse=True)))


@bp.route("/<int:user_id>/hosts")
def user_show_hosts_json(user_id):
    list_items = []
    for user_host in User.q.get(user_id).user_hosts:
        if user_host.room:
            patch_ports = user_host.room.switch_patch_ports
            switches = ', '.join(p.switch_interface.host.name for p in patch_ports)
            ports = ', '.join(p.switch_interface.name for p in patch_ports)
        else:
            switches = None
            ports = None
        for ip in user_host.ips:
            list_items.append({
                'id': str(user_host.id),
                'ip': str(ip.address),
                'mac': ip.interface.mac,
                'switch': switches,
                'port': ports,
                'action': {'href': url_for('.change_mac', user_id=user_id,
                                           user_interface_id=ip.interface.id),
                           'title': "Bearbeiten",
                           'icon': 'glyphicon-pencil',
                           'btn-class': 'btn-link'}
            })
    return jsonify(items=list_items)


@bp.route("/<int:user_id>/groups")
@bp.route("/<int:user_id>/groups/<group_filter>")
def user_show_groups_json(user_id, group_filter="all"):
    memberships = Membership.q.filter(Membership.user_id == user_id)
    if group_filter == "active":
        memberships = memberships.filter(
            # it is important to use == here, "is" does NOT work
            or_(Membership.begins_at == None,
                Membership.begins_at <= functions.utcnow())
        ).filter(
            # it is important to use == here, "is" does NOT work
            or_(Membership.ends_at == None,
                Membership.ends_at > functions.utcnow())
        )

    return jsonify(items=[{
            'group_name': membership.group.name,
            'begins_at': (datetime_filter(membership.begins_at)
                          if membership.begins_at is not None else ''),
            'ends_at': (datetime_filter(membership.ends_at)
                        if membership.ends_at is not None else ''),
            'actions': [{'href': url_for(".edit_membership",
                                        user_id=user_id,
                                        membership_id=membership.id),
                        'title': 'Bearbeiten',
                        'icon': 'glyphicon-edit'},
                        {'href': url_for(".end_membership",
                                         user_id=user_id,
                                         membership_id=membership.id),
                         'title': "Beenden",
                         'icon': 'glyphicon-off'}],
        } for membership in memberships.all()])


@bp.route('/<int:user_id>/add_membership', methods=['GET', 'Post'])
@access.require('groups_change_membership')
def add_membership(user_id):
    user = get_user_or_404(user_id)
    form = UserAddGroupMembership()

    if form.validate_on_submit():
        if form.begins_at.data is not None:
            begins_at = datetime.combine(form.begins_at.data, time(0))
        else:
            begins_at = session.utcnow()
        if not form.ends_at.unlimited.data:
            ends_at = datetime.combine(form.ends_at.date.data, time(0))
        else:
            ends_at = None
        make_member_of(user, form.group.data, current_user,
                       closed(begins_at, ends_at))
        message = u"Nutzer zur Gruppe '{}' hinzugefügt.".format(form.group.data.name)
        lib.logging.log_user_event(message, current_user, user)
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
    membership = Membership.q.get(membership_id)
    membership.disable()

    if membership.user.id != user_id:
        flash(u"Mitgliedschaft {} gehört nicht zu Nutzer {}!".format(membership.id, user_id), 'error')
        return abort(404)

    # ToDo: Make the log messages not Frontend specific (a helper?)
    message = u"hat die Mitgliedschaft des Nutzers in der Gruppe '{}' " \
              u"beendet.".format(membership.group.name)
    lib.logging.log_user_event(message, current_user, membership.user)
    session.session.commit()
    flash(u'Mitgliedschaft in Gruppe beendet', 'success')
    return redirect(url_for(".user_show",
                            user_id=membership.user_id,
                            _anchor='groups'))


@bp.route('/<int:user_id>/traffic/json')
@bp.route('/<int:user_id>/traffic/json/<int:days>')
def json_trafficdata(user_id, days=7):
    """Generate a Highcharts compatible JSON file to use with traffic graphs.

    :param user_id:
    :param days: optional amount of days to be included
    :return: JSON with traffic data for INPUT and OUTPUT with [datetime, megabyte] tuples.
    """
    traffic_timespan = (session.utcnow() - timedelta(days=days)).date()
    # get all traffic volumes for the user in the timespan

    traffic_volumes = TrafficVolume.q.join(IP).join(Interface).join(Host
        ).filter(
            and_(TrafficVolume.timestamp > traffic_timespan,
                 Host.owner_id == user_id)
        ).order_by(
            TrafficVolume.timestamp)

    traffic_volumes = json_agg(traffic_volumes).one()[0]

    traffic_credits = json_agg(
        TrafficCredit.q.filter_by(user_id=user_id)).one()[0]

    traffic_balance = json_agg(TrafficBalance.q.filter_by(user_id=user_id)).one()[0]

    return jsonify(
        items={
            'debits': traffic_volumes,
            'credits': traffic_credits,
            'balance': traffic_balance,
        }
    )


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate(u"Anlegen")
@access.require('user_change')
def create():
    form = UserCreateForm()
    if form.validate_on_submit():
        try:
            new_user = lib.user.move_in(name=form.name.data,
                login=form.login.data,
                building=form.building.data, level=form.level.data,
                room_number=form.room_number.data,
                mac=form.mac.data,
                processor=current_user,
                email=form.email.data,
            )
            session.session.commit()

            flash(u'Benutzer angelegt', 'success')
            return redirect(url_for('.user_show', user_id = new_user.id))

        except (MacExistsException,
                SubnetFullException,
                InvalidMACAddressException) as error:
            flash(str(error), 'error')
            session.session.rollback()

    return render_template('user/user_create.html', form = form)


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
            edited_user = lib.user.move(user, form.building.data,
                form.level.data, form.room_number.data, current_user)
            session.session.commit()

            flash(u'Benutzer umgezogen', 'success')
            return redirect(url_for('.user_show', user_id=edited_user.id))

    if not form.is_submitted() or refill_form_data:
        form.building.data = user.room.building

        levels = session.session.query(Room.level.label('level')).filter_by(
            building_id=user.room.building.id).order_by(Room.level).distinct()

        form.level.choices = [(entry.level, str(entry.level)) for entry in
                                                              levels]
        form.level.data = user.room.level

        rooms = session.session.query(Room).filter_by(
            building_id=user.room.building.id,
            level=user.room.level
        ).order_by(Room.number).distinct()

        form.room_number.choices = [(entry.number, str(entry.number))
                                    for entry in rooms]
        form.room_number.data = user.room

    return render_template('user/user_move.html', user_id=user_id, form=form)


@bp.route('/<int:user_id>/edit_membership/<int:membership_id>', methods=['GET', 'POST'])
@access.require('groups_change_membership')
def edit_membership(user_id, membership_id):
    membership = Membership.q.get(membership_id)

    if membership is None:
        flash(u"Gruppenmitgliedschaft mit ID {} existiert nicht!".format(
        membership_id), 'error')
        abort(404)

    membership_data = {}
    if request.method == 'GET':
        membership_data = {
            "begins_at": membership.begins_at.date(),
            "ends_at": {"unlimited": membership.ends_at is None,
                        "date": membership.ends_at and membership.ends_at.date()}
        }

    form = UserEditGroupMembership(**membership_data)

    if form.validate_on_submit():
        membership.begins_at = datetime.combine(form.begins_at.data,
                                                datetime.min.time())
        if form.ends_at.unlimited.data:
            membership.ends_at = None
        else:
            membership.ends_at = datetime.combine(form.ends_at.date.data,
                                                  datetime.min.time())

        message = (u"hat die Mitgliedschaft des Nutzers in der Gruppe '{}' "
                   u"bearbeitet.".format(membership.group.name))
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


@bp.route('/<int:user_id>/edit_name', methods=['GET', 'POST'])
@access.require('user_change')
def edit_name(user_id):
    user = get_user_or_404(user_id)
    form = UserEditNameForm()

    if not form.is_submitted():
        form.name.data = user.name

    if form.validate_on_submit():
        edited_user = lib.user.edit_name(user, form.name.data, current_user)
        session.session.commit()

        flash(u'Benutzername geändert', 'success')
        return redirect(url_for('.user_show', user_id=edited_user.id))

    return render_template('user/user_edit_name.html', user_id=user_id,
        form=form)


@bp.route('/<int:user_id>/edit_email', methods=['GET', 'POST'])
@access.require('user_change')
def edit_email(user_id):
    user = get_user_or_404(user_id)
    form = UserEditEMailForm()

    if not form.is_submitted():
        form.email.data = user.email

    if form.validate_on_submit():
        edited_user = lib.user.edit_email(user, form.email.data, current_user)
        session.session.commit()

        flash(u'E-Mail-Adresse geändert', 'success')
        return redirect(url_for('.user_show', user_id=edited_user.id))

    return render_template('user/user_edit_email.html', user_id=user_id,
        form=form)


@bp.route('/search', methods=['GET', 'POST'])
@nav.navigate(u"Suchen")
def search():
    form = UserSearchForm()
    if form.validate_on_submit():
        return render_template('user/user_search.html',
                               page_title=u"Suchergebnis",
                               form=form)
    # apply args given in direct GET-link
    if request.args.get('id'):
        form.userid.data = request.args.get('id')
    if request.args.get('name'):
        form.name.data = request.args.get('name')
    if request.args.get('login'):
        form.login.data = request.args.get('login')
    return render_template('user/user_search.html', form=form)


@bp.route('/search/results')
def search_results():
    user_id = request.args.get('userid')
    name = request.args.get('name')
    login = request.args.get('login')
    result = User.q
    if user_id:
        result = result.filter(User.id == user_id)
    if name:
        result = result.filter(User.name.ilike("%{}%".format(name)))
    if login:
        result = result.filter(User.login.ilike("%{}%".format(login)))
    return jsonify(items=[{
            'id': found_user.id,
            'name': {'title': found_user.name,
                     'href': url_for(".user_show", user_id=found_user.id)},
            'login': found_user.login,
            'hosts': ", ".join("{} ({})".format(
                host_cname_filter(user_host),
                host_name_filter(user_host)
            ) for user_host in found_user.user_hosts)
        } for found_user in result.all()] if user_id or name or login else [])


@bp.route('/json/groups')
@access.require('groups_show')
def json_groups():
    groups = []
    group_type = request.args.get("group_type", 0, type=str)
    if group_type == 'traff':
        groups = [(entry.id, entry.name) for entry in TrafficGroup.q.all()]
    elif group_type == 'prop':
        groups = [(entry.id, entry.name) for entry in PropertyGroup.q.all()]

    return jsonify(dict(items=groups))


@bp.route('/by_group', methods=['GET', 'POST'])
@nav.navigate(u"Nach Gruppe")
def show_by_group():
    form = UserSelectGroupForm()

    if form.validate_on_submit():
        group_id = form.group.data
        if form.group_type.data == 'traff':
            return redirect(url_for(".list_users_by_traffic_group",
                                    traffic_group_id=group_id))
        elif form.group_type.data == 'prop':
            return redirect(url_for(".list_users_by_property_group",
                                    property_group_id=group_id))

    return render_template('user/list_groups.html', groups_form=form)


@bp.route('/by_group/property/<int:property_group_id>')
def list_users_by_property_group(property_group_id):
    property_group = PropertyGroup.q.get(property_group_id)
    user_list = []
    for entry in Membership.q.join(PropertyGroup).filter(
                     PropertyGroup.id == property_group_id).all():
        user_list.append(User.q.get(entry.user_id))

    return render_template('user/user_show_by_group.html',
                           group_name=property_group.name,
                           users=user_list)


@bp.route('/by_group/traffic/<int:traffic_group_id>')
def list_users_by_traffic_group(traffic_group_id):
    traffic_group = TrafficGroup.q.get(traffic_group_id)
    user_list = []
    for entry in Membership.q.join(PropertyGroup).filter(
                     PropertyGroup.id == traffic_group_id).all():
        user_list.append(User.q.get(entry.user_id))

    return render_template('user/user_show_by_group.html',
                           group_name=traffic_group.name,
                           users=user_list)


@bp.route('/<int:user_id>/suspend', methods=['GET', 'POST'])
@access.require('user_change')
def suspend(user_id):
    form = UserSuspendForm()
    myUser = User.q.get(user_id)
    if form.validate_on_submit():
        if form.ends_at.unlimited.data:
            ends_at = None
        else:
            ends_at = datetime.combine(form.ends_at.date.data, time(0))

        try:
            during = closedopen(session.utcnow(), ends_at)
            blocked_user = lib.user.suspend(
                user=myUser,
                reason=form.reason.data,
                processor=current_user,
                during=during)
            session.session.commit()
        except ValueError as e:
            flash(str(e), 'error')
        else:
            flash(u'Nutzer gesperrt', 'success')
            return redirect(url_for('.user_show', user_id=user_id))
    return render_template('user/user_block.html', form=form, user_id=user_id)


@bp.route('/<int:user_id>/unblock', methods=['GET', 'POST'])
@access.require('user_change')
def unblock(user_id):
    user = User.q.get(user_id)

    if user.member_of(config.violation_group) == False:
        flash(u"Nutzer {} ist nicht gesperrt!".format(
            user_id), 'error')
        return abort(404)

    try:
        unblocked_user = lib.user.unblock(
            user=user,
            processor=current_user)
        session.session.commit()
    except ValueError as e:
        flash(str(e), 'error')
    else:
        flash(u'Nutzer entsperrt', 'success')
        return redirect(url_for('.user_show', user_id=user_id))


@bp.route('/<int:user_id>/move_out', methods=['GET', 'POST'])
@access.require('user_change')
def move_out(user_id):
    form = UserMoveOutForm()
    user = get_user_or_404(user_id)

    if not user.member_of(config.member_group):
        flash("Nutzer {} ist aktuell nirgends eingezogen!".
              format(user_id), 'error')
        abort(404)

    if form.validate_on_submit():
        lib.user.move_out(user=user, comment=form.comment.data,
                          processor=current_user,
                          # when=datetime.combine(form.when.data, time(0))
                          when=session.utcnow())
        session.session.commit()
        flash(u'Nutzer wurde ausgezogen', 'success')
        return redirect(url_for('.user_show', user_id=user.id))
    return render_template('user/user_moveout.html', form=form, user_id=user_id)


@bp.route('/<int:user_id>/move_back_in', methods=['GET', 'POST'])
@access.require('user_change')
def move_back_in(user_id):
    form = UserMoveBackInForm()
    user = get_user_or_404(user_id)

    if user.member_of(config.member_group):
        flash("Nutzer {} ist nicht ausgezogen!".format(user_id), 'error')
        abort(404)

    if form.validate_on_submit():
        lib.user.move_back_in(
            user=user,
            building=form.building.data,
            level=form.level.data,
            room_number=form.room_number.data,
            mac=form.mac.data,
            processor=current_user,
        )
        session.session.commit()
        flash("Nutzer wurde wieder eingezogen", 'success')
        return redirect(url_for('.user_show', user_id=user_id))

    return render_template('user/user_move_back_in.html', form=form, user_id=user_id)


@bp.route('/<int:user_id>/change_mac/<int:user_interface_id>', methods=['GET', 'POST'])
@access.require('user_mac_change')
def change_mac(user_id, user_interface_id):
    form = InterfaceChangeMacForm()
    my_interface = UserInterface.q.get(user_interface_id)
    if not form.is_submitted():
        form.mac.data = my_interface.mac
    if form.validate_on_submit():
        changed_interface = lib_change_mac(interface=my_interface,
            mac=form.mac.data,
            processor=current_user)
        flash(u'Mac geändert', 'success')
        session.session.commit()
        return redirect(url_for('.user_show', user_id=changed_interface.host.owner.id))
    return render_template('user/change_mac.html',
                           form=form, user_id=user_id,
                           user_interface_id=user_interface_id)
