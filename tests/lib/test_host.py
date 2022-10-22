# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import re

import pytest
from sqlalchemy.orm import Session

from pycroft.helpers.i18n import localized
from pycroft.lib.host import change_mac
from pycroft.model.host import Interface
from pycroft.model.logging import UserLogEntry
from pycroft.model.user import User
from tests.factories import InterfaceFactory, UserFactory


@pytest.fixture(scope="module")
def interface(module_session: Session) -> Interface:
    return InterfaceFactory.create()


@pytest.fixture()
def owner(session, interface) -> User:
    user = UserFactory.create(host=interface.host)
    interface.host.owner = user
    return user


NEW_MAC = "20:00:00:00:00:00"


def test_change_mac(interface, processor):
    change_mac(interface, NEW_MAC, processor)
    assert interface.mac == NEW_MAC


CHANGED_MAC_REGEX = re.compile(r"changed mac", re.IGNORECASE)
def test_change_mac_with_owner(session, owner, interface, processor):
    interface = change_mac(interface, NEW_MAC, processor)
    assert interface.mac == NEW_MAC
    assert len(owner.log_entries) == 1
    l: UserLogEntry = owner.log_entries[0]
    assert CHANGED_MAC_REGEX.search(localized(l.message))
