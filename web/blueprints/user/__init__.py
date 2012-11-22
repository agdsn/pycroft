# -*- coding: utf-8 -*-
"""
    web.blueprints.user
    ~~~~~~~~~~~~~~

    This module defines view functions for /user

    :copyright: (c) 2012 by AG DSN.
"""
from flask import Blueprint, render_template, flash, redirect, url_for,\
    request, jsonify, abort
from pycroft import lib
from pycroft.helpers import host_helper
from pycroft.model.dormitory import Room
from pycroft.model.hosts import Host, UserNetDevice, Ip
from pycroft.model.logging import UserLogEntry
from pycroft.model.session import session
from pycroft.model.user import User
from pycroft.model.properties import Membership
from pycroft.model.accounting import TrafficVolume
from sqlalchemy.sql.expression import or_
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.user.forms import UserSearchForm, UserCreateForm,\
    hostCreateForm, userLogEntry, UserAddGroupMembership, UserMoveForm,\
    UserEditNameForm, UserEditEMailForm, UserBanForm, UserMoveoutForm, \
    NetDeviceChangeMacForm
from web.blueprints.access import login_required, BlueprintAccess
from datetime import datetime, timedelta, time
from flask.ext.login import current_user

bp = Blueprint('user', __name__, )
nav = BlueprintNavigation(bp, "Nutzer")
access = BlueprintAccess(bp)


@bp.errorhandler(404)
def error_404(e):
    return render_template('errorpages/404.html', ref=request.referrer)


@bp.route('/')
@nav.navigate(u"Übersicht")
def overview():
    return redirect(url_for("dormitories.overview"))


@bp.route('/show/<user_id>', methods=['GET', 'POST'])
@access.login_required
def user_show(user_id):

    user = User.q.get(user_id)
    if user is None:
        flash(u"Nutzer mit ID %s existiert nicht!" % (user_id,), 'error')
        abort(404)

    room = Room.q.get(user.room_id)
    form = userLogEntry()

    if form.validate_on_submit():
        newUserLogEntry = UserLogEntry(message=form.message.data,
            timestamp=datetime.now(),
            author_id=current_user.id, user_id=user_id)
        session.add(newUserLogEntry)
        session.commit()
        flash(u'Kommentar hinzugefügt', 'success')

    user_log_list = user.user_log_entries[::-1]

    memberships = Membership.q.filter(Membership.user_id == user.id)
    memberships_active = memberships.filter(
        # it is important to use == here, "is" does NOT work
        or_(Membership.start_date == None,
            Membership.start_date <= datetime.now())
    ).filter(
        # it is important to use == here, "is" does NOT work
        or_(Membership.end_date == None,
            Membership.end_date > datetime.now())
    )

    return render_template('user/user_show.html',
        user=user, user_logs=user_log_list, room=room, form=form,
        memberships=memberships.all(),
        memberships_active=memberships_active.all())


@bp.route('/add_membership/<int:user_id>/', methods=['GET', 'Post'])
def add_membership(user_id):

    user = User.q.get(user_id)
    if user is None:
        flash(u"Nutzer mit ID %s existiert nicht!" % (user_id,), 'error')
        abort(404)

    form = UserAddGroupMembership()
    if form.validate_on_submit():
        newMembership = Membership(user=user, group=form.group_id.data,
            start_date=datetime.combine(form.begin_date.data,time(0)), end_date=datetime.combine(form.end_date.data,time(0)))
        newUserLogEntry = UserLogEntry(author_id=current_user.id,
            message=u"hat Nutzer zur Gruppe '%s' hinzugefügt." %
                    form.group_id.data.name,
            timestamp=datetime.now(), user_id=user_id)

        session.add(newMembership)
        session.add(newUserLogEntry)
        session.commit()
        flash(u'Nutzer wurde der Gruppe hinzugefügt.', 'success')

        return redirect(url_for(".user_show", user_id=user_id))

    return render_template('user/add_membership.html',
        page_title=u"Neue Gruppenmitgliedschaft für Nutzer %s" % user_id,
        user_id=user_id, form=form)


@bp.route('/delete_membership/<int:membership_id>')
def end_membership(membership_id):
    membership = Membership.q.get(membership_id)
    membership.disable()

    # ToDo: Make the log messages not Frontend specific (a helper?)
    newUserLogEntry = UserLogEntry(author_id=current_user.id,
        message=u"hat die Mitgliedschaft des Nutzers"
                u" in der Gruppe '%s' beendet." %
                membership.group.name,
        timestamp=datetime.now(), user_id=membership.user_id)

    session.add(newUserLogEntry)
    session.commit()
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
def json_trafficdata(user_id):
    traffic_timespan = datetime.now() - timedelta(days=7)

    trafficvolumes = session.query(
        TrafficVolume
    ).join(
        TrafficVolume.ip
    ).join(
        Ip.host
    ).filter(
        Host.user_id == user_id
    ).filter(
        TrafficVolume.timestamp > traffic_timespan)

    trafficvolume_in = trafficvolumes.filter(TrafficVolume.type == 'IN').all()
    trafficvolume_out = trafficvolumes.filter(TrafficVolume.type == 'OUT').all()

    tv_in = []
    for entry in trafficvolume_in:
        tv_in.append(entry.size / 1024 / 1024)
    tv_out = []
    for entry in trafficvolume_out:
        tv_out.append(entry.size / 1024 / 1024)

    trafficdata = [{ "name": 'Input', "data": tv_in, "stack": 0 },
            { "name": 'Output', "data": tv_out, "stack": 1 }]

    return jsonify({"series" : trafficdata})


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate(u"Anlegen")
@access.login_required
def create():
    form = UserCreateForm()
    if form.validate_on_submit():
        try:
            new_user = lib.user.moves_in(
                form.name.data, form.login.data, form.email.data,
                form.dormitory.data, form.level.data, form.room_number.data,
                form.host.data, form.mac.data, form.semester.data, current_user)

            flash(u'Benutzer angelegt', 'success')
            return redirect(url_for('.user_show', user_id = new_user.id))

        except host_helper.SubnetFullException, error:
            flash(u'Subnetz voll', 'error')

    return render_template('user/user_create.html', form = form)


@bp.route('/move/<int:user_id>', methods=['GET', 'POST'])
@access.login_required
def move(user_id):
    user = User.q.get(user_id)
    if user is None:
        flash(u"Nutzer mit ID %s existiert nicht!" % (user_id,), 'error')
        abort(404)

    form = UserMoveForm()

    if not form.is_submitted():
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

    if form.validate_on_submit():
        edited_user = lib.user.move(user, form.dormitory.data,
            form.level.data, form.room_number.data, current_user)

        flash(u'Benutzer umgezogen', 'success')
        return redirect(url_for('.user_show', user_id=edited_user.id))

    return render_template('user/user_move.html', user_id=user_id, form=form)


@bp.route('/edit_name/<int:user_id>', methods=['GET', 'POST'])
@access.login_required
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
@access.login_required
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


@bp.route('/host_create', methods=['GET', 'POST'])
@nav.navigate(u"Host erstellen")
def host_create():
    form = hostCreateForm()
    hostResult = Host.q.all()
    if form.validate_on_submit():
        myHost = Host(hostname=form.name.data)
        session.add(myHost)
        session.commit()
        flash(u'Host angelegt', 'success')
        return render_template('user/host_create.html', form=form,
            results=hostResult)
    return render_template('user/host_create.html', form=form,
        results=hostResult)

@bp.route('/ban/<int:user_id>', methods=['GET', 'POST'])
def ban_user(user_id):
    form = UserBanForm()
    myUser = User.q.get(user_id)
    if form.validate_on_submit():
        banned_user = lib.user.ban_user(user=myUser,
            date=form.date.data,
            reason=form.reason.data,
            processor=current_user)
        flash(u'Nutzer gesperrt', 'success')
        return redirect(url_for('.user_show', user_id=banned_user.id))
    return render_template('user/user_ban.html', form=form, user_id=user_id)

@bp.route('/user_moveout/<int:user_id>', methods=['GET', 'POST'])
def user_moveout(user_id):
    form = UserMoveoutForm()
    myUser = User.q.get(user_id)
    if myUser is None:
        flash(u"Nutzer mit ID %s existiert nicht!" % (user_id,), 'error')
        abort(404)
    if form.validate_on_submit():
        for membership in myUser.memberships:
            if membership.end_date > form.date.data:
                membership.end_date = form.date.data
        newUserLogEntry = UserLogEntry(author_id=current_user.id,
            message=u"wird zum %s komplett ausziehen." % form.date.data.strftime("%d.%m.%Y"),
            timestamp=datetime.now(), user_id=myUser.id)
        session.add(newUserLogEntry)
        session.commit()
        flash(u'Nutzer wurde ausgezogen', 'success')
        return redirect(url_for('.user_show', user_id=myUser.id))
    return render_template('user/user_moveout.html', form=form, user_id=user_id)

@bp.route('/change_mac/<int:user_net_device_id>', methods=['GET', 'POST'])
def change_mac(user_net_device_id):
    form = NetDeviceChangeMacForm()
    my_net_device = UserNetDevice.q.get(user_net_device_id)
    if not form.is_submitted():
        form.mac.data = my_net_device.mac
    if form.validate_on_submit():
        changed_net_device = lib.hosts.change_mac(net_device=my_net_device,
            mac=form.mac.data,
            processor=current_user)
        flash(u'Mac geändert', 'success')
        return redirect(url_for('.user_show', user_id=changed_net_device.host.user.id))
    return render_template('user/change_mac.html', form=form, user_net_device_id=user_net_device_id)