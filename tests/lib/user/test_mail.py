#  Copyright (c) 2025. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import pytest

from pycroft.lib.user import get_active_users_with_building
from pycroft.model.facilities import Room, Building
from itertools import combinations

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
    out = []
    for _ in range(20):
        b = BuildingFactory.create()
        out.append(b)
    return out


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
