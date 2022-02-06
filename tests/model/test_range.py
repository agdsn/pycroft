#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from datetime import datetime, timedelta

import pytest
import pytz
from sqlalchemy import Column, literal, cast, TEXT, func
from sqlalchemy.future import select

from pycroft.helpers.interval import open, closed, openclosed, closedopen, single
from pycroft.model.base import IntegerIdModel
from pycroft.model.types import TsTzRange, DateTimeTz


class TableWithInterval(IntegerIdModel):
    value = Column(TsTzRange, server_default=literal(open(None, None), TsTzRange))


NOW = datetime.utcnow().replace(tzinfo=pytz.utc)

def test_select_as_text(session):
    stmt = select(cast(literal(open(None, None), TsTzRange), TEXT))
    assert session.scalar(stmt) == '(,)'


@pytest.mark.parametrize('interval', [
    open(NOW, NOW + timedelta(days=1)),
    closed(NOW, NOW + timedelta(days=1)),
    open(NOW, NOW + timedelta(days=1)),
    open(None, None),
    open(None, NOW),
    openclosed(None, NOW),
    closedopen(None, NOW),
])
def test_declarative_insert_and_select(session, interval):
    mem = TableWithInterval(value=interval)
    with session.begin_nested():
        session.add(mem)
    assert mem.value == interval


@pytest.mark.parametrize('interval', [
        open(NOW, NOW + timedelta(days=1)),
])
def test_literal_select(session, interval):
    stmt = select(cast(literal(interval, TsTzRange), TsTzRange))
    assert session.scalar(stmt) == interval


@pytest.fixture
def table_with_interval(session):
    interval = closedopen(NOW, NOW + timedelta(days=1))
    with session.begin_nested():
        session.add(TableWithInterval(value=interval))

@pytest.mark.parametrize('value, expected', [
    (literal(NOW, DateTimeTz), True),
    (NOW, True),
    (func.current_timestamp(), True),
    (NOW + timedelta(hours=6), True),
    (single(NOW), True),
    (closedopen(NOW, NOW + timedelta(days=1)), True),
    (open(NOW, NOW + timedelta(days=1)), True),

    (NOW - timedelta(days=1), False),
    (NOW - timedelta(seconds=1), False),
    (literal(NOW - timedelta(seconds=1), DateTimeTz), False),
    (closed(NOW, NOW + timedelta(days=1)), False),
])
def test_containmment(session, table_with_interval, value, expected):
    stmt = select(TableWithInterval.value.contains(value))
    assert session.execute(stmt).scalar() is expected
