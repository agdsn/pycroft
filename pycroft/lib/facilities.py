from collections import defaultdict

from sqlalchemy import func, and_
from sqlalchemy.orm import aliased, contains_eager, joinedload

from pycroft.lib.logging import log_room_event, log_event
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.host import Host
from pycroft.model.session import with_transaction
from pycroft.model.user import User


class RoomAlreadyExistsException(Exception):
    pass


def get_overcrowded_rooms(building_id=None):
    """
    :param building_id: Limit to rooms of the building.
    Returns a dict of overcrowded rooms with their inhabitants
    :return: dict
    """

    oc_rooms_filter = []
    if building_id is not None:
        oc_rooms_filter.append(Room.building_id == building_id)

    # rooms containing multiple users each of which has a host in the room
    oc_rooms_query = (
        Room.q.join(User)
            .join(Host).filter(User.room_id == Host.room_id)
            .filter(*oc_rooms_filter)
            .group_by(Room.id).having(func.count(User.id) > 1)
            .subquery()
    )

    user = aliased(User)

    # room can be extracted from the subquery
    oc_room = contains_eager(user.room, alias=oc_rooms_query)

    query = (
        session.session.query(user)
            # only include users living in overcrowded rooms
            .join(oc_rooms_query)
            # only include users that have a host in their room
            .join(Host,
                  and_(user.id == Host.owner_id, user.room_id == Host.room_id))
            .options(oc_room)
            .options(oc_room.joinedload(Room.building))
            .options(joinedload(user.current_properties))
    )

    rooms = defaultdict(list)
    for user in query.all():
        rooms[user.room.id].append(user)

    return rooms


@with_transaction
def create_room(building, level, number, processor, inhabitable=True):
    if Room.q.filter_by(number=number, level=level, building=building).first() is not None:
        raise RoomAlreadyExistsException()

    room = Room(number=number,
                level=level,
                inhabitable=inhabitable,
                building=building)

    log_room_event("Room created.", processor, room)

    return room


@with_transaction
def edit_room(room, number, inhabitable, processor):
    if room.number != number:
        if Room.q.filter_by(number=number, level=room.level, building=room.building).filter(Room.id!=room.id).first() is not None:
            raise RoomAlreadyExistsException()

        log_room_event("Renamed room from {} to {}.".format(room.number, number), processor, room)

        room.number = number

    if room.inhabitable != inhabitable:
        log_room_event("Changed inhabitable status to {}.".format(str(inhabitable)), processor, room)

        room.inhabitable = inhabitable

    return room


def get_room(building_id, level, room_number):
    return Room.q.filter_by(number=room_number,
                            level=level, building_id=building_id).one_or_none()
