#  Copyright (c) 2024. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import pytest
from packaging.utils import InvalidName
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.base import object_state

from pycroft.model.mpsk_client import MPSKClient
from pycroft.model.types import InvalidMACAddressException
from .. import factories


class TestMPSKValidators:

    @pytest.fixture(scope="class")
    def user(self, class_session):
        user = factories.UserFactory.build(with_host=True)
        class_session.add(user)
        return user

    @pytest.fixture(scope="class")
    def mpsk_client(self, user):
        return factories.MPSKFactory()

    @pytest.mark.parametrize(
        "mac",
        [
            "ff:ff:ff:ff:ff",
            "ff:ff:ff:ff:ff:ff",
            "ff:asjfjsdaf:ff:ff:ff:ff",
            "aj:00:ff:1f:ff:ff",
            "ff:ff:ff:ff:ff:ff:ff",
        ],
    )
    def test_bad_macs(self, session, user, mac):
        mpsk_client = MPSKClient(
            name="the needs of the many outweigh the needs of the few", owner=user
        )
        assert object_state(mpsk_client).transient
        with pytest.raises(InvalidMACAddressException):
            mpsk_client.mac = mac
        with pytest.raises(IntegrityError):
            session.add(mpsk_client)
            session.flush()

    def test_no_name(self, session, user):
        mpsk_client = MPSKClient(mac="00:00:00:00:00:00", owner=user)
        with pytest.raises(IntegrityError):
            session.add(mpsk_client)
            session.flush()
        with pytest.raises(InvalidName):
            MPSKClient(mac="00:00:00:00:00:00", name="", owner=user)

    def test_no_mac(self, session, user):
        mpsk_client = MPSKClient(name="00:00:00:00:00:00", owner=user)
        with pytest.raises(IntegrityError):
            session.add(mpsk_client)
            session.flush()

    def test_no_owner(self, session, user):
        mpsk_client = MPSKClient(mac="00:00:00:00:00:00", name="as")
        with pytest.raises(IntegrityError):
            session.add(mpsk_client)
            session.flush()

    @pytest.mark.parametrize(
        "name",
        [
            "  a   ",
            " a",
            "ff:asjfjsdaf:ff:ff:ff:ff",
            "aj:00:ff:1f:ff:ff",
            "ff:ff:ff:ff:ff:ff:ff",
        ],
    )
    def test_names(self, session, user, name):
        mpsk_client = MPSKClient(mac="00:00:00:00:00:00", name=name, owner=user)
        assert mpsk_client.name == name
