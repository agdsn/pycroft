#!/usr/bin/env python3
import csv
import datetime
import logging
import re
import sys

from ipaddr import IPAddress
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, scoped_session

from pycroft.model.address import Address
from pycroft.model.session import session

from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import closed, UnboundedInterval
from pycroft.model import create_engine
from pycroft.model.facilities import Room
from pycroft.model.finance import Account
from pycroft.model.host import Host, Interface, IP
from pycroft.model.logging import UserLogEntry
from pycroft.model.net import Subnet
from pycroft.model.user import User, UnixAccount, PropertyGroup, Membership
from scripts.connection import try_create_connection, get_connection_string
from flask import _request_ctx_stack
import pycroft.model.session


default_handler = logging.StreamHandler(sys.stdout)
default_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
)
fh = logging.FileHandler('spb-{:%Y-%m-%d_%H-%M-%S}.log'.format(datetime.datetime.now()))
formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(lineno)04d | %(message)s')
fh.setFormatter(formatter)

building_id = 66

subnet_ids = {
    'A': 68,
    'B': 69,
    'C': 70,
}

vlan_ids = {
    'A': 67,
    'B': 68,
    'C': 69
}

ignore_debits = [4051171, 4051942,  4055284,  4056841, 4056874]

mac_ignore = [
    'd8:0d:17:4a:f1:33',
    'ac:84:c6:f1:b4:a3',
    '98:da:c4:7b:1e:73',
    '9c:5a:44:6e:44:34',
]

def make_member_of(session, user, group, processor, during=UnboundedInterval):
    session.add(Membership(begins_at=during.begin, ends_at=during.end, user=user, group=group))
    message = deferred_gettext(f"Added to group {group.name} during {during}.").to_json()

    session.add(UserLogEntry(user=user, author=processor,
                             message=message))

def get_csv_content(file, delimiter=','):
    data = []

    with open(file, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter, quotechar='"')
        con_data_ws = list(reader)

        for co in con_data_ws:
            new_co = {}
            for key, value in co.items():
                new_co[key] = value.strip()

            data.append(new_co)

    return data

def run():
    logger = logging.getLogger('pycroft')
    logger.addHandler(default_handler)
    logger.addHandler(fh)
    logging.basicConfig(level=logging.INFO)

    connection_string = get_connection_string()

    # connection, engine = try_create_connection(connection_string, False, None,
    #                                            reflections=False)

    # session = sessionmaker(bind=engine)()

    engine = create_engine(connection_string, echo=False)
    pycroft.model.session.set_scoped_session(
        scoped_session(sessionmaker(bind=engine),
                       scopefunc=lambda: _request_ctx_stack.top))

    processor = User.q.get(0)
    now = datetime.datetime.now(datetime.timezone.utc)

    users = get_csv_content('fl12/users.csv')
    rooms = get_csv_content('fl12/rooms.csv')
    contracts = get_csv_content('fl12/contracts.csv')
    macs = get_csv_content('fl12/latest_mac_per_room.csv')
    ips = get_csv_content('fl12/room_ips.csv')

    new_rooms = {}

    session.begin(subtransactions=True)

    for room in rooms:
        level = int(room['level']) + 1
        number = room['number']

        ex_room = Room.q.filter_by(number=number, level=level, building_id=building_id).first()

        if ex_room is not None:
            new_room = ex_room

            logger.warning(f"Room {number} already exists.")
        else:
            new_address = Address(
                street="Fritz-Löffler-Straße",
                number="12",
                zip_code="01069",
                city="Dresden",
                country="Germany",
                addition=number,
            )
            new_room = Room(number=number, level=level, swdd_vo_suchname=room['swdd_vo_suchname'],
                            inhabitable=True, building_id=building_id, address=new_address)

            logger.info(f"Created room {number}.")

            session.add(new_room)

        new_rooms[room['number']] = new_room

    # uid_start = 21020

    extra_count = 2

    for co in contracts:
        logger.info(co)

        if int(co['debitor']) in ignore_debits:
            logger.error(f"Ignored user {co['debitor']}")

            continue

        ud = next(u for u in users if u['debitor'] == co['debitor'])

        logger.info(ud)

        room = new_rooms[co['room']]

        existing_user = User.q.filter(User.swdd_person_id == int(ud['debitor'])).one_or_none()

        ext_group = PropertyGroup.q.get(8)

        if existing_user is None:
            first = ud['firstname'].lower()
            last = ud['surname'].lower()

            first = re.sub(r'[^a-z]+', '', first)
            last = re.sub(r'[^a-z]+', '', last)

            login = f"{first[0]}.{last}"

            if User.q.filter_by(login=login).first() is not None:
                login = f'{login}{extra_count}'

                extra_count += 1

            logger.info(f"New Login: {login}")

            unix_acc = UnixAccount(home_directory="/home/{}".format(login))

            user = User(login=login,
                        name='{} {}'.format(ud['firstname'], ud['surname']),
                        email=None,
                        email_confirmed=False,
                        registered_at=now,
                        address=room.address,
                        room=room,
                        account=Account(name="", type="USER_ASSET"),
                        unix_account=unix_acc,
                        )

            session.add(user)

            session.flush()

            user.account.name = deferred_gettext(u"User {id}").format(
                id=user.id).to_json()

            make_member_of(session, user, ext_group, processor, closed(now, None))

            logger.info(f"Created user {user.id}: {login}")

            #  uid_start += 1

            session.add(UserLogEntry(user=user, author=processor,
                                     message=deferred_gettext(u"User imported from FL12 data.").to_json()))
        else:
            user = existing_user
            logger.warning(f"Found existing user {user.id} for debitorennummer {ud['debitor']}.")

            if user.room == room:
                logger.warning("User already living in correct room.")
            else:
                logger.error(f"MANUAL INTERVENTION!! User {user.id} may lives in FL12 {room.number}!")
                continue

                logger.warning("Moving user.")
                user.room = room
                user.address = room.address

                session.add(UserLogEntry(user=user, author=processor,
                                         message=deferred_gettext(
                                   u"Automatic movement to FL12 due to import.").to_json()))

                if user.has_property('member'):
                    raise Exception("User is member.")
                else:
                    if not user.member_of(ext_group):
                        logger.warning("Give extern group.")
                        make_member_of(session, user, ext_group, processor, closed(now, None))
                    else:
                        logger.warning("Already has extern group.")

        create_host = True
        for host in user.hosts:
            if host.room != room:
                logger.warning(f"User {user.id} already has an other host, removing.")
                session.delete(host)
            else:
                logger.warning(f"User {user.id} already has host in room, skipping.")
                create_host = False

        try:
            mac = next(m for m in macs if m['room'] == co['room'])

            if mac['mac'] in mac_ignore:
                logger.error(f"MAC address ignored for user {login}.")

                session.add(UserLogEntry(user=user, author=processor,
                                         message=deferred_gettext(
                                             u"No host imported, because MAC address already used by an other user.").to_json()))

                create_host = False
        except StopIteration:
            logger.warning(f"Cannot find mac address for user {login}.")

            session.add(UserLogEntry(user=user, author=processor,
                                     message=deferred_gettext(
                                         u"No MAC address found in imported data.").to_json()))

            create_host = False

        if create_host:
            logger.info(mac)

            subhouse = room.number[0]

            subnet = session.query(Subnet).filter_by(id=subnet_ids[subhouse]).one()

            host = Host(
                owner=user,
                room=room,
            )

            interface = Interface(
                mac=mac['mac'],
                host=host,
            )

            ip_add = next(i for i in ips if i['room'] == room.number)

            ip = IP(
                interface=interface,
                address=IPAddress(ip_add['ip']),
                subnet=subnet,
            )

            logger.info(f"Created Host with interface for user {user.id}.")

            session.add(host)
            session.add(interface)
            session.add(ip)

        session.flush()

        # session.commit()


if __name__ == "__main__":
    run()
