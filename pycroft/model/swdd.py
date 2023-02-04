"""
pycroft.model.swdd
~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations
import typing as t
from datetime import date

from enum import Enum

from sqlalchemy import text, select, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from pycroft.model.base import ModelBase
from pycroft.model.ddl import DDLManager, View

if t.TYPE_CHECKING:
    # FKeys
    from .facilities import Room
    from .user import User, PreMember

    # backrefs


class TenancyStatus(Enum):
    PROVISIONAL = 1
    ESTABLISHED = 2
    UNDO_PROVISIONAL = 3
    UNDO_FINAL = 4
    CANCELED = 5


swdd_view_ddl = DDLManager()

swdd_vo = View(
    name='swdd_vo',
    query=select(text('*')).select_from(text("swdd.swdd_vo")),
    materialized=True
)
swdd_view_ddl.add_view(ModelBase.metadata, swdd_vo)


class RentalObject(ModelBase):
    __tablename__ = 'swdd_vo'
    __table_args__ = {'info': dict(is_view=True)}

    vo_id: Mapped[int] = mapped_column(primary_key=True)
    suchname: Mapped[str]
    name: Mapped[str]
    voart_id: Mapped[int | None]
    nutzungsart_id: Mapped[int | None]
    nutzbarvon: Mapped[date]
    nutzbarbis: Mapped[date]
    status: Mapped[int | None]
    wohneim_id: Mapped[int | None]
    wohneim_suchname: Mapped[int | None]
    wohneim_name: Mapped[str]
    stockwerk_id: Mapped[int | None]
    stockwerk: Mapped[str]
    stockwerk_name: Mapped[str]
    haus_id: Mapped[int | None]
    haus_name: Mapped[str]


swdd_vv = View(
    name='swdd_vv',
    query=select(text('*')).select_from(text("swdd.swdd_vv")),
    materialized=True
)
swdd_view_ddl.add_view(ModelBase.metadata, swdd_vv)


class Tenancy(ModelBase):
    __tablename__ = 'swdd_vv'
    __table_args__ = {'info': dict(is_view=True)}

    persvv_id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int | None]
    user: Mapped[User | None] = relationship(
        primaryjoin="foreign(Tenancy.person_id) == User.swdd_person_id",
        uselist=False,
        back_populates="tenancies",
        viewonly=True,
    )
    pre_member: Mapped[PreMember | None] = relationship(
        back_populates="tenancies",
        uselist=False,
        primaryjoin="foreign(Tenancy.person_id) == PreMember.swdd_person_id",
        viewonly=True,
        sync_backref=False,
    )

    vo_suchname: Mapped[str] = mapped_column(ForeignKey("room.swdd_vo_suchname"))
    # over `vo_suchname`
    room: Mapped[Room] = relationship(
        back_populates="tenancies",
        uselist=False,  # sketchy, but de facto valid, see #600
        viewonly=True,
    )
    person_hash: Mapped[str]
    mietbeginn: Mapped[date]
    mietende: Mapped[date]
    status_id: Mapped[int]

    @property
    def status(self):
        return TenancyStatus(self.status_id)


swdd_import = View(
    name='swdd_import',
    query=select(text('*')).select_from(text("swdd.swdd_import")),
    materialized=True
)
swdd_view_ddl.add_view(ModelBase.metadata, swdd_import)


swdd_view_ddl.register()
