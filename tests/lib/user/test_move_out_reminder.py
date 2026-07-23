#  Copyright (c) 2025. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from __future__ import annotations

import typing as t
from datetime import datetime, date

import pytest
from sqlalchemy.orm import Session

from pycroft.helpers.interval import closedopen
from pycroft.lib.user.mail import get_members_with_contract_end_at
from pycroft.model.user import User
from ...factories import UserFactory

def test_move_out_reminder(session, config, gen_user: UserWithTenancyGen):
    u = gen_user(
        session,
        date(2019, 10, 1),
        date(2020, 9, 30),
        None,
    )
    session.flush()

    # TODO fixture: member with contract end at 2020-01-08
    # TODO fixture: member with the former, but also

    m = get_members_with_contract_end_at(session, date(2020, 9, 30))
    assert m.all() == [u]



class UserWithTenancyGen(t.Protocol):
    def __call__(
        self,
        session: Session,
        tenancy_begin: date,
        tenancy_end: date,
        mem_end: datetime | None = None,
    ) -> User: ...


@pytest.fixture(scope="function")
def gen_user(config) -> UserWithTenancyGen:
    def gen(
        session: Session, tenancy_begin: date, tenancy_end: date, mem_end: datetime | None = None
    ) -> User:
        u = t.cast(
            User,
            UserFactory.create(
                with_membership=True,
                registered_at=tenancy_begin,
                membership__active_during=closedopen(tenancy_begin, mem_end),
                membership__group=config.member_group,
            ),
        )
        u.swdd_person_id = u.id + 10000
        session.add(u)
        session.flush()
        from sqlalchemy import Table, MetaData, Column, Integer, Text, Date
        from sqlalchemy.sql import text

        swdd_vv = Table(
            "swdd_vv",
            MetaData(),
            Column("persvv_id", Integer, nullable=False),
            Column("person_id", Integer, nullable=False),
            Column("vo_suchname", Text, nullable=False),
            Column("person_hash", Text, nullable=False),
            Column("mietbeginn", Date, nullable=False),
            Column("mietende", Date, nullable=False),
            Column("status_id", Integer, nullable=False),
            schema="swdd",
        )
        assert u.room
        session.execute(
            swdd_vv.insert().values(
                persvv_id=u.id + 10000,
                person_id=u.id + 10000,
                vo_suchname=u.room.swdd_vo_suchname,
                person_hash="",
                mietbeginn=tenancy_begin.isoformat(),
                mietende=tenancy_end.isoformat(),
                status_id=1,
            )
        )
        session.execute(text("refresh materialized view swdd_vv"))
        return u

    return gen

