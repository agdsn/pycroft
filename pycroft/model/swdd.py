from sqlalchemy import text, select, Table, Column, Integer
from sqlalchemy.ext.declarative import DeferredReflection

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
    vo_id = Column(Integer, primary_key=True)


swdd_vv = View(
    name='swdd_vv',
    query=select([text('*')]).select_from(text("swdd.swdd_vv")),
    materialized=True
)
swdd_view_ddl.add_view(ModelBase.metadata, swdd_vv, or_replace=False)

swdd_import = View(
    name='swdd_import',
    query=select([text('*')]).select_from(text("swdd.swdd_import")),
    materialized=True
)
swdd_view_ddl.add_view(ModelBase.metadata, swdd_import, or_replace=False)


swdd_view_ddl.register()
