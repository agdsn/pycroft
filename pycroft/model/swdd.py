from sqlalchemy import text, select, Table, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import DeferredReflection
from sqlalchemy.orm import relationship, backref

from pycroft.model.base import ModelBase
from pycroft.model.ddl import DDLManager, View
from sqlalchemy import event as sqla_event

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

    room = relationship("Room", backref=backref("room", uselist=False))

    user = relationship("User", backref=backref("tenancies"), uselist=False,
                        primaryjoin="foreign(Tenancy.person_id) == remote(User.swdd_person_id)")
    pre_member = relationship("PreMember", backref=backref("tenancies"), uselist=False,
                              primaryjoin="foreign(Tenancy.person_id) == remote(PreMember.swdd_person_id)")


swdd_import = View(
    name='swdd_import',
    query=select([text('*')]).select_from(text("swdd.swdd_import")),
    materialized=True
)
swdd_view_ddl.add_view(ModelBase.metadata, swdd_import, or_replace=False)


swdd_view_ddl.register()
