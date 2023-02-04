"""
pycroft.lib.facilities
~~~~~~~~~~~~~~~~~~~~~~
"""
import logging
import re
import typing as t
from dataclasses import dataclass
from itertools import groupby

from sqlalchemy import func, and_, distinct, literal_column, select
from sqlalchemy.orm import aliased, contains_eager, joinedload

from pycroft.helpers.i18n import deferred_gettext
from pycroft.lib.exc import PycroftLibException
from pycroft.lib.logging import log_room_event
from pycroft.model import session
from pycroft.model.address import Address
from pycroft.model.facilities import Room, Building
from pycroft.model.host import Host
from pycroft.model.session import with_transaction
from pycroft.model.user import User

logger = logging.getLogger(__name__)


class RoomAlreadyExistsException(PycroftLibException):
    pass


def get_overcrowded_rooms(building_id: int = None) -> dict[int, list[User]]:
    """
    :param building_id: Limit to rooms of the building.
        Returns a dict of overcrowded rooms with their inhabitants.
    :return: a dict mapping room ids to inhabitants
    """

    oc_rooms_filter = []
    if building_id is not None:
        oc_rooms_filter.append(Room.building_id == building_id)

    # rooms containing multiple users each of which has a host in the room
    oc_rooms_query = (
        select(Room)
        .join(User)
        .join(Host)
        .filter(User.room_id == Host.room_id)
        .filter(*oc_rooms_filter)
        .group_by(Room.id)
        .having(func.count(distinct(User.id)) > 1)
        .subquery()
    )

    user = aliased(User)

    # room can be extracted from the subquery
    oc_room = contains_eager(user.room, alias=oc_rooms_query)

    stmt = (
        select(user)
        # only include users living in overcrowded rooms
        .join(oc_rooms_query)
        # only include users that have a host in their room
        .join(Host, and_(user.id == Host.owner_id, user.room_id == Host.room_id))
        .options(oc_room)
        .options(oc_room.joinedload(Room.building))
        .options(joinedload(user.current_properties))
    )

    users = session.session.scalars(stmt).unique().all()
    return {k: list(v) for k, v in groupby(users, lambda u: u.room.id)}


@with_transaction
def create_room(
    building: Building,
    level: int,
    number: str,
    processor: User,
    address: Address,
    inhabitable: bool = True,
    vo_suchname: str | None = None,
) -> Room:
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
def edit_room(
    room: Room,
    number: str,
    inhabitable: bool,
    vo_suchname: str,
    address: Address,
    processor: User,
) -> Room:
    if room.number != number:
        if Room.q.filter_by(number=number, level=room.level, building=room.building).filter(Room.id!=room.id).first() is not None:
            raise RoomAlreadyExistsException()

        message = (
            deferred_gettext("Renamed room from {} to {}.")
            .format(room.number, number)
        )
        log_room_event(message.to_json(), processor, room)
        room.number = number

    if room.inhabitable != inhabitable:
        message = (
            deferred_gettext("Changed inhabitable status to {}.")
            .format(inhabitable)
        )
        log_room_event(message.to_json(), processor, room)
        room.inhabitable = inhabitable

    if room.swdd_vo_suchname != vo_suchname:
        log_room_event(
            deferred_gettext("Changed VO id from {} to {}.")
                .format(room.swdd_vo_suchname, vo_suchname).to_json(),
            processor, room
        )
        room.swdd_vo_suchname = vo_suchname

    if room.address != address:
        room.address = address
        log_room_event(deferred_gettext("Changed address to {}").format(str(address)).to_json(),
                       processor, room)
        for user in room.users_sharing_address:
            user.address = room.address

    return room


def get_room(building_id: int, level: int, room_number: str) -> Room | None:
    return t.cast(
        Room | None,
        Room.q.filter_by(
            number=room_number, level=level, building_id=building_id
        ).one_or_none(),
    )


@dataclass
class RoomAddressSuggestion:
    street: str
    number: str
    zip_code: str
    city: str
    state: str
    country: str

    def __str__(self) -> str:
        return f"{self.street} {self.number}, {self.zip_code} {self.city}," \
               + (f" {self.state}, " if self.state else "") \
               + f"{self.country}"


def suggest_room_address_data(building: Building) -> RoomAddressSuggestion | None:
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
        return None

    def row_to_suggestion(row: t.Any) -> RoomAddressSuggestion:
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


def sort_buildings(buildings: t.Iterable[Building]) -> list[Building]:
    def make_sort_key(building: Building) -> tuple[str, str | tuple[int, str]]:
        s = re.split(r"(\d+)([a-zA-Z]?)", building.number)
        if len(s) != 4:
            return building.street, building.number  # split unsuccessful
        return building.street, (int(s[1]), s[2].lower())

    return sorted(buildings, key=make_sort_key)


def determine_building(shortname: str | None = None, id: int | None = None) -> Building:
    """Determine building from shortname or id in this order.

    :param shortname: The short name of the building
    :param id: The id of the building

    :return: The unique building
    """
    if shortname:
        return t.cast(
            Building, Building.q.filter(Building.short_name == shortname).one()
        )
    if id:
        return session.session.get(Building, id)
    raise ValueError("Either shortname or id must be given to identify the building!")
