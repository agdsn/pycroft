#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

from contextlib import contextmanager

import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError


@contextmanager
def assert_unique_violation():
    pattern = 'duplicate key value violates unique constraint ".+_key"'
    with pytest.raises(IntegrityError, match=pattern):
        yield


@pytest.fixture(scope='module')
def utcnow(module_session):
    return module_session.scalar(select(func.current_timestamp()))
