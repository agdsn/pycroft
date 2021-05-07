# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from pycroft import config
from pycroft.lib import user as UserHelper
from pycroft.model import session
from tests import FactoryDataTestBase
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
        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
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
            assert membership.ends_at is not None
            membership.ends_at <= out_time

        assert not new_user.hosts
        assert new_user.room is None
        # move_out keeps user's address
        assert new_user.address == address

        # check if users finance account still exists
        assert new_user.account is not None

        UserHelper.move_in(
            user=new_user,
            building_id=test_building.id,
            level=1,
            room_number="1",
            mac=test_mac,
            birthdate=test_birthdate,
            processor=self.processing_user,
        )

        self.session.refresh(new_user)
        assert new_user.room.building == test_building
        assert new_user.room.level == 1
        assert new_user.room.number == "1"
        assert new_user.address == new_user.room.address

        assert len(new_user.hosts) == 1
        user_host = new_user.hosts[0]
        assert len(user_host.interfaces) == 1
        assert user_host.interfaces[0].mac == test_mac
        assert len(user_host.ips) == 1

        assert new_user.member_of(config.member_group)
        assert new_user.member_of(config.network_access_group)
