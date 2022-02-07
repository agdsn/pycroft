#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import pytest
from sqlalchemy.future import select

from pycroft.model.address import Address
from tests.factories import AddressFactory, RoomFactory, UserFactory
from tests.factories.base import copy_factory
from tests.model.conftest import assert_unique_violation


def all_addrs(session) -> list[Address]:
    return session.scalars(select(Address)).all()


@pytest.mark.parametrize('address_kw', [
    {},
    {'state': None},
    {'addition': None},
    {'addition': None, 'state': None},
])
def test_duplicate_address_cannot_be_added(session, address_kw):
    with session.begin_nested():
        address = AddressFactory.create(**address_kw)

    new_addr = copy_factory(AddressFactory, address)
    with assert_unique_violation():
        with session.begin_nested():
            session.add(new_addr)


@pytest.fixture
def address(session):
    return AddressFactory()


@pytest.fixture
def room(address):
    return RoomFactory(address=address)


def test_room_update_cleanup(session, room):
    with session.begin_nested():
        room.address = AddressFactory()
        session.add(room)
    assert all_addrs(session) == [room.address]


def test_room_delete_cleanup(session, room):
    with session.begin_nested():
        session.delete(room)
    assert all_addrs(session) == []


@pytest.fixture
def user_no_room(address):
    return UserFactory(address=address, room=None)


def test_user_update_cleanup(session, user_no_room):
    user = user_no_room
    with session.begin_nested():
        user.address = AddressFactory()  # other address
        session.add(user)
    assert all_addrs(session) == [user.address]


def test_user_delete_cleanup(session, user_no_room):
    user = user_no_room
    with session.begin_nested():
        session.delete(user)
    assert all_addrs(session) == []


@pytest.fixture
def user_with_room(session, address):
    return UserFactory(address=address)


def test_address_stays_after_room_delete(session, user_with_room):
    user = user_with_room
    with session.begin_nested():
        session.delete(user.room)
    assert all_addrs(session) == [user.address]


def test_address_stays_after_user_delete(session, user_with_room):
    room_addr = user_with_room.room.address
    user = user_with_room
    with session.begin_nested():
        session.delete(user)
    assert all_addrs(session) == [room_addr]
