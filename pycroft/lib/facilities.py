import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, and_, distinct, literal_column
from sqlalchemy.orm import aliased, contains_eager, joinedload

from pycroft.helpers.i18n import deferred_gettext
from pycroft.lib.logging import log_room_event, log_event, log_user_event
from pycroft.model import session
from pycroft.model.address import Address
from pycroft.model.facilities import Room, Building
from pycroft.model.host import Host
from pycroft.model.session import with_transaction
from pycroft.model.user import User


logger = logging.getLogger(__name__)


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
            .group_by(Room.id).having(func.count(distinct(User.id)) > 1)
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
def create_room(building, level, number, processor, address,
                inhabitable=True, vo_suchname: Optional[str] = None):
    if Room.q.filter_by(number=number, level=level, building=building).first() is not None:
        raise RoomAlreadyExistsException

    if vo_suchname and Room.q.filter_by(swdd_vo_suchname=vo_suchname).first() is not None:
        raise RoomAlreadyExistsException

    room = Room(number=number,
                level=level,
                inhabitable=inhabitable,
                building=building,
                address=address,
                swdd_vo_suchname=vo_suchname)

    log_room_event("Room created.", processor, room)

    return room


@with_transaction
def edit_room(room, number, inhabitable, vo_suchname: str, address: Address, processor: User):
    if room.number != number:
        if Room.q.filter_by(number=number, level=room.level, building=room.building).filter(Room.id!=room.id).first() is not None:
            raise RoomAlreadyExistsException()

        log_room_event("Renamed room from {} to {}.".format(room.number, number), processor, room)

        room.number = number

    if room.inhabitable != inhabitable:
        log_room_event("Changed inhabitable status to {}.".format(str(inhabitable)), processor, room)

        room.inhabitable = inhabitable

    if room.swdd_vo_suchname != vo_suchname:
        log_room_event("Changed VO id from {} to {}.".format(room.swdd_vo_suchname,
                                                             vo_suchname), processor, room)

        room.swdd_vo_suchname = vo_suchname

    if room.address != address:
        room.address = address
        log_room_event(deferred_gettext("Changed address to {}").format(f'blah').to_json(),
                       processor, room)
        for user in room.users_sharing_address:
            user.address = room.address

    return room


def get_room(building_id, level, room_number):
    return Room.q.filter_by(number=room_number,
                            level=level, building_id=building_id).one_or_none()


@dataclass
class RoomAddressSuggestion:
    street: str
    number: str
    zip_code: str
    city: str
    state: str
    country: str

    def __str__(self):
        return f"{self.street} {self.number}, {self.zip_code} {self.city}," \
               + (f" {self.state}, " if self.state else "") \
               + f"{self.country}"


def suggest_room_address_data(building: Building) -> Optional[RoomAddressSuggestion]:
    """Return the most common address features of preexisting rooms in a certain building. """

    cols = (Address.street, Address.number, Address.zip_code,
            Address.city, Address.state, Address.country)
    query = (
        session.session.query()
        .select_from(Room)
        .join(Address)
        .add_columns(*cols)
        .add_columns(func.count().label('count'))
        .filter(Room.building == building)
        .group_by(*cols)
        .order_by(literal_column('count').desc())
    )

    rows = query.all()
    if not rows:
        return

    def row_to_suggestion(row):
        return RoomAddressSuggestion(*list(row[:-1]))

    row, *rest = rows
    suggestion = row_to_suggestion(row)
    if rest:
        logger.warning("Address suggestion for building '%s' not unique (%d total):\n"
                       "first suggestion:\n  %s (%d times),\n"
                       "runner-up suggestion:\n  %s (%d times)",
                       building.short_name, len(rows),
                       suggestion, row.count,
                       row_to_suggestion(rest[0]), rest[0].count)

    return suggestion
