# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from pycroft.lib.logging import log_user_event, log_room_event
from pycroft.model.facilities import Room
from pycroft.model.logging import RoomLogEntry, LogEntry
from pycroft.model.user import User
from tests.factories import UserFactory, RoomFactory


def assert_log_entry(log_entry, expected_author, expected_created_at, expected_message):
    assert log_entry.message == expected_message
    assert abs(log_entry.created_at - expected_created_at) < timedelta(seconds=5)
    assert log_entry.author == expected_author
    assert LogEntry.get(log_entry.id) is not None


@pytest.fixture(scope="session")
def message() -> str:
    return "test_message"


@pytest.fixture(scope="module")
def user(module_session: Session) -> User:
    return UserFactory.create()


@pytest.fixture(scope="module")
def room(module_session: Session) -> Room:
    return RoomFactory.create()


def test_user_log_entry(session, utcnow, message, user):
    user_log_entry = log_user_event(message=message, author=user, user=user)

    assert_log_entry(user_log_entry, user, utcnow, message)
    assert user_log_entry.user == user

    session.delete(user_log_entry)
    session.flush()
    assert LogEntry.get(user_log_entry.id) is None


def test_create_room_log_entry(session, utcnow, message, user, room):
    room_log_entry = log_room_event(message=message, author=user, room=room)

    assert RoomLogEntry.get(room_log_entry.id) is not None

    db_room_log_entry = RoomLogEntry.get(room_log_entry.id)

    assert_log_entry(db_room_log_entry, user, utcnow, message)
    assert db_room_log_entry.room == room

    assert LogEntry.get(db_room_log_entry.id) is not None
    session.delete(db_room_log_entry)
    session.flush()
    assert LogEntry.get(db_room_log_entry.id) is None
