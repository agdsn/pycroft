# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from pycroft.lib.logging import log_user_event, log_room_event
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.logging import RoomLogEntry
from pycroft.model.user import User
from tests import FixtureDataTestBase
from tests.fixtures.dummy.dormitory import RoomData
from tests.fixtures.dummy.logging import UserLogEntryData, RoomLogEntryData
from tests.fixtures.dummy.user import UserData


class LogTestBase(FixtureDataTestBase):
    message = "test_message"

    def setUp(self):
        super(LogTestBase, self).setUp()
        self.user = User.q.filter_by(login=UserData.dummy.login).one()


class Test_010_UserLogEntry(LogTestBase):
    datasets = [UserData, UserLogEntryData]

    def test_0010_create_user_log_entry(self):
        user_log_entry = log_user_event(message=self.message,
                                        author=self.user,
                                        user=self.user)

        self.assertEqual(user_log_entry.message, self.message)
        self.assertAlmostEqual(user_log_entry.created_at, session.utcnow(),
                               delta=timedelta(seconds=5))
        self.assertEqual(user_log_entry.author, self.user)
        self.assertEqual(user_log_entry.user, self.user)

        session.session.delete(user_log_entry)
        session.session.commit()


class Test_020_RoomLogEntry(LogTestBase):
    datasets = [RoomData, RoomLogEntryData]

    def test_0010_create_room_log_entry(self):
        room = Room.q.filter_by(number=RoomData.dummy_room1.number,
                                level=RoomData.dummy_room1.level).one()

        room_log_entry = log_room_event(message=self.message,
                                        author=self.user,
                                        room=room)

        self.assertIsNotNone(RoomLogEntry.q.get(room_log_entry.id))

        db_room_log_entry = RoomLogEntry.q.get(room_log_entry.id)

        self.assertEqual(db_room_log_entry.message, self.message)
        self.assertAlmostEqual(db_room_log_entry.created_at, session.utcnow(),
                               delta=timedelta(seconds=5))
        self.assertEqual(db_room_log_entry.author, self.user)
        self.assertEqual(db_room_log_entry.room, room)

        session.session.delete(db_room_log_entry)
        session.session.commit()
