#  Copyright (c) 2025. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import typing as t
from datetime import datetime, date
from itertools import combinations

import pytest
from sqlalchemy.orm import Session

from pycroft import config
from pycroft.helpers.interval import closedopen
from pycroft.lib.user import get_active_users_with_building
from pycroft.model.facilities import Room, Building
from pycroft.model.user import User
from ...factories import UserFactory, RoomFactory, BuildingFactory, AddressFactory


@pytest.fixture(scope="module")
def user(module_session, config) -> User:
    return UserFactory(
        room=RoomFactory(building=BuildingFactory.create()),
        address=AddressFactory(),
        membership__group=config.violation_group,
        with_membership=True,
    )


@pytest.fixture(scope="module")
def user_no_room(module_session, config) -> User:
    return UserFactory.create(
        room=None,
        address=AddressFactory(),
        membership__group=config.member_group,
        with_membership=True,
    )


@pytest.fixture(scope="module")
def building_list(module_session) -> list[Building]:
    return BuildingFactory.create_batch(20)


@pytest.fixture(scope="module")
def build_map(module_session, config, building_list) -> dict:
    out = {}
    for building in building_list:
        out[building] = []
        for _ in range(5):
            user = UserFactory.create(
                room=RoomFactory(building=building),
                membership__group=config.member_group,
                with_membership=True,
            )
            out[building].append(user)
    return out


@pytest.fixture(scope="module")
def room(module_session) -> Room:
    return RoomFactory()


class TestMailSelectWtihoutBulding:

    def test_mail_just_goup(self, session, config, build_map, user_no_room):
        session.flush()
        length = sum(len(v) for v in build_map.values()) + 1
        users = get_active_users_with_building(session, [config.member_group], [])

        assert len(users.all()) == length

    def test_building(self, session, config, build_map):
        session.flush()
        for building, userlist in build_map.items():
            users = get_active_users_with_building(session, [config.member_group], [building])
            assert len(users.all()) == len(userlist)

    def test_multi_building(self, session, config, build_map):
        session.flush()
        for comb in combinations(build_map.keys(), 2):
            users = get_active_users_with_building(session, [config.member_group], comb)
            length = sum(len(build_map[building]) for building in comb)
            assert len(users.all()) == length

    def test_not_found_in_building(self, session, config, build_map, user, building_list):
        users = get_active_users_with_building(session, [config.violation_group], [])
        assert len(users.all()) == 1
        users = get_active_users_with_building(session, [config.violation_group], building_list)
        assert len(users.all()) == 0


class UserWithTenancyGen(t.Protocol):
    def __call__(
        self,
        session: Session,
        tenancy_begin: date,
        tenancy_end: date,
        mem_end: datetime | None = None,
    ) -> User: ...

@pytest.fixture(scope="function")
def gen_user(config) -> UserWithTenancyGen:
    def gen(
        session: Session, tenancy_begin: date, tenancy_end: date, mem_end: datetime | None = None
    ) -> User:
        u = t.cast(
            User,
            UserFactory.create(
                with_membership=True,
                registered_at=tenancy_begin,
                membership__active_during=closedopen(tenancy_begin, mem_end),
                membership__group=config.member_group,
            ),
        )
        u.swdd_person_id = u.id + 10000
        session.add(u)
        session.flush()
        from sqlalchemy import Table, MetaData, Column, Integer, Text, Date
        from sqlalchemy.sql import insert, text

        swdd_vv = Table(
            "swdd_vv",
            MetaData(),
            Column("persvv_id", Integer, nullable=False),
            Column("person_id", Integer, nullable=False),
            Column("vo_suchname", Text, nullable=False),
            Column("person_hash", Text, nullable=False),
            Column("mietbeginn", Date, nullable=False),
            Column("mietende", Date, nullable=False),
            Column("status_id", Integer, nullable=False),
            schema="swdd",
        )
        assert u.room
        session.execute(
            swdd_vv.insert().values(
                persvv_id=u.id + 10000,
                person_id=u.id + 10000,
                vo_suchname=u.room.swdd_vo_suchname,
                person_hash="",
                mietbeginn=tenancy_begin.isoformat(),
                mietende=tenancy_end.isoformat(),
                status_id=1,
            )
        )
        session.execute(text("refresh materialized view swdd_vv"))
        return u

    return gen

def test_move_out_reminder(session, config, gen_user: UserWithTenancyGen):
    u = gen_user(
        session,
        date(2019, 10, 1),
        date(2020, 9, 30),
        None,
    )
    session.flush()

    # TODO fixture: member with contract end at 2020-01-08
    # TODO fixture: member with the former, but also
    from pycroft.lib.user.mail import get_members_with_contract_end_at
    m = get_members_with_contract_end_at(session, date(2020, 9, 30))
    assert m.all() == [u]
