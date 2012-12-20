# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from tests import FixtureDataTestBase
from tests.lib.fixtures.infrastructure_fixtures import DestinationPortData,\
    PatchPortData, PhonePortData, SwitchPortData, RoomData, SwitchData

from pycroft.lib.infrastructure import create_patch_port, create_phone_port,\
    create_switch_port, _create_port, delete_port

from pycroft.model.ports import DestinationPort, PatchPort, PhonePort,\
    SwitchPort, Port
from pycroft.model.dormitory import Room
from pycroft.model.hosts import Switch
from pycroft.model import session

from sqlalchemy.types import Integer
from sqlalchemy import Column, ForeignKey

class Test_010_PatchPort(FixtureDataTestBase):
    datasets = [RoomData, DestinationPortData, PatchPortData]

    def test_0010_create_patch_port(self):
        name = "P101"
        destination_port = DestinationPort.q.first()
        room = Room.q.first()

        patch_port = create_patch_port(name=name,
            destination_port=destination_port, room=room)

        self.assertIsNotNone(PatchPort.q.get(patch_port.id))

        db_patch_port = PatchPort.q.get(patch_port.id)

        self.assertEqual(db_patch_port.name, name)
        self.assertEqual(db_patch_port.destination_port, destination_port)
        self.assertEqual(db_patch_port.room, room)

        session.session.delete(db_patch_port)
        session.session.commit()

    def test_0020_delete_patch_port(self):
        del_patch_port = delete_port(PatchPortData.dummy_patch_port1.id)

        self.assertIsNone(PatchPort.q.get(del_patch_port.id))

    def test_0025_delete_wrong_patch_port(self):
        self.assertRaises(ValueError, delete_port,
            PatchPortData.dummy_patch_port1.id + 100)


class Test_020_PhonePort(FixtureDataTestBase):
    datasets = [PhonePortData]

    def test_0010_create_phone_port(self):
        name = "P201"

        phone_port = create_phone_port(name=name)

        self.assertIsNotNone(PhonePort.q.get(phone_port.id))

        db_phone_port = PhonePort.q.get(phone_port.id)

        self.assertEqual(db_phone_port.name, name)

        session.session.delete(db_phone_port)
        session.session.commit()

    def test_0020_delete_phone_port(self):
        del_phone_port = delete_port(PhonePortData.dummy_phone_port.id)

        self.assertIsNone(PhonePort.q.get(del_phone_port.id))

    def test_0025_delete_wrong_phone_port(self):
        self.assertRaises(ValueError, delete_port,
            PhonePortData.dummy_phone_port.id + 100)


class Test_030_SwitchPort(FixtureDataTestBase):
    datasets = [SwitchData, SwitchPortData]

    def test_0010_create_switch_port(self):
        name = "S101"
        switch = Switch.q.first()

        switch_port = create_switch_port(name=name, switch=switch)

        self.assertIsNotNone(SwitchPort.q.get(switch_port.id))

        db_switch_port = SwitchPort.q.get(switch_port.id)

        self.assertEqual(db_switch_port.name, name)
        self.assertEqual(db_switch_port.switch, switch)

        session.session.delete(db_switch_port)
        session.session.commit()

    def test_0020_delete_switch_port(self):
        del_switch_port = delete_port(SwitchPortData.dummy_switch_port.id)

        self.assertIsNone(SwitchPort.q.get(del_switch_port.id))

    def test_0025_delete_wrong_switch_port(self):
        self.assertRaises(ValueError, delete_port,
            SwitchPortData.dummy_switch_port.id + 100)


class Test_040_MalformedPort(FixtureDataTestBase):
    datasets = [DestinationPortData]

    class MalformedPort(Port):
        id = Column(Integer, ForeignKey("port.id"), primary_key=True)
        __mapper_args__ = {'polymorphic_identity': "malformed_port"}

    def test_0010_create_malformed_port(self):
        self.assertRaises(ValueError, _create_port, 'malformed_port', id=1000)

    def test_0020_delete_malformed_port(self):
        name = "M100"

        malformed_port = Test_040_MalformedPort.MalformedPort(name=name)

        session.session.add(malformed_port)
        session.session.commit()

        self.assertRaises(ValueError, delete_port, malformed_port.id)

        session.session.delete(malformed_port)
        session.session.commit()
