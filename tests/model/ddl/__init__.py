import sqlalchemy.dialects.postgresql.base as postgresql_base
from sqlalchemy import Table, Column, Integer, MetaData, \
    util
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import sqltypes


class LiteralInterval(postgresql_base.INTERVAL):
    @classmethod
    def _adapt_from_generic_interval(cls, interval):
        return LiteralInterval(precision=interval.second_precision)

    def literal_processor(self, dialect):
        def process(value):
            return "interval '{}'".format(value) \
                .replace(',', '').replace(' 0:00:00', '')

        return process


class LiteralDate(postgresql_base.DATE):
    def literal_processor(self, dialect):
        def process(value):
            return "date '{}'".format(value.isoformat())

        return process


class Literal_PGDialect_pygresql(postgresql.dialect):
    colspecs = util.update_copy(
        postgresql.dialect.colspecs,
        {
            sqltypes.Interval: LiteralInterval,
            sqltypes.Date: LiteralDate,
        }
    )


def literal_compile(stmt):
    return str(stmt.compile(compile_kwargs={"literal_binds": True},
                            dialect=Literal_PGDialect_pygresql()))


def create_table(name):
    return Table(name, MetaData(), Column("id", Integer))
