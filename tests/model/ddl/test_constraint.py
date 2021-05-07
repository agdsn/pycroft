from sqlalchemy import PrimaryKeyConstraint

from pycroft.model.ddl import DropConstraint
from . import literal_compile


def test_drop_constraint_if_exists(table):
    stmt = DropConstraint(PrimaryKeyConstraint(table.c.id, name="pk_constraint"), if_exists=True)
    assert literal_compile(stmt) == "ALTER TABLE test DROP CONSTRAINT IF EXISTS pk_constraint"


def test_drop_constraint_identifier_quotation(table):
    stmt = DropConstraint(PrimaryKeyConstraint(table.c.id, name='PRIMARY'))
    assert literal_compile(stmt) == 'ALTER TABLE test DROP CONSTRAINT "PRIMARY"'
