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


class Test_010_UserLogEntry(LogTestBase):
    def test_0010_create_user_log_entry(self):
        user_log_entry = log_user_event(message=self.message,
                                        author=self.user,
                                        user=self.user)

        self.assertEqual(user_log_entry.message, self.message)
        self.assertAlmostEqual(user_log_entry.created_at, session.utcnow(),
                               delta=timedelta(seconds=5))
        self.assertEqual(user_log_entry.author, self.user)
        self.assertEqual(user_log_entry.user, self.user)

        self.assertIsNotNone(LogEntry.q.get(user_log_entry.id))
        session.session.delete(user_log_entry)
        session.session.commit()
        self.assertIsNone(LogEntry.q.get(user_log_entry.id))


class Test_020_RoomLogEntry(LogTestBase):
    def create_factories(self):
        super().create_factories()

        self.room = RoomFactory.create()

    def test_0010_create_room_log_entry(self):
        room_log_entry = log_room_event(message=self.message,
                                        author=self.user,
                                        room=self.room)

        self.assertIsNotNone(RoomLogEntry.q.get(room_log_entry.id))

        db_room_log_entry = RoomLogEntry.q.get(room_log_entry.id)

        self.assertEqual(db_room_log_entry.message, self.message)
        self.assertAlmostEqual(db_room_log_entry.created_at, session.utcnow(),
                               delta=timedelta(seconds=5))
        self.assertEqual(db_room_log_entry.author, self.user)
        self.assertEqual(db_room_log_entry.room, self.room)

        self.assertIsNotNone(LogEntry.q.get(db_room_log_entry.id))
        session.session.delete(db_room_log_entry)
        session.session.commit()
        self.assertIsNone(LogEntry.q.get(db_room_log_entry.id))
