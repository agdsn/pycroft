#!/usr/bin/env python3
import csv
import datetime
import logging
import sys

from ipaddr import IPAddress
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, scoped_session
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

nr_to_id = {
    '21': {'id': 67, 'subnet_id': 65},
    '25': {'id': 68, 'subnet_id': 66},
    '29': {'id': 69, 'subnet_id': 67},
}


def make_member_of(session, user, group, processor, during=UnboundedInterval):
    session.add(Membership(begins_at=during.begin, ends_at=during.end, user=user, group=group))
    message = deferred_gettext(f"Added to group {group.name} during {during}.").to_json()

    session.add(UserLogEntry(user=user, author=processor,
                             message=message))

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

    user_data = []

    session.begin(subtransactions=True)

    with open('peter.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';', quotechar="'")
        user_data_ws = list(reader)

        for ud in user_data_ws:
            new_ud = {}
            for key, value in ud.items():
                new_ud[key] = value.strip()

            user_data.append(new_ud)

    # uid_start = 21020

    for ud in user_data:
        logger.info(ud)

        if len(ud['mac']) == 0:
            logger.info("No mac, skip.")
            continue

        rn = ud['Zimmer']
        building = nr_to_id[ud['Haus']]['id']

        if rn[0] == 'A' or rn[0] == 'K':
            level = 0
            number = rn
        elif len(rn) == 3:
            level = int(rn[0])
            number = str(int(rn[1:]))
        elif len(rn) == 4:
            level = int(rn[:2])
            number = str(int(rn[2:]))
        else:
            raise

        logger.info(f"Searching room {rn}: {building}, {level}, {number}")

        room = Room.q.filter_by(building_id=building, level=level, number=number).one()

        if room is None:
            raise

        existing_user = User.q.filter(func.lower(User.email) == ud['email'].lower()).one_or_none()

        ext_group = PropertyGroup.q.get(8)

        if existing_user is None:
            login = ud['email'].split('@')[0].lower().replace('_', '-')

            if not login[0].isalpha():
                login = f'spb-{login}'

            if User.q.filter_by(login=login).first() is not None:
                login = f'spb-{login}'

            unix_acc = UnixAccount(home_directory="/home/{}".format(login))

            user = User(login=login,
                        name='{} {}'.format(ud['Vorname'], ud['Nachname']),
                        email=ud['email'].lower(),
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
                                     message=deferred_gettext(u"User imported from St. Petersburger data.").to_json()))
        else:
            user = existing_user
            logger.warning(f"Found existing user {user.id} for email {user.email}.")

            if user.room == room:
                logger.warning("User already living in correct room.")
            else:
                logger.warning("Moving user.")
                user.room = room
                user.address = room.address

                session.add(UserLogEntry(user=user, author=processor,
                                         message=deferred_gettext(
                                   u"Automatic movement to St.-Petersburger-Straße.").to_json()))

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

        if create_host:
            subnet = session.query(Subnet).filter_by(id=nr_to_id[ud['Haus']]['subnet_id']).one()

            host = Host(
                owner=user,
                room=room,
            )

            interface = Interface(
                mac=ud['mac'],
                host=host,
            )

            ip = IP(
                interface=interface,
                address=IPAddress(ud['ip']),
                subnet=subnet,
            )

            logger.info(f"Created Host with interface for user {user.id}.")

            session.add(host)
            session.add(interface)
            session.add(ip)

        session.commit()


if __name__ == "__main__":
    run()
