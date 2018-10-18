from collections import defaultdict

from sqlalchemy import func, and_
from sqlalchemy.orm import aliased, contains_eager, joinedload

from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.host import Host
from pycroft.model.user import User


def get_overcrowded_rooms():
    # rooms containing multiple users each of which has a host in the room
    oc_rooms_query = (
        Room.q.join(User)
            .join(Host).filter(User.room_id == Host.room_id)
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
