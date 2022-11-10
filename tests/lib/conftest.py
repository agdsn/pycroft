#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import pytest
from sqlalchemy import func
from sqlalchemy.future import select

from pycroft.model import _all as m
from tests import factories


@pytest.fixture(scope='module')
def utcnow(module_session):
    return module_session.scalar(select(func.current_timestamp()))


@pytest.fixture(scope="module")
def processor(module_session) -> m.User:
    return factories.UserFactory.create()


@pytest.fixture(scope="module")
def config(module_session) -> m.Config:
    return factories.ConfigFactory.create()
