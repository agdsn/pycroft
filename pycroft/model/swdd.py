from enum import Enum

from sqlalchemy import text, select, Table, Column, Integer, String, ForeignKey, Date
from sqlalchemy.ext.declarative import DeferredReflection
from sqlalchemy.orm import relationship, backref

from pycroft.model.base import ModelBase
from pycroft.model.ddl import DDLManager, View


class TenancyStatus(Enum):
    PROVISIONAL = 1
    ESTABLISHED = 2
    UNDO_PROVISIONAL = 3
    UNDO_FINAL = 4
    CANCELED = 5


swdd_view_ddl = DDLManager()

swdd_vo = View(
    name='swdd_vo',
    query=select([text('*')]).select_from(text("swdd.swdd_vo")),
    materialized=True
)
swdd_view_ddl.add_view(ModelBase.metadata, swdd_vo, or_replace=False)


class RentalObject(DeferredReflection, ModelBase):
    __tablename__ = 'swdd_vo'
    __table_args__ = {'info': dict(is_view=True)}

    vo_id = Column(Integer, primary_key=True)
    suchname = Column(String)
    name = Column(String)
    voart_id = Column(Integer)
    nutzungsart_id = Column(Integer)
    nutzbarvon = Column(Date)
    nutzbarbis = Column(Date)
    status = Column(Integer)
    wohneim_id = Column(Integer)
    wohneim_suchname = Column(Integer)
    wohneim_name = Column(String)
    stockwerk_id = Column(Integer)
    stockwerk = Column(String)
    stockwerk_name = Column(String)
    haus_id = Column(Integer)
    haus_name = Column(String)


swdd_vv = View(
    name='swdd_vv',
    query=select([text('*')]).select_from(text("swdd.swdd_vv")),
    materialized=True
)
swdd_view_ddl.add_view(ModelBase.metadata, swdd_vv, or_replace=False)


class Tenancy(DeferredReflection, ModelBase):
    __tablename__ = 'swdd_vv'
    __table_args__ = {'info': dict(is_view=True)}

    persvv_id = Column(Integer, primary_key=True)
    person_id = Column(Integer)
    vo_suchname = Column(String, ForeignKey("room.swdd_vo_suchname"))

    person_hash = Column(String)

    mietbeginn = Column(Date)
    mietende = Column(Date)

    status_id = Column(Integer, nullable=False)

    room = relationship("Room", backref=backref("room", uselist=False),
                        viewonly=True, sync_backref=False)

    user = relationship("User", backref=backref("tenancies"), uselist=False,
                        primaryjoin="foreign(Tenancy.person_id) == remote(User.swdd_person_id)",
                        viewonly=True, sync_backref=False)
    pre_member = relationship("PreMember", backref=backref("tenancies"), uselist=False,
                              primaryjoin="foreign(Tenancy.person_id) == remote(PreMember.swdd_person_id)",
                              viewonly=True, sync_backref=False)

    @property
    def status(self):
        return TenancyStatus(self.status_id)


swdd_import = View(
    name='swdd_import',
    query=select([text('*')]).select_from(text("swdd.swdd_import")),
    materialized=True
)
swdd_view_ddl.add_view(ModelBase.metadata, swdd_import, or_replace=False)


swdd_view_ddl.register()
