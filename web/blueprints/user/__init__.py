# -*- coding: utf-8 -*-
"""
    web.blueprints.user
    ~~~~~~~~~~~~~~

    This module defines view functions for /user

    :copyright: (c) 2012 by AG DSN.
"""
from itertools import chain
from flask import Blueprint, render_template, flash, redirect, url_for,\
    request, jsonify, abort
import operator
from pycroft import lib
from pycroft.helpers import host
from pycroft.model.dormitory import Room
from pycroft.model.host import Host, UserNetDevice, Ip
from pycroft.model.session import session
from pycroft.model.user import User
from pycroft.model.property import Membership, PropertyGroup, TrafficGroup
from pycroft.model.accounting import TrafficVolume
from sqlalchemy.sql.expression import or_, func
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.user.forms import UserSearchForm, UserCreateForm,\
    hostCreateForm, UserLogEntry, UserAddGroupMembership, UserMoveForm,\
    UserEditNameForm, UserEditEMailForm, UserBlockForm, UserMoveOutForm, \
    NetDeviceChangeMacForm, UserEditGroupMembership, UserSelectGroupForm
from web.blueprints.access import BlueprintAccess
from datetime import datetime, timedelta, time
from flask.ext.login import current_user

bp = Blueprint('user', __name__, )
access = BlueprintAccess(bp, ['user_show'])
nav = BlueprintNavigation(bp, "Nutzer", blueprint_access=access)


@bp.route('/')
@nav.navigate(u"Übersicht")
def overview():
    return redirect(url_for("dormitories.overview"))


@bp.route('/json/search')
@access.require('user_show')
def json_search():
    query = request.args['query']
    results = session.query(User.id, User.login, User.name).filter(or_(
        func.lower(User.name).like(func.lower(u"%{0}%".format(query))),
        func.lower(User.login).like(func.lower(u"%{0}%".format(query))),
        User.id.like(u"{0}%".format(query))
    )).all()
    users = [{"id": user_id, "login": login, "name": name}
             for user_id, login, name in results]
    return jsonify(users=users)


@bp.route('/show/<user_id>', methods=['GET', 'POST'])
@access.require('user_show')
def user_show(user_id):

    user = User.q.get(user_id)
    if user is None:
        flash(u"Nutzer mit ID %s existiert nicht!" % (user_id,), 'error')
        abort(404)

    room = Room.q.get(user.room_id)
    form = UserLogEntry()

    now = datetime.utcnow()
    if form.validate_on_submit():
        lib.logging.create_user_log_entry(message=form.message.data,
            timestamp=now,
            author=current_user,
            user=user)
        flash(u'Kommentar hinzugefügt', 'success')

    log_list = sorted(
        chain(user.user_log_entries, room.room_log_entries),
        key=operator.attrgetter("timestamp"), reverse=True
    )
    user_log_list = user.user_log_entries[::-1]
    room_log_list = room.room_log_entries[::-1]

    memberships = Membership.q.filter(Membership.user_id == user.id)
    memberships_active = memberships.filter(
        # it is important to use == here, "is" does NOT work
        or_(Membership.start_date == None,
            Membership.start_date <= now)
    ).filter(
        # it is important to use == here, "is" does NOT work
        or_(Membership.end_date == None,
            Membership.end_date > now)
    )

    return render_template('user/user_show.html',
        user=user,
        all_log=log_list,
        user_log=user_log_list,
        room_log=room_log_list,
        room=room,
        form=form,
        memberships=memberships.all(),
        memberships_active=memberships_active.all(),
        status=lib.user.determine_status(user))


@bp.route('/add_membership/<int:user_id>/', methods=['GET', 'Post'])
@access.require('groups_change_user')
def add_membership(user_id):

    user = User.q.get(user_id)
    if user is None:
        flash(u"Nutzer mit ID %s existiert nicht!" % (user_id,), 'error')
        abort(404)

    form = UserAddGroupMembership()
    if form.validate_on_submit():
        now = datetime.utcnow()
        if form.begin_date.data is not None:
            start_date = datetime.combine(form.begin_date.data, time(0))
        else:
            start_date = now
        if not form.unlimited.data:
            end_date = datetime.combine(form.end_date.data, time(0))
        else:
            end_date=None
        lib.property.create_membership(
            user=user,
            group=form.group_id.data,
            start_date=start_date,
            end_date=end_date)
        lib.logging.create_user_log_entry(author=current_user,
                message=u"hat Nutzer zur Gruppe '%s' hinzugefügt." %
                form.group_id.data.name,
                timestamp=now,
                user=user)

        flash(u'Nutzer wurde der Gruppe hinzugefügt.', 'success')

        return redirect(url_for(".user_show", user_id=user_id))

    return render_template('user/add_membership.html',
        page_title=u"Neue Gruppenmitgliedschaft für Nutzer %s" % user_id,
        user_id=user_id, form=form)


@bp.route('/delete_membership/<int:membership_id>')
@access.require('groups_change_user')
def end_membership(membership_id):
    membership = Membership.q.get(membership_id)
    membership.disable()

    # ToDo: Make the log messages not Frontend specific (a helper?)
    lib.logging.create_user_log_entry(author=current_user,
            message=u"hat die Mitgliedschaft des Nutzers"
                u" in der Gruppe '%s' beendet." %
                membership.group.name,
            timestamp=datetime.utcnow(),
            user=membership.user)

    flash(u'Mitgliedschaft in Gruppe beendet', 'success')
    return redirect(url_for(".user_show", user_id=membership.user_id))


@bp.route('/json/levels')
def json_levels():
    if not request.is_xhr:
        abort(404)
    dormitory_id = request.args.get('dormitory', 0, type=int)
    levels = session.query(Room.level.label('level')).filter_by(
        dormitory_id=dormitory_id).order_by(Room.level).distinct()
    return jsonify(dict(items=[entry.level for entry in levels]))


@bp.route('/json/rooms')
def json_rooms():
    if not request.is_xhr:
        abort(404)
    dormitory_id = request.args.get('dormitory', 0, type=int)
    level = request.args.get('level', 0, type=int)
    rooms = session.query(
        Room.number.label("room_num")).filter_by(
        dormitory_id=dormitory_id, level=level).order_by(
        Room.number).distinct()
    return jsonify(dict(items=[entry.room_num for entry in rooms]))


@bp.route('/json/traffic/<int:user_id>')
@bp.route('/json/traffic/<int:user_id>/<int:days>')
@access.require('user_show')
def json_trafficdata(user_id, days=7):
    """Generate a Highcharts compatible JSON file to use with traffic graphs.

    :param user_id:
    :param days: optional amount of days to be included
    :return: JSON with traffic data for INPUT and OUTPUT with [datetime, megabyte] tuples.
    """
    traffic_timespan = datetime.utcnow() - timedelta(days=days)

    # get all traffic volumes for the user in the timespan
    traffic_volumes = session.query(
        TrafficVolume
    ).join(
        TrafficVolume.ip
    ).join(
        Ip.host
    ).filter(
        Host.user_id == user_id
    ).filter(
        TrafficVolume.timestamp > traffic_timespan)

    # filter for INPUT and OUTPUT
    traffic_volume_in = traffic_volumes.filter(TrafficVolume.type == 'IN').all()
    traffic_volume_out = traffic_volumes.filter(TrafficVolume.type == 'OUT').all()

    # generate the data arrays which will be used in the JSON
    tv_in = []
    for volume in traffic_volume_in:
        tv_in.append([volume.timestamp, volume.size / 1024 / 1024])
    tv_out = []
    for volume in traffic_volume_out:
        tv_out.append([volume.timestamp, volume.size / 1024 / 1024])

    # reverse, so data is in chronological order
    for tv in (tv_in, tv_out):
        tv.reverse()

    return jsonify(
        series=[
            {"name": 'Input', "data": tv_in, "stack": 0},
            {"name": 'Output', "data": tv_out, "stack": 1}
        ]
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
                dormitory=form.dormitory.data, level=form.level.data,
                room_number=form.room_number.data,
                host_name=form.host.data, mac=form.mac.data,
                processor=current_user,
                email=form.email.data,
                moved_from_division=form.moved_from_division.data,
                already_paid_semester_fee=form.already_paid_semester_fee.data
            )

            flash(u'Benutzer angelegt', 'success')
            return redirect(url_for('.user_show', user_id = new_user.id))

        except host.MacExistsException, error:
            flash(u'Duplicate MAC address (already present on one of the connected subnets)', 'error')

        except host.SubnetFullException, error:
            flash(u'Subnetz voll', 'error')

    return render_template('user/user_create.html', form = form)


@bp.route('/move/<int:user_id>', methods=['GET', 'POST'])
@access.require('user_change')
def move(user_id):
    user = User.q.get(user_id)
    if user is None:
        flash(u"Nutzer mit ID %s existiert nicht!" % (user_id,), 'error')
        abort(404)

    form = UserMoveForm()

    refill_form_data = False
    if form.validate_on_submit():
        if user.room == Room.q.filter_by(
                number=form.room_number.data,
                level=form.level.data,
                dormitory_id=form.dormitory.data.id
            ).one():
            flash(u"Nutzer muss in anderes Zimmer umgezogen werden!", "error")
            refill_form_data = True
        else:
            edited_user = lib.user.move(user, form.dormitory.data,
                form.level.data, form.room_number.data, current_user)

            flash(u'Benutzer umgezogen', 'success')
            return redirect(url_for('.user_show', user_id=edited_user.id))

    if not form.is_submitted() or refill_form_data:
        form.dormitory.data = user.room.dormitory

        levels = session.query(Room.level.label('level')).filter_by(
            dormitory_id=user.room.dormitory.id).order_by(Room.level).distinct()

        form.level.choices = [(entry.level, str(entry.level)) for entry in
                                                              levels]
        form.level.data = user.room.level

        rooms = session.query(Room).filter_by(
            dormitory_id=user.room.dormitory.id,
            level=user.room.level
        ).order_by(Room.number).distinct()

        form.room_number.choices = [(entry.number, str(entry.number)) for entry
                                                                      in rooms]
        form.room_number.data = user.room

    return render_template('user/user_move.html', user_id=user_id, form=form)


@bp.route('edit_membership/<int:membership_id>', methods=['GET', 'POST'])
@access.require('groups_change_user')
def edit_membership(membership_id):
    membership = Membership.q.get(membership_id)

    if membership is None:
        flash(u"Gruppenmitgliedschaft mit ID %s existiert nicht!" % (
        membership_id), 'error')
        abort(404)

    form = UserEditGroupMembership()
    now = datetime.utcnow()
    if request.method == 'GET':
        form.begin_date.data = membership.start_date
        if membership.start_date < now:
            form.begin_date.disabled = True

        if membership.end_date is not None:
            form.end_date.data = membership.end_date

    if form.validate_on_submit():
        membership.start_date = datetime.combine(form.begin_date.data, datetime.min.time())
        if form.unlimited.data:
            membership.end_date = None
        else:
            membership.end_date = datetime.combine(form.end_date.data, datetime.min.time())

        session.commit()
        flash(u'Gruppenmitgliedschaft bearbeitet', 'success')
        lib.logging.create_user_log_entry(author=current_user,
            message=u"hat die Mitgliedschaft des Nutzers"
                u" in der Gruppe '%s' bearbeitet." %
                membership.group.name,
            timestamp=now,
            user=membership.user)
        return redirect(url_for('.user_show', user_id=membership.user_id))

    return render_template('user/user_edit_membership.html',
                           page_title=u"Mitgliedschaft %s für %s bearbeiten" % (membership.group.name, membership.user.name),
                           membership_id=membership_id,
                           user = membership.user,
                           form = form)


@bp.route('/edit_name/<int:user_id>', methods=['GET', 'POST'])
@access.require('user_change')
def edit_name(user_id):
    user = User.q.get(user_id)
    if user is None:
        flash(u"Nutzer mit ID %s existiert nicht!" % (user_id,), 'error')
        abort(404)

    form = UserEditNameForm()

    if not form.is_submitted():
        form.name.data = user.name

    if form.validate_on_submit():
        edited_user = lib.user.edit_name(user, form.name.data, current_user)

        flash(u'Benutzername geändert', 'success')
        return redirect(url_for('.user_show', user_id=edited_user.id))

    return render_template('user/user_edit_name.html', user_id=user_id,
        form=form)


@bp.route('/edit_email/<int:user_id>', methods=['GET', 'POST'])
@access.require('user_change')
def edit_email(user_id):
    user = User.q.get(user_id)
    if user is None:
        flash(u"Nutzer mit ID %s existiert nicht!" % (user_id,), 'error')
        abort(404)

    form = UserEditEMailForm()

    if not form.is_submitted():
        form.email.data = user.email

    if form.validate_on_submit():
        edited_user = lib.user.edit_email(user, form.email.data, current_user)

        flash(u'E-Mail-Adresse geändert', 'success')
        return redirect(url_for('.user_show', user_id=edited_user.id))

    return render_template('user/user_edit_email.html', user_id=user_id,
        form=form)


@bp.route('/search', methods=['GET', 'POST'])
@nav.navigate(u"Suchen")
@access.require('user_show')
def search():
    form = UserSearchForm()
    if form.validate_on_submit():
        userResult = User.q
        if len(form.userid.data):
            userResult = userResult.filter(User.id == form.userid.data)
        if len(form.name.data):
            userResult = userResult.filter(User.name.like('%' + form.name\
            .data + '%'))
        if len(form.login.data):
            userResult = userResult.filter(User.login == form.login.data)
        if not len(userResult.all()):
            flash(u'Benutzer nicht gefunden', 'error')
        return render_template('user/user_search.html',
            page_title=u"Suchergebnis",
            results=userResult.all(), form=form)
    return render_template('user/user_search.html', form=form)

@bp.route('/json/groups')
def json_groups():
    if not request.is_xhr:
        abort(404)
    groups = []
    group_type = request.args.get("group_type", 0, type=str)
    if group_type == 'traff':
        groups = [(entry.id, entry.name) for entry in TrafficGroup.q.all()]
    elif group_type == 'prop':
        groups = [(entry.id, entry.name) for entry in PropertyGroup.q.all()]

    return jsonify(dict(items=groups))


@bp.route('/show_by_group', methods=['GET', 'POST'])
@nav.navigate(u"Nach Gruppe")
@access.require('user_show')
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


@bp.route('/show_by_group/property/<int:property_group_id>')
@access.require('user_show')
def list_users_by_property_group(property_group_id):
    property_group = PropertyGroup.q.get(property_group_id)
    user_list = []
    for entry in Membership.q.join(PropertyGroup).filter(
                     PropertyGroup.id == property_group_id).all():
        user_list.append(User.q.get(entry.user_id))

    return render_template('user/user_show_by_group.html',
                           group_name=property_group.name,
                           users=user_list)


@bp.route('/show_by_group/traffic/<int:traffic_group_id>')
@access.require('user_show')
def list_users_by_traffic_group(traffic_group_id):
    traffic_group = TrafficGroup.q.get(traffic_group_id)
    user_list = []
    for entry in Membership.q.join(PropertyGroup).filter(
                     PropertyGroup.id == traffic_group_id).all():
        user_list.append(User.q.get(entry.user_id))

    return render_template('user/user_show_by_group.html',
                           group_name=traffic_group.name,
                           users=user_list)


@bp.route('/block/<int:user_id>', methods=['GET', 'POST'])
@access.require('user_change')
def block(user_id):
    form = UserBlockForm()
    myUser = User.q.get(user_id)
    if form.validate_on_submit():
        end_date = datetime.combine(form.date.data, time(0))
        if form.unlimited.data:
            end_date = None

        try:
            blocked_user = lib.user.block(
                user=myUser,
                date=end_date,
                reason=form.reason.data,
                processor=current_user)
        except ValueError as e:
            flash(e.message, 'error')
        else:
            flash(u'Nutzer gesperrt', 'success')
            return redirect(url_for('.user_show', user_id=user_id))
    return render_template('user/user_block.html', form=form, user_id=user_id)


@bp.route('/move_out/<int:user_id>', methods=['GET', 'POST'])
@access.require('user_change')
def move_out(user_id):
    form = UserMoveOutForm()
    myUser = User.q.get(user_id)
    if myUser is None:
        flash(u"Nutzer mit ID %s existiert nicht!" % (user_id,), 'error')
        abort(404)
    if form.validate_on_submit():
        lib.user.move_out(
            user=myUser,
            date=datetime.combine(form.date.data, time(0)),
            processor=current_user,
            comment=form.comment.data
        )
        flash(u'Nutzer wurde ausgezogen', 'success')
        return redirect(url_for('.user_show', user_id=myUser.id))
    return render_template('user/user_moveout.html', form=form, user_id=user_id)


@bp.route('/change_mac/<int:user_net_device_id>', methods=['GET', 'POST'])
@access.require('user_mac_change')
def change_mac(user_net_device_id):
    form = NetDeviceChangeMacForm()
    my_net_device = UserNetDevice.q.get(user_net_device_id)
    if not form.is_submitted():
        form.mac.data = my_net_device.mac
    if form.validate_on_submit():
        changed_net_device = lib.host.change_mac(net_device=my_net_device,
            mac=form.mac.data,
            processor=current_user)
        flash(u'Mac geändert', 'success')
        return redirect(url_for('.user_show', user_id=changed_net_device.host.user.id))
    return render_template('user/change_mac.html', form=form, user_net_device_id=user_net_device_id)


@bp.route('/move_out_tmp/<int:user_id>', methods=['GET', 'POST'])
@access.require('user_change')
def move_out_tmp(user_id):
    form = UserMoveOutForm()
    my_user = User.q.get(user_id)
    if my_user is None:
        flash(u"Nutzer mit ID %s existiert nicht!" % (user_id,), 'error')
        abort(404)
    if form.validate_on_submit():
        changed_user = lib.user.move_out_tmp(
            user=my_user,
            date=datetime.combine(form.date.data,time(0)),
            comment=form.comment.data,
            processor=current_user
        )
        flash(u'Nutzer zieht am %s vorübegehend aus' % form.date.data,
            'success')
        return redirect(url_for('.user_show', user_id=changed_user.id))
    return render_template('user/user_moveout.html', form=form, user_id=user_id)


@bp.route('/is_back/<int:user_id>')
@access.require('user_change')
def is_back(user_id):
    my_user = User.q.get(user_id)
    changed_user = lib.user.is_back(user=my_user, processor=current_user)
    flash(u'Nutzer ist zurück', 'success')
    return redirect(url_for('.user_show', user_id=changed_user.id))
