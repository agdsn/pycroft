#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from datetime import datetime, timedelta

import pytz
from sqlalchemy import Column, literal, cast, TEXT
from sqlalchemy.future import select

from pycroft.helpers.interval import open, closed, openclosed, closedopen
from pycroft.model.base import IntegerIdModel
from pycroft.model.types import TsTzRange
from tests import SQLAlchemyTestCase


class TestTable(IntegerIdModel):
    value = Column(TsTzRange)


NOW = datetime.utcnow().replace(tzinfo=pytz.utc)

class TestTsTzRange(SQLAlchemyTestCase):
    def test_select_as_text(self):
        stmt = select(cast(literal(open(None, None), TsTzRange), TEXT))
        assert self.session.scalar(stmt) == '(,)'

    def test_declarative_insert_and_select(self):
        for interval in [
            open(NOW, NOW + timedelta(days=1)),
            closed(NOW, NOW + timedelta(days=1)),
            open(NOW, NOW + timedelta(days=1)),
            open(None, None),
            open(None, NOW),
            openclosed(None, NOW),
            closedopen(None, NOW),
        ]:
            with self.subTest(interval=interval):
                mem = TestTable(value=interval)

                self.session.add(mem)
                self.session.commit()

                assert mem.value == interval
    def test_literal_select(self):
        for interval in [
            open(NOW, NOW + timedelta(days=1)),
        ]:
            with self.subTest(interval=interval):
                stmt = select(cast(literal(interval, TsTzRange), TsTzRange))
                assert self.session.scalar(stmt) == interval
