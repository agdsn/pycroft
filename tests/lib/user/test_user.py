# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from pycroft import config
from pycroft.lib import user as UserHelper
from pycroft.model import session
from ...legacy_base import FactoryDataTestBase
from tests.factories import UserFactory
from ... import factories


# TODO slaughter this test, and only leave things that aren't already tested elsewhere.
class Test_User_Move_Out_And_Back_In(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.config = factories.ConfigFactory()
        self.room = factories.RoomFactory(patched_with_subnet=True, number="1", level=1)
        self.processing_user = UserFactory()

    def test_move_out(self):
        test_name = "Hans"
        test_login = "hans66"
        test_email = "hans@hans.de"
        test_building = self.room.building
        test_mac = "12:11:11:11:11:11"
        test_birthdate = "1990-01-01"

        address = self.room.address

        new_user, _ = UserHelper.create_user(
            test_name,
            test_login,
            test_email,
            test_birthdate,
            processor=self.processing_user,
            groups=[self.config.member_group],
            address=address
        )

        UserHelper.move_in(
            new_user,
            building_id=test_building.id,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=self.processing_user,
        )

        self.session.commit()

        out_time = session.utcnow()

        UserHelper.move_out(user=new_user, comment="",
                            processor=self.processing_user, when=out_time)
        self.session.refresh(new_user)
        # check ends_at of moved out user
        for membership in new_user.memberships:
            assert (int := membership.active_during) is not None
            assert (end := int.end) is not None
            assert end <= out_time

        assert not new_user.hosts
        assert new_user.room is None
        # move_out keeps user's address
        assert new_user.address == address

        # check if users finance account still exists
        assert new_user.account is not None
