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
import re
from difflib import SequenceMatcher
from itertools import chain
from functools import partial

from flask import (
    Blueprint, Markup, abort, flash, jsonify, redirect, render_template,
    request, url_for, session as flask_session, make_response)
import operator
from sqlalchemy import Text
import uuid
from sqlalchemy import Text, and_
from wtforms.widgets import HTMLString

from pycroft import lib, config
from pycroft.helpers.interval import closed, closedopen
from pycroft.helpers.net import mac_regex, ip_regex
from pycroft.lib.finance import get_typed_splits
from pycroft.lib.net import SubnetFullException, MacExistsException
from pycroft.lib.host import change_mac as lib_change_mac
from pycroft.lib.user import encode_type1_user_id, encode_type2_user_id, \
    traffic_balance_expr, generate_user_sheet
from pycroft.lib.membership import make_member_of
from pycroft.lib.traffic import effective_traffic_group, NoTrafficGroup
from pycroft.model import session
from pycroft.model.traffic import TrafficVolume, TrafficCredit, TrafficBalance
from pycroft.model.facilities import Room
from pycroft.model.host import Host, Interface, IP, Interface
from pycroft.model.user import User, Membership, PropertyGroup, TrafficGroup
from pycroft.model.finance import Split
from pycroft.model.types import InvalidMACAddressException
from sqlalchemy.sql.expression import or_, func, cast
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.user.forms import UserSearchForm, UserCreateForm, \
    HostCreateForm, UserLogEntry, UserAddGroupMembership, UserMoveForm, \
    UserEditNameForm, UserEditEMailForm, UserSuspendForm, UserMoveOutForm, \
    InterfaceChangeMacForm, UserEditGroupMembership, UserSelectGroupForm, \
    UserResetPasswordForm, UserMoveInForm, UserEditBirthdateForm
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

    return make_pdf_response(generate_user_sheet(user, plain_password="********"),
                             filename='user_sheet_plain_{}.pdf'.format(user_id))


@bp.route('/json/search')
def json_search():
    user_id = request.args.get('id')
    name = request.args.get('name')
    login = request.args.get('login')
    mac = request.args.get('mac')
    ip_address = request.args.get('ip_address')
    traffic_group_id = request.args.get('traffic_group_id')
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

    search_for_tg = traffic_group_id is not None and traffic_group_id != "" \
        and traffic_group_id != "__None"

    if search_for_pg or search_for_tg:
        result = result.join(Membership)
        result = result.filter(or_(
                            Membership.ends_at.is_(None),
                            Membership.ends_at > datetime.today())) \
                       .filter(or_(
                            Membership.begins_at.is_(None),
                            Membership.begins_at < datetime.today()))

        try:
            result_pg, result_tg = None, None

            if search_for_pg:
                pg_id = int(property_group_id)
                result_pg = result.join(PropertyGroup, PropertyGroup.id == Membership.group_id) \
                                  .filter(PropertyGroup.id == pg_id)
                if not search_for_tg:
                    result = result_pg
            if search_for_tg:
                tg_id = int(traffic_group_id)
                result_tg = result.join(TrafficGroup, TrafficGroup.id == Membership.group_id) \
                                  .filter(TrafficGroup.id == tg_id)
                if not search_for_pg:
                    result = result_tg

            if search_for_pg and search_for_tg:
                result = result_pg.intersect(result_tg)
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
            'href': '/user/' + str(found_user.id),
            'title': found_user.name
        },
        'login': found_user.login,
        'room_id': found_user.room_id if found_user.room_id is not None else None
    } for found_user in (result.all() if result.count() < count_no_filter else [])])


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

    balance = -user.account.balance
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
    try:
        traffic_group_name = effective_traffic_group(user).name
    except NoTrafficGroup:
        traffic_group_name = None
    try:
        if flask_session['user_sheet'] and lib.user.get_user_sheet(flask_session['user_sheet']):
            flash(Markup(u'Es ist ein <a href="{}">Nutzerdatenblatt</a> verfügbar!'.format(
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
        balance=balance,
        hosts_rooms={host.room for host in user.hosts},
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
        effective_traffic_group_name=traffic_group_name,
        is_blocked=is_blocked,
        granted_properties=sorted(p.property_name for p in user.current_properties),
        revoked_properties=sorted(
            p.property_name
            for p in set(user.current_properties_maybe_denied) -set(user.current_properties)
        )
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
    for user_host in User.q.get(user_id).hosts:
        if user_host.room:
            patch_ports = user_host.room.connected_patch_ports
            switches = ', '.join(p.switch_port.switch.name for p in patch_ports)
            ports = ', '.join(p.switch_port.name for p in patch_ports)
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
                Membership.begins_at <= session.utcnow())
        ).filter(
            # it is important to use == here, "is" does NOT work
            or_(Membership.ends_at == None,
                Membership.ends_at > session.utcnow())
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

    if membership is None:
        flash(u"Gruppenmitgliedschaft mit ID {} existiert nicht!".format(membership.id), 'error')
        abort(404)

    membership.disable()

    if membership.user.id != user_id:
        flash(u"Gruppenmitgliedschaft {} gehört nicht zu Nutzer {}!".format(membership.id, user_id), 'error')
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
    def traffic_events_as_json(model):
        result = model.q.filter(
            model.user_id == user_id,
            model.timestamp > traffic_timespan).order_by(
            model.timestamp)
        result = json_agg(result).one()[0]
        return result if result is not None else []

    # sum traffic balance up until the beginning of traffic_timespan
    traffic_balance = session.session.query(traffic_balance_expr(
        datetime.combine(traffic_timespan, time()) - timedelta(
            microseconds=1))).filter(User.id == user_id).scalar()

    credit_limit = session.session.execute(User.active_traffic_groups().where(
        User.id == user_id).with_only_columns(
        [func.max(TrafficGroup.credit_limit)])).scalar()

    return jsonify(
        items={
            'debits': traffic_events_as_json(TrafficVolume),
            'credits': traffic_events_as_json(TrafficCredit),
            'balance': traffic_balance,
            'credit_limit': credit_limit
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


def validate_unique_mac(form, field):
    if re.match(mac_regex, field.data):
        interface_existing = Interface.q.filter_by(mac=field.data).first()

        if interface_existing is not None and not form.annex.data:
            owner = interface_existing.host.owner

            return HTMLString("MAC bereits in Verwendung!<br/>Nutzer: " +
                              "<a target=\"_blank\" href=\"" +
                              url_for("user.user_show", user_id=owner.id) +
                              "#hosts\">" + owner.name + "</a>")


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate(u"Anlegen")
@access.require('user_change')
def create():
    form = UserCreateForm()

    if form.is_submitted():
        unique_name_error = validate_unique_name(form, form.name)
        unique_email_error = validate_unique_email(form, form.email)
        unique_mac_error = validate_unique_mac(form, form.mac)

    if form.validate_on_submit() and not (unique_name_error or
                                          unique_email_error or
                                          unique_mac_error):
        try:
            new_user, plain_password = lib.user.create_member(
                name=form.name.data,
                login=form.login.data,
                processor=current_user,
                email=form.email.data,
                birthdate=form.birthdate.data
            )

            if form.mac.data and form.building.data and form.level.data \
                    and form.room_number.data and form.birthdate.data:
                lib.user.move_in(
                    user=new_user,
                    building=form.building.data, level=form.level.data,
                    room_number=form.room_number.data,
                    mac=form.mac.data,
                    processor=current_user,
                    host_annex=form.annex.data
                )

            sheet = lib.user.store_user_sheet(new_user, plain_password)
            session.session.commit()

            flask_session['user_sheet'] = sheet.id
            flash(Markup(u'Benutzer angelegt. <a href="{}">Nutzerdatenblatt</a> verfügbar!'
                         .format(url_for('.user_sheet'))), 'success')
            return redirect(url_for('.user_show', user_id=new_user.id))

        except (MacExistsException,
                SubnetFullException,
                InvalidMACAddressException) as error:
            flash(str(error), 'error')
            session.session.rollback()

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
            edited_user = lib.user.move(user, form.building.data,
                form.level.data, form.room_number.data, current_user)
            session.session.commit()

            flash(u'Benutzer umgezogen', 'success')
            return redirect(url_for('.user_show', user_id=edited_user.id))

    if not form.is_submitted() or refill_form_data:
        if user.room is not None:
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
            "begins_at": None if membership.begins_at is None else membership.begins_at.date(),
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


@bp.route('/<int:user_id>/edit_birthdate', methods=['GET', 'POST'])
@access.require('user_change')
def edit_birthdate(user_id):
    user = get_user_or_404(user_id)
    form = UserEditBirthdateForm()

    if not form.is_submitted():
        if user.birthdate is None:
            form.birthdate.data = user.birthdate
        else:
            form.birthdate.data = user.birthdate

    if form.validate_on_submit():
        edited_user = lib.user.edit_birthdate(user, form.birthdate.data, current_user)
        session.session.commit()

        flash(u'Geburtsdatum geändert', 'success')
        return redirect(url_for('.user_show', user_id=edited_user.id))

    return render_template('user/user_edit_birthdate.html', user_id=user_id,
        form=form)


@bp.route('/search', methods=['GET', 'POST'])
@nav.navigate(u"Suchen")
def search():
    form = UserSearchForm()

    return render_template('user/user_search.html', form=form)


@bp.route('/<int:user_id>/reset_password', methods=['GET', 'POST'])
@access.require('user_change')
def reset_password(user_id):
    form = UserResetPasswordForm()
    myUser = User.q.get(user_id)
    if form.validate_on_submit():
        plain_password = lib.user.reset_password(myUser, processor=current_user)
        sheet = lib.user.store_user_sheet(myUser, plain_password)
        session.session.commit()

        flask_session['user_sheet'] = sheet.id
        flash(Markup(u'Passwort erfolgreich zurückgesetzt.'),
              'success')
        return redirect(url_for('.user_show', user_id=user_id))
    return render_template('user/user_reset_password.html', form=form, user_id=user_id)


@bp.route('/<int:user_id>/suspend', methods=['GET', 'POST'])
@access.require('user_change')
def suspend(user_id):
    form = UserSuspendForm()
    myUser = get_user_or_404(user_id)
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
    user = get_user_or_404(user_id)

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
        lib.user.move_in(
            user=user,
            building=form.building.data,
            level=form.level.data,
            room_number=form.room_number.data,
            mac=form.mac.data,
            birthdate=form.birthdate.data,
            processor=current_user
        )
        session.session.commit()
        flash("Nutzer wurde eingezogen", 'success')
        return redirect(url_for('.user_show', user_id=user_id))
    else:
        form.birthdate.data = user.birthdate

    return render_template('user/user_move_in.html', form=form, user_id=user_id)


@bp.route('/<int:user_id>/change_mac/<int:user_interface_id>', methods=['GET', 'POST'])
@access.require('user_mac_change')
def change_mac(user_id, user_interface_id):
    user = get_user_or_404(user_id)

    form = InterfaceChangeMacForm()
    my_interface = Interface.q.get(user_interface_id)

    if my_interface is None:
        flash(u"Interface mit ID {} existiert nicht!".format(user_interface_id), 'error')
        abort(404)

    if my_interface.host.owner.id != user_id:
        flash(u"Interface {} gehört nicht zu Nutzer {}!".format(my_interface.id, user.id), 'error')
        return abort(404)

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
                           form=form, user_id=user.id,
                           user_interface_id=my_interface.id)


@bp.route('/<int:user_id>/reset_credit')
@access.require('user_change')
def reset_credit(user_id):
    user = get_user_or_404(user_id)
    try:
        lib.traffic.reset_credit(user, processor=current_user)
    except ValueError as e:
        flash(str(e), 'error')
    else:
        session.session.commit()
        flash("Traffic erfolgreich resetted", 'success')

    return redirect(url_for('user.user_show', user_id=user_id))
