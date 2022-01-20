# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from pycroft.lib.logging import log_user_event, log_room_event
from pycroft.model import session
from pycroft.model.logging import RoomLogEntry, LogEntry
from tests.legacy_base import FactoryDataTestBase
from tests.factories import UserFactory, RoomFactory


class LogTestBase(FactoryDataTestBase):
    message = "test_message"

    def create_factories(self):
        super().create_factories()
        self.user = UserFactory.create()

    def assert_log_entry(self, log_entry, expected_author, expected_created_at, expected_message):
        assert log_entry.message == expected_message
        assert abs(log_entry.created_at - expected_created_at) < timedelta(seconds=5)
        assert log_entry.author == expected_author
        assert LogEntry.get(log_entry.id) is not None


class UserLogEntryTest(LogTestBase):
    def test_user_log_entry(self):
        user_log_entry = log_user_event(message=self.message,
                                        author=self.user,
                                        user=self.user)

        self.assert_log_entry(user_log_entry, self.user, session.utcnow(), self.message)
        assert user_log_entry.user == self.user

        session.session.delete(user_log_entry)
        session.session.commit()
        assert LogEntry.get(user_log_entry.id) is None


class RoomLogEntryTest(LogTestBase):
    def create_factories(self):
        super().create_factories()
        self.room = RoomFactory.create()

    def test_create_room_log_entry(self):
        room_log_entry = log_room_event(message=self.message,
                                        author=self.user,
                                        room=self.room)

        assert RoomLogEntry.get(room_log_entry.id) is not None

        db_room_log_entry = RoomLogEntry.get(room_log_entry.id)

        self.assert_log_entry(db_room_log_entry, self.user, session.utcnow(), self.message)
        assert db_room_log_entry.room == self.room

        assert LogEntry.get(db_room_log_entry.id) is not None
        session.session.delete(db_room_log_entry)
        session.session.commit()
        assert LogEntry.get(db_room_log_entry.id) is None
