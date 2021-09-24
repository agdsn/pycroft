import re
from typing import Optional

from sqlalchemy import or_, func, cast, Text
from sqlalchemy.orm import Query

from pycroft.helpers.net import mac_regex, ip_regex
from pycroft.model.facilities import Room
from pycroft.model.host import Host, Interface, IP
from pycroft.model.user import User, Membership, PropertyGroup


def user_search_query(
    user_id: Optional[int],
    name: Optional[str],
    login: Optional[str],
    mac: Optional[str],
    ip_address: Optional[str],
    property_group_id: Optional[int],
    building_id: Optional[int],
    email: Optional[str],
    person_id: Optional[int],
    query: Optional[str],
) -> Query:
    result = User.q
    if user_id is not None:
        result = result.filter(User.id == int(user_id))
    if email:
        result = result.filter(User.email.ilike(f"%{email}%"))
    if person_id is not None:
        result = result.filter(User.swdd_person_id == person_id)
    if name:
        result = result.filter(User.name.ilike(f"%{name}%"))
    if login:
        result = result.filter(User.login.ilike(f"%{login}%"))
    if mac:
        result = result.join(User.hosts) \
            .join(Host.interfaces) \
            .filter(Interface.mac == mac)
    if ip_address:
        result = result.join(User.hosts) \
            .join(Host.ips) \
            .filter(IP.address == ip_address)

    if property_group_id is not None:
        result = result\
            .join(Membership)\
            .filter(Membership.active_during.contains(func.current_timestamp))\
            .join(PropertyGroup, PropertyGroup.id == Membership.group_id)\
            .filter(PropertyGroup.id == property_group_id)

    if building_id is not None:
        result = result.join(User.room) \
            .filter(Room.building_id == building_id)

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
                func.lower(User.name).like(func.lower(f"%{query}%")),
                func.lower(User.login).like(func.lower(f"%{query}%")),
                cast(User.id, Text).like(f"{query}%"),
                cast(User.swdd_person_id, Text) == query,
                cast(User.email, Text) == query,
            ))
    return result
