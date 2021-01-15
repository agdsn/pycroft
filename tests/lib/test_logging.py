# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from pycroft.lib.logging import log_user_event, log_room_event
from pycroft.model import session
from pycroft.model.logging import RoomLogEntry, LogEntry
from tests import FactoryDataTestBase
from tests.factories import UserFactory, RoomFactory


class LogTestBase(FactoryDataTestBase):
    message = "test_message"

    def create_factories(self):
        super().create_factories()
        self.user = UserFactory.create()

    def assert_log_entry(self, log_entry, expected_author, expected_created_at, expected_message):
        self.assertEqual(log_entry.message, expected_message)
        self.assertAlmostEqual(log_entry.created_at, expected_created_at,
                               delta=timedelta(seconds=5))
        self.assertEqual(log_entry.author, expected_author)
        self.assertIsNotNone(LogEntry.q.get(log_entry.id))


class UserLogEntryTest(LogTestBase):
    def test_user_log_entry(self):
        user_log_entry = log_user_event(message=self.message,
                                        author=self.user,
                                        user=self.user)

        self.assert_log_entry(user_log_entry, self.user, session.utcnow(), self.message)
        self.assertEqual(user_log_entry.user, self.user)

        session.session.delete(user_log_entry)
        session.session.commit()
        self.assertIsNone(LogEntry.q.get(user_log_entry.id))


class RoomLogEntryTest(LogTestBase):
    def create_factories(self):
        super().create_factories()
        self.room = RoomFactory.create()

    def test_create_room_log_entry(self):
        room_log_entry = log_room_event(message=self.message,
                                        author=self.user,
                                        room=self.room)

        self.assertIsNotNone(RoomLogEntry.q.get(room_log_entry.id))

        db_room_log_entry = RoomLogEntry.q.get(room_log_entry.id)

        self.assert_log_entry(db_room_log_entry, self.user, session.utcnow(), self.message)
        self.assertEqual(db_room_log_entry.room, self.room)

        self.assertIsNotNone(LogEntry.q.get(db_room_log_entry.id))
        session.session.delete(db_room_log_entry)
        session.session.commit()
        self.assertIsNone(LogEntry.q.get(db_room_log_entry.id))
