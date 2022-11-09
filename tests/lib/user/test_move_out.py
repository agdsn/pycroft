# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import pytest

from pycroft.helpers.interval import single
from pycroft.lib.user import move_out
from pycroft.model.user import User
from ... import factories


@pytest.mark.usefixtures("config")
class TestUserMoveOut:
    @pytest.fixture(scope="class")
    def user(self, class_session) -> User:
        return factories.UserFactory(
            with_host=True,
            room__patched_with_subnet=True,
        )

    def test_move_out(self, session, user, processor, utcnow):
        address = user.room.address
        move_out(user=user, comment="", processor=processor, when=utcnow)
        session.refresh(user)
        # check ends_at of moved out user
        for membership in user.memberships:
            assert membership.active_during.before(single(utcnow))

        assert not user.hosts
        assert user.room is None
        # move_out keeps user's address
        assert user.address == address
        # check if users finance account still exists
        assert user.account is not None
