# -*- coding: utf-8 -*-
"""
    web.blueprints.dormitories
    ~~~~~~~~~~~~~~

    This module defines view functions for /dormitories
    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, flash, redirect, render_template, url_for
from pycroft.helpers import dormitory
from pycroft.lib.dormitory import create_dormitory, create_room, delete_room
from pycroft.model.session import session
from pycroft.model.dormitory import Room, Dormitory
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.dormitories.forms import RoomForm, DormitoryForm

bp = Blueprint('dormitories', __name__, )
nav = BlueprintNavigation(bp, "Wohnheime")


@bp.route('/')
def overview():
    dormitories_list = Dormitory.q.all()
    dormitories_list = dormitory.sort_dormitories(dormitories_list)
    return render_template('dormitories/overview.html',
        dormitories=dormitories_list)


@bp.route('/')
@nav.navigate(u"Wohnheime")
def dormitories():
    dormitories_list = Dormitory.q.all()
    dormitories_list = dormitory.sort_dormitories(dormitories_list)
    return render_template('dormitories/dormitories_list.html',
        dormitories=dormitories_list)


@bp.route('/show/<dormitory_id>')
def dormitory_show(dormitory_id):
    dormitory = Dormitory.q.get(dormitory_id)
    rooms_list = dormitory.rooms
    return render_template('dormitories/dormitory_show.html',
        page_title=u"Wohnheim " + dormitory.short_name, rooms=rooms_list)


@bp.route('/create', methods=['GET', 'POST'])
@nav.navigate(u"Neues Wohnheim")
def dormitory_create():
    form = DormitoryForm()
    if form.validate_on_submit():
        create_dormitory(short_name=form.short_name.data,
            street=form.street.data, number=form.number.data)
        flash(u'Wohnheim angelegt', 'success')
        return redirect(url_for('.dormitories'))
    return render_template('dormitories/dormitory_create.html', form=form)


@bp.route('/room/delete/<room_id>')
def room_delete(room_id):
    delete_room(room_id)
    flash(u'Raum gelöscht', 'success')
    return redirect(url_for('.dormitories'))


@bp.route('/room/show/<room_id>')
def room_show(room_id):
    room = Room.q.get(room_id)
    return render_template('dormitories/room_show.html',
        page_title=u"Raum " + str(room.dormitory.short_name) + u" " + \
                   str(room.level) + u"-" + str(room.number), room=room)


@bp.route('/room/create', methods=['GET', 'POST'])
@nav.navigate(u"Neuer Raum")
def room_create():
    form = RoomForm()
    if form.validate_on_submit():
        room = create_room(
            number=form.number.data,
            level=form.level.data,
            inhabitable=form.inhabitable.data,
            dormitory_id=form.dormitory_id.data.id)
        flash(u'Raum angelegt', 'success')
        return redirect(url_for('.room_show', room_id=room.id))
    return render_template('dormitories/dormitory_create.html', form=form)


# ToDo: Review this!
@bp.route('/levels/<int:dormitory_id>')
def dormitory_levels(dormitory_id):
    dormitory = Dormitory.q.get(dormitory_id)
    rooms_list = session.query(Room.level.label('level')).filter_by(
        dormitory_id=dormitory_id).order_by(Room.level).distinct()
    levels_list = [room.level for room in rooms_list]

    return render_template('dormitories/levels.html',
        levels=levels_list, dormitory_id=dormitory_id, dormitory=dormitory,
        page_title=u"Etagen Wohnheim %s" % dormitory.short_name)


# ToDo: Review this!
@bp.route('/levels/<int:dormitory_id>/rooms/<int:level>')
def dormitory_level_rooms(dormitory_id, level):
    dormitory = Dormitory.q.get(dormitory_id)
    rooms_list = Room.q.filter_by(
        dormitory_id=dormitory_id, level=level).order_by(Room.number)

    level_l0 = "%02d" % level

    #TODO depending on, whether a user is living in the room, the room is
    # a link to the user. If there is more then one user, the room is
    # duplicated
    return render_template('dormitories/rooms.html', rooms=rooms_list, level=level_l0,
                           dormitory=dormitory, page_title=u"Zimmer der Etage %d des Wohnheims %s" % (level,
                                                              dormitory.short_name))