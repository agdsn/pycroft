#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import pytest

from pycroft.model import _all as m
from tests import factories


@pytest.fixture(scope="module")
def processor(module_session) -> m.User:
    return factories.UserFactory.create()
