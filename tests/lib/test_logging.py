# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime
from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import Integer

from tests import FixtureDataTestBase
from tests.lib.fixtures.logging_fixtures import UserData, UserLogEntryData,\
    RoomData, RoomLogEntryData

from pycroft.model.logging import UserLogEntry, LogEntry, RoomLogEntry
from pycroft.model.user import User
from pycroft.model.dormitory import Room
from pycroft.model import session

from pycroft.lib.logging import create_user_log_entry, delete_log_entry,\
    _create_log_entry, create_room_log_entry

class Test_010_UserLogEntry(FixtureDataTestBase):
    datasets = [UserData, UserLogEntryData]

    def test_0010_create_user_log_entry(self):
        message = "test_message"
        timestamp = datetime.now()
        author = User.q.first()
        user = User.q.first()

        user_log_entry = create_user_log_entry(message=message,
            timestamp=timestamp, author=author, user=user)

        self.assertIsNotNone(UserLogEntry.q.get(user_log_entry.id))

        db_user_log_entry = UserLogEntry.q.get(user_log_entry.id)

        self.assertEqual(db_user_log_entry.message, message)
        self.assertEqual(db_user_log_entry.timestamp, timestamp)
        self.assertEqual(db_user_log_entry.author, author)
        self.assertEqual(db_user_log_entry.user, user)

        session.session.delete(db_user_log_entry)
        session.session.commit()

    def test_0020_delete_user_log_entry(self):
        del_user_log_entry = delete_log_entry(
            UserLogEntryData.dummy_log_entry1.id)

        self.assertIsNone(UserLogEntry.q.get(del_user_log_entry.id))

    def test_0025_delete_wrong_user_log_entry(self):
        self.assertRaises(ValueError, delete_log_entry,
            UserLogEntryData.dummy_log_entry1.id + 100)


class Test_020_MalformedTypes(FixtureDataTestBase):
    datasets = [UserData]

    class MalformedLogEntry(LogEntry):
        id = Column(Integer, ForeignKey("logentry.id"), primary_key=True)
        __mapper_args__ = {'polymorphic_identity': 'malformedlogentry'}

    def test_0010_create_malformed_log_entry(self):
        self.assertRaises(ValueError, _create_log_entry, 'malformedlogentry',
            id=100)

    def test_0020_delete_malformed_log_entry(self):
        message = "malformed_type"
        timestamp = datetime.now()
        author = User.q.first()

        malformed_log_entry = Test_020_MalformedTypes.MalformedLogEntry(
            message=message, timestamp=timestamp, author=author, id=10000)

        session.session.add(malformed_log_entry)
        session.session.commit()

        self.assertRaises(ValueError, delete_log_entry, malformed_log_entry.id)

        session.session.delete(malformed_log_entry)
        session.session.commit()


class Test_030_RoomLogEntry(FixtureDataTestBase):
    datasets = [RoomData, RoomLogEntryData]

    def test_0010_create_room_log_entry(self):
        message = "test_message"
        timestamp = datetime.now()
        author = User.q.first()
        room = Room.q.first()

        room_log_entry = create_room_log_entry(message=message,
                                               timestamp=timestamp,
                                               author=author,
                                               room=room)

        self.assertIsNotNone(RoomLogEntry.q.get(room_log_entry.id))

        db_room_log_entry = RoomLogEntry.q.get(room_log_entry.id)

        self.assertEqual(db_room_log_entry.message, message)
        self.assertEqual(db_room_log_entry.timestamp, timestamp)
        self.assertEqual(db_room_log_entry.author, author)
        self.assertEqual(db_room_log_entry.room, room)

        session.session.delete(db_room_log_entry)
        session.session.commit()

    def test_0020_delete_room_log_entry(self):
        del_room_log_entry = delete_log_entry(
            RoomLogEntryData.dummy_log_entry1.id)

        self.assertIsNone(RoomLogEntry.q.get(del_room_log_entry.id))

    def test_0025_delete_wrong_room_log_entry(self):
        self.assertRaises(ValueError, delete_log_entry,
                          RoomLogEntryData.dummy_log_entry1.id + 100)
